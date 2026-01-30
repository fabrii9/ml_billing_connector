# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MlOperation(models.Model):
    _name = 'ml.operation'
    _description = 'Operación de Mercado Libre'
    _order = 'date_created desc, id desc'
    _rec_name = 'order_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Identificación
    order_id = fields.Char(string='Order ID', required=True, index=True, 
                           help='ID de la orden en Mercado Libre')
    pack_id = fields.Char(string='Pack ID', help='ID del paquete si aplica')
    
    # Fechas
    date_created = fields.Datetime(string='Fecha Creación', required=True, index=True)
    date_closed = fields.Datetime(string='Fecha Cierre')
    date_approved = fields.Datetime(string='Fecha Aprobación Pago')
    last_updated = fields.Datetime(string='Última Actualización ML')
    
    # Estados
    status = fields.Selection([
        ('confirmed', 'Confirmada'),
        ('payment_required', 'Pago Requerido'),
        ('payment_in_process', 'Pago en Proceso'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado Orden', index=True, tracking=True)
    
    payment_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('in_process', 'En Proceso'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
    ], string='Estado Pago', index=True, tracking=True)
    
    # Importes
    total_amount = fields.Monetary(string='Total Orden', currency_field='currency_id')
    paid_amount = fields.Monetary(string='Monto Pagado', currency_field='currency_id')
    
    # Desglose de importes
    item_amount = fields.Monetary(string='Productos', currency_field='currency_id',
                                   help='Total de productos vendidos')
    shipping_amount = fields.Monetary(string='Envío', currency_field='currency_id')
    tax_amount = fields.Monetary(string='Impuestos', currency_field='currency_id')
    
    # Comisiones y cargos (calculados desde fees)
    total_fees = fields.Monetary(string='Comisiones Totales', 
                                  compute='_compute_total_fees', 
                                  store=True,
                                  currency_field='currency_id')
    
    net_amount = fields.Monetary(string='Neto a Cobrar', 
                                  compute='_compute_net_amount',
                                  store=True,
                                  currency_field='currency_id',
                                  help='Total - Comisiones - Cargos')
    
    # Moneda
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True)
    currency_code = fields.Char(string='Código Moneda ML')
    
    # Datos fiscales del comprador
    buyer_doc_type = fields.Selection([
        ('DNI', 'DNI'),
        ('CUIT', 'CUIT'),
        ('CUIL', 'CUIL'),
        ('CDI', 'CDI'),
        ('Otro', 'Otro'),
    ], string='Tipo Documento')
    
    buyer_doc_number = fields.Char(string='Número Documento', index=True)
    buyer_name = fields.Char(string='Nombre Comprador')
    buyer_nickname = fields.Char(string='Usuario ML Comprador')
    buyer_email = fields.Char(string='Email Comprador')
    buyer_phone = fields.Char(string='Teléfono Comprador')
    
    # Dirección de envío
    shipping_address = fields.Text(string='Dirección de Envío')
    shipping_city = fields.Char(string='Ciudad')
    shipping_state = fields.Char(string='Provincia/Estado')
    shipping_zip_code = fields.Char(string='Código Postal')
    
    # Items de la orden
    item_count = fields.Integer(string='Cantidad Items', compute='_compute_item_count', store=True)
    
    # Fees/Comisiones
    fee_ids = fields.One2many('ml.operation.fee', 'operation_id', string='Comisiones y Cargos')
    
    # Relaciones
    config_id = fields.Many2one('ml.api.config', string='Configuración ML', 
                                 required=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Compañía', 
                                  related='config_id.company_id', store=True)
    
    # Tags
    tag_ids = fields.Many2many('ml.operation.tag', string='Etiquetas')
    
    # Auditoría
    raw_json = fields.Text(string='JSON Completo', help='Respuesta completa de la API para auditoría')
    raw_billing_info = fields.Text(string='JSON Billing Info')
    notes = fields.Text(string='Notas')
    
    # Control
    imported_date = fields.Datetime(string='Fecha Importación', default=fields.Datetime.now, readonly=True)
    
    _sql_constraints = [
        ('unique_order_config', 'unique(order_id, config_id)', 
         'Esta orden ya ha sido importada en esta configuración!')
    ]

    @api.depends('fee_ids', 'fee_ids.amount')
    def _compute_total_fees(self):
        """Calcula el total de comisiones y cargos"""
        for record in self:
            record.total_fees = sum(record.fee_ids.mapped('amount'))

    @api.depends('total_amount', 'total_fees')
    def _compute_net_amount(self):
        """Calcula el monto neto (total - comisiones)"""
        for record in self:
            record.net_amount = record.total_amount - record.total_fees

    @api.depends('raw_json')
    def _compute_item_count(self):
        """Calcula la cantidad de items desde el JSON"""
        for record in self:
            if record.raw_json:
                try:
                    data = json.loads(record.raw_json)
                    order_items = data.get('order_items', [])
                    record.item_count = sum(item.get('quantity', 0) for item in order_items)
                except:
                    record.item_count = 0
            else:
                record.item_count = 0

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"Orden {record.order_id}"
            if record.buyer_name:
                name += f" - {record.buyer_name}"
            if record.date_created:
                name += f" ({record.date_created.strftime('%d/%m/%Y')})"
            result.append((record.id, name))
        return result

    def action_view_items_detail(self):
        """Muestra el detalle de items de la orden"""
        self.ensure_one()
        
        if not self.raw_json:
            raise UserError(_('No hay información detallada disponible para esta orden.'))
        
        try:
            data = json.loads(self.raw_json)
            order_items = data.get('order_items', [])
            
            message = "Items de la orden:\n\n"
            for item in order_items:
                item_data = item.get('item', {})
                message += f"• {item_data.get('title', 'N/A')}\n"
                message += f"  Cantidad: {item.get('quantity', 0)}\n"
                message += f"  Precio unitario: {item.get('unit_price', 0)} {self.currency_code}\n"
                message += f"  SKU: {item_data.get('seller_custom_field', 'N/A')}\n\n"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Detalle de Items'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }
        except Exception as e:
            raise UserError(_(f'Error al procesar el detalle: {str(e)}'))

    def action_refresh_from_ml(self):
        """Actualiza la información de la orden desde Mercado Libre"""
        self.ensure_one()
        
        try:
            # Obtener datos actualizados
            order_data = self.config_id._make_api_request(f'/orders/{self.order_id}')
            
            # Actualizar operación
            self._update_from_api_data(order_data, update_mode=True)
            
            # Intentar actualizar billing info
            try:
                billing_info = self._fetch_billing_info(self.order_id)
                if billing_info:
                    self._update_billing_info(billing_info)
            except Exception as e:
                _logger.warning(f"No se pudo actualizar billing info: {str(e)}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Actualizado'),
                    'message': _('Información actualizada desde Mercado Libre'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_(f'Error al actualizar: {str(e)}'))

    def _update_from_api_data(self, order_data, update_mode=False):
        """
        Actualiza los campos del registro con datos de la API
        
        :param order_data: Diccionario con datos de la orden desde ML API
        :param update_mode: Si True, actualiza registro existente; si False, crea nuevo
        """
        # Obtener moneda
        currency_code = order_data.get('currency_id', 'ARS')
        currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
        if not currency:
            currency = self.env['res.currency'].search([('name', '=', 'ARS')], limit=1)
        
        # Parsear fechas
        date_created = self._parse_ml_date(order_data.get('date_created'))
        date_closed = self._parse_ml_date(order_data.get('date_closed'))
        last_updated = self._parse_ml_date(order_data.get('last_updated'))
        
        # Obtener fecha de aprobación del pago
        date_approved = None
        payments = order_data.get('payments', [])
        if payments:
            date_approved = self._parse_ml_date(payments[0].get('date_approved'))
        
        # Calcular importes
        total_amount = float(order_data.get('total_amount', 0))
        paid_amount = float(order_data.get('paid_amount', 0))
        
        # Desglose (puede variar según la estructura de la orden)
        order_items = order_data.get('order_items', [])
        item_amount = sum(float(item.get('unit_price', 0)) * item.get('quantity', 0) 
                         for item in order_items)
        
        shipping_amount = 0
        if order_data.get('shipping'):
            shipping_amount = float(order_data.get('shipping', {}).get('cost', 0))
        
        # Impuestos (si están disponibles)
        tax_amount = 0
        if order_data.get('taxes'):
            tax_amount = float(order_data.get('taxes', {}).get('amount', 0))
        
        # Datos del comprador
        buyer = order_data.get('buyer', {})
        buyer_name = f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip()
        
        # Dirección de envío
        shipping_address = ''
        shipping_city = ''
        shipping_state = ''
        shipping_zip_code = ''
        
        if order_data.get('shipping'):
            receiver_address = order_data['shipping'].get('receiver_address', {})
            if receiver_address:
                address_parts = []
                if receiver_address.get('street_name'):
                    address_parts.append(receiver_address['street_name'])
                if receiver_address.get('street_number'):
                    address_parts.append(str(receiver_address['street_number']))
                if receiver_address.get('apartment'):
                    address_parts.append(f"Apt. {receiver_address['apartment']}")
                
                shipping_address = ', '.join(address_parts)
                shipping_city = receiver_address.get('city', {}).get('name', '')
                shipping_state = receiver_address.get('state', {}).get('name', '')
                shipping_zip_code = receiver_address.get('zip_code', '')
        
        # Valores a actualizar/crear
        values = {
            'order_id': str(order_data.get('id')),
            'pack_id': str(order_data.get('pack_id')) if order_data.get('pack_id') else False,
            'date_created': date_created,
            'date_closed': date_closed,
            'date_approved': date_approved,
            'last_updated': last_updated,
            'status': order_data.get('status', 'confirmed'),
            'payment_status': payments[0].get('status') if payments else 'pending',
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'item_amount': item_amount,
            'shipping_amount': shipping_amount,
            'tax_amount': tax_amount,
            'currency_id': currency.id,
            'currency_code': currency_code,
            'buyer_name': buyer_name or False,
            'buyer_nickname': buyer.get('nickname', False),
            'buyer_email': buyer.get('email', False),
            'buyer_phone': buyer.get('phone', {}).get('number', False),
            'shipping_address': shipping_address or False,
            'shipping_city': shipping_city or False,
            'shipping_state': shipping_state or False,
            'shipping_zip_code': shipping_zip_code or False,
            'raw_json': json.dumps(order_data, indent=2, ensure_ascii=False),
        }
        
        if update_mode:
            self.write(values)
        else:
            return values

    def _fetch_billing_info(self, order_id):
        """Obtiene la información de facturación desde ML API"""
        try:
            billing_info = self.config_id._make_api_request(
                f'/orders/{order_id}/billing_info'
            )
            return billing_info
        except Exception as e:
            _logger.warning(f"No se pudo obtener billing_info para orden {order_id}: {str(e)}")
            return None

    def _update_billing_info(self, billing_info):
        """Actualiza los datos fiscales del comprador"""
        if not billing_info:
            return
        
        doc_type = billing_info.get('doc_type', '').upper()
        doc_number = billing_info.get('doc_number', '')
        
        # Mapear tipo de documento
        doc_type_mapped = False
        if doc_type in ['DNI', 'CUIT', 'CUIL', 'CDI']:
            doc_type_mapped = doc_type
        elif doc_type:
            doc_type_mapped = 'Otro'
        
        values = {
            'buyer_doc_type': doc_type_mapped,
            'buyer_doc_number': doc_number,
            'raw_billing_info': json.dumps(billing_info, indent=2, ensure_ascii=False),
        }
        
        self.write(values)

    @api.model
    def _parse_ml_date(self, date_string):
        """Parsea una fecha en formato ISO de Mercado Libre"""
        if not date_string:
            return False
        
        try:
            # ML usa formato ISO 8601: 2023-12-25T10:30:45.000-03:00
            # Python puede parsear esto directamente
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            # Convertir a naive datetime (Odoo maneja UTC internamente)
            return dt.replace(tzinfo=None)
        except Exception as e:
            _logger.warning(f"Error al parsear fecha '{date_string}': {str(e)}")
            return False

    @api.model
    def import_operations_from_ml(self, config, date_from, date_to, limit=50):
        """
        Importa operaciones desde Mercado Libre
        
        :param config: Registro de ml.api.config
        :param date_from: Fecha desde (datetime)
        :param date_to: Fecha hasta (datetime)
        :param limit: Límite de resultados por página
        :return: Diccionario con estadísticas
        """
        _logger.info(f"Iniciando importación de operaciones ML desde {date_from} hasta {date_to}")
        
        stats = {
            'total_fetched': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
        }
        
        try:
            # Buscar órdenes por seller y rango de fechas
            offset = 0
            has_more = True
            
            while has_more:
                # Parámetros de búsqueda
                # ML requiere formato ISO con timezone (Z para UTC)
                params = {
                    'seller': config.seller_id,
                    'order.date_created.from': date_from.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    'order.date_created.to': date_to.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    'sort': 'date_desc',
                    'limit': limit,
                    'offset': offset,
                }
                
                # Buscar órdenes
                search_result = config._make_api_request('/orders/search', params=params)
                
                results = search_result.get('results', [])
                paging = search_result.get('paging', {})
                
                stats['total_fetched'] += len(results)
                
                _logger.info(f"Procesando {len(results)} órdenes (offset: {offset})")
                
                # Procesar cada orden
                for result in results:
                    try:
                        # ML puede devolver solo IDs o objetos completos dependiendo del endpoint
                        if isinstance(result, dict):
                            # Si es un objeto, extraer el ID
                            order_id = result.get('id')
                            if not order_id:
                                _logger.warning(f"Orden sin ID encontrada: {result}")
                                stats['errors'] += 1
                                continue
                        else:
                            # Si es un número/string, es el ID directamente
                            order_id = result
                        
                        self._import_single_operation(config, str(order_id), stats)
                    except Exception as e:
                        _logger.error(f"Error al importar orden {result}: {str(e)}")
                        stats['errors'] += 1
                
                # Verificar si hay más resultados
                total = paging.get('total', 0)
                offset += limit
                has_more = offset < total
                
                # Límite de seguridad: máximo 1000 órdenes por importación
                if offset >= 1000:
                    _logger.warning("Alcanzado límite de 1000 órdenes, deteniendo importación")
                    has_more = False
            
            # Actualizar fecha de última sincronización
            config.write({'last_sync_date': fields.Datetime.now()})
            
            _logger.info(f"Importación completada. Stats: {stats}")
            
        except Exception as e:
            _logger.error(f"Error en importación de operaciones: {str(e)}")
            stats['errors'] += 1
            raise
        
        return stats

    @api.model
    def _import_single_operation(self, config, order_id, stats):
        """Importa una única operación"""
        # Obtener detalle de la orden
        order_data = config._make_api_request(f'/orders/{order_id}')
        
        # Verificar si ya existe
        existing = self.search([
            ('order_id', '=', str(order_id)),
            ('config_id', '=', config.id)
        ], limit=1)
        
        if existing:
            # Actualizar existente
            existing._update_from_api_data(order_data, update_mode=True)
            stats['updated'] += 1
            operation = existing
        else:
            # Crear nuevo
            values = self._update_from_api_data(order_data, update_mode=False)
            values['config_id'] = config.id
            operation = self.create(values)
            stats['created'] += 1
        
        # Intentar obtener billing info
        try:
            billing_info = operation._fetch_billing_info(order_id)
            if billing_info:
                operation._update_billing_info(billing_info)
        except Exception as e:
            _logger.warning(f"No se pudo obtener billing info para {order_id}: {str(e)}")
        
        # Importar fees si están disponibles
        try:
            operation._import_fees_from_order_data(order_data)
        except Exception as e:
            _logger.warning(f"No se pudieron importar fees para {order_id}: {str(e)}")
        
        return operation

    def _import_fees_from_order_data(self, order_data):
        """Importa las comisiones y cargos desde los datos de la orden"""
        self.ensure_one()
        
        # Limpiar fees existentes
        self.fee_ids.unlink()
        
        # Obtener payments
        payments = order_data.get('payments', [])
        
        for payment in payments:
            # Comisión de ML
            if payment.get('marketplace_fee'):
                self.env['ml.operation.fee'].create({
                    'operation_id': self.id,
                    'fee_type': 'marketplace_fee',
                    'description': 'Comisión Mercado Libre',
                    'amount': abs(float(payment['marketplace_fee'])),
                    'currency_id': self.currency_id.id,
                })
            
            # Costo de envío para el vendedor
            if payment.get('shipping_cost'):
                self.env['ml.operation.fee'].create({
                    'operation_id': self.id,
                    'fee_type': 'shipping_cost',
                    'description': 'Costo de Envío (Vendedor)',
                    'amount': abs(float(payment['shipping_cost'])),
                    'currency_id': self.currency_id.id,
                })
            
            # Costo financiero
            if payment.get('transaction_amount_refunded'):
                refunded = abs(float(payment['transaction_amount_refunded']))
                if refunded > 0:
                    self.env['ml.operation.fee'].create({
                        'operation_id': self.id,
                        'fee_type': 'refund',
                        'description': 'Monto Reembolsado',
                        'amount': refunded,
                        'currency_id': self.currency_id.id,
                    })


class MlOperationTag(models.Model):
    _name = 'ml.operation.tag'
    _description = 'Etiqueta de Operación ML'

    name = fields.Char(string='Nombre', required=True)
    color = fields.Integer(string='Color')
