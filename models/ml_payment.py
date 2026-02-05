# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MlPayment(models.Model):
    _name = 'ml.payment'
    _description = 'Pago de Mercado Pago'
    _order = 'date_approved desc, id desc'
    _rec_name = 'payment_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Identificación del pago
    payment_id = fields.Char(string='ID Pago MP', required=True, index=True, 
                             help='ID único del pago en Mercado Pago')
    external_reference = fields.Char(string='Referencia Externa', 
                                     help='Referencia externa del comercio')
    
    # Fechas
    date_created = fields.Datetime(string='Fecha Creación', index=True)
    date_approved = fields.Datetime(string='Fecha Aprobación', required=True, index=True)
    date_last_modified = fields.Datetime(string='Última Modificación')
    
    # Estado del pago
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('in_process', 'En Proceso'),
        ('in_mediation', 'En Mediación'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
        ('charged_back', 'Contracargo'),
    ], string='Estado', required=True, index=True, tracking=True)
    
    status_detail = fields.Char(string='Detalle Estado')
    
    # Importes
    transaction_amount = fields.Monetary(string='Monto Transacción', 
                                        currency_field='currency_id',
                                        help='Monto total de la transacción')
    
    # Comisiones y cargos
    mp_fee = fields.Monetary(string='Comisión MP', currency_field='currency_id',
                            help='Comisión de Mercado Pago')
    
    shipping_cost = fields.Monetary(string='Costo Envío', currency_field='currency_id')
    
    financing_fee = fields.Monetary(string='Costo Financiero', currency_field='currency_id',
                                    help='Costo por cuotas/financiación')
    
    taxes_amount = fields.Monetary(string='Impuestos', currency_field='currency_id')
    
    # Monto neto (calculado)
    net_amount = fields.Monetary(string='Neto Recibido', 
                                 compute='_compute_net_amount',
                                 store=True,
                                 currency_field='currency_id',
                                 help='Monto neto acreditado después de comisiones')
    
    # Moneda
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True)
    currency_code = fields.Char(string='Código Moneda')
    
    # Método de pago
    payment_method_id = fields.Char(string='Método de Pago')
    payment_type = fields.Selection([
        ('credit_card', 'Tarjeta de Crédito'),
        ('debit_card', 'Tarjeta de Débito'),
        ('account_money', 'Dinero en Cuenta'),
        ('ticket', 'Efectivo'),
        ('bank_transfer', 'Transferencia'),
        ('prepaid_card', 'Tarjeta Prepaga'),
    ], string='Tipo de Pago')
    
    installments = fields.Integer(string='Cuotas', default=1)
    installment_amount = fields.Monetary(string='Monto por Cuota', currency_field='currency_id')
    
    # Emisor y marca
    issuer_id = fields.Char(string='Emisor ID')
    card_brand = fields.Char(string='Marca Tarjeta')
    authorization_code = fields.Char(string='Código Autorización')
    
    # Datos del pagador/comprador
    payer_id = fields.Char(string='ID Pagador', index=True)
    payer_email = fields.Char(string='Email Pagador')
    payer_first_name = fields.Char(string='Nombre')
    payer_last_name = fields.Char(string='Apellido')
    payer_identification_type = fields.Char(string='Tipo Doc')
    payer_identification_number = fields.Char(string='Número Doc', index=True)
    
    # Orden relacionada (si existe)
    order_id = fields.Char(string='ID Orden ML', index=True)
    
    # Datos adicionales
    description = fields.Char(string='Descripción')
    statement_descriptor = fields.Char(string='Descriptor')
    
    # JSON completo
    raw_json = fields.Text(string='JSON Completo')
    
    # Relaciones
    config_id = fields.Many2one('ml.api.config', string='Configuración ML', 
                                required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', 
                                required=True, 
                                default=lambda self: self.env.company)
    
    # Fecha de importación
    imported_date = fields.Datetime(string='Fecha Importación', 
                                   default=fields.Datetime.now,
                                   readonly=True)
    
    _sql_constraints = [
        ('payment_id_config_unique', 
         'unique(payment_id, config_id)', 
         'Este pago ya fue importado.')
    ]

    @api.depends('transaction_amount', 'mp_fee', 'shipping_cost', 'financing_fee', 'taxes_amount')
    def _compute_net_amount(self):
        """Calcula el monto neto recibido después de comisiones"""
        for payment in self:
            payment.net_amount = (
                payment.transaction_amount - 
                payment.mp_fee - 
                payment.shipping_cost - 
                payment.financing_fee -
                payment.taxes_amount
            )

    @api.model
    def import_payments(self, config_id, date_from, date_to):
        """
        Importa pagos desde Mercado Pago
        
        :param config_id: ID de la configuración ML
        :param date_from: Fecha desde (datetime)
        :param date_to: Fecha hasta (datetime)
        :return: Dict con estadísticas de importación
        """
        config = self.env['ml.api.config'].browse(config_id)
        if not config.exists():
            raise UserError(_('Configuración de API no encontrada'))
        
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'total_fetched': 0,
        }
        
        try:
            offset = 0
            limit = 50
            has_more = True
            
            while has_more:
                # Obtener user_id si no está disponible
                if not config.ml_user_id:
                    user_info = config._make_api_request('/users/me')
                    config.write({'ml_user_id': user_info.get('id')})
                
                # Parámetros para buscar pagos recibidos por el vendedor
                # El endpoint correcto para payments es con el collector_id (user_id del vendedor)
                params = {
                    'collector_id': config.ml_user_id,
                    'begin_date': date_from.strftime('%Y-%m-%dT%H:%M:%S.000-00:00'),
                    'end_date': date_to.strftime('%Y-%m-%dT%H:%M:%S.000-00:00'),
                    'sort': 'date_approved',
                    'criteria': 'desc',
                    'limit': limit,
                    'offset': offset,
                }
                
                # Usar el endpoint de búsqueda de pagos
                search_result = config._make_api_request('/v1/payments/search', params=params)
                
                results = search_result.get('results', [])
                paging = search_result.get('paging', {})
                
                stats['total_fetched'] += len(results)
                
                _logger.info(f"Procesando {len(results)} pagos (offset: {offset})")
                
                # Procesar cada pago
                for payment_data in results:
                    savepoint_name = f'import_payment_{offset}_{results.index(payment_data)}'
                    try:
                        # Crear savepoint
                        self.env.cr.execute(f'SAVEPOINT {savepoint_name}')
                        
                        self._import_single_payment(config, payment_data, stats)
                        
                        # Liberar savepoint
                        self.env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')
                        
                    except Exception as e:
                        # Rollback al savepoint
                        self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                        _logger.error(f"Error al importar pago {payment_data.get('id')}: {str(e)}")
                        stats['errors'] += 1
                
                # Verificar si hay más resultados
                total = paging.get('total', 0)
                offset += limit
                has_more = offset < total
                
                # Límite de seguridad
                if offset >= 5000:
                    _logger.warning("Alcanzado límite de 5000 pagos, deteniendo importación")
                    has_more = False
            
            # Actualizar fecha de última sincronización
            config.write({'last_sync_date': fields.Datetime.now()})
            
            _logger.info(f"Importación de pagos completada. Stats: {stats}")
            
        except Exception as e:
            _logger.error(f"Error en importación de pagos: {str(e)}")
            stats['errors'] += 1
            raise
        
        return stats

    @api.model
    def _import_single_payment(self, config, payment_data, stats):
        """Importa un único pago"""
        payment_id = str(payment_data.get('id'))
        
        # Verificar si ya existe
        existing = self.search([
            ('payment_id', '=', payment_id),
            ('config_id', '=', config.id)
        ], limit=1)
        
        if existing:
            # Actualizar existente
            values = self._prepare_payment_values(config, payment_data)
            existing.write(values)
            stats['updated'] += 1
        else:
            # Crear nuevo
            values = self._prepare_payment_values(config, payment_data)
            values['config_id'] = config.id
            self.create(values)
            stats['created'] += 1

    @api.model
    def _prepare_payment_values(self, config, payment_data):
        """Prepara los valores para crear/actualizar un pago"""
        
        # Obtener moneda
        currency_code = payment_data.get('currency_id', 'ARS')
        currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
        if not currency:
            currency = self.env['res.currency'].search([('name', '=', 'ARS')], limit=1)
        if not currency:
            currency = self.env.company.currency_id
        if not currency:
            raise UserError(_('No se encontró ninguna moneda en el sistema'))
        
        # Parsear fechas
        date_created = self._parse_mp_date(payment_data.get('date_created'))
        date_approved = self._parse_mp_date(payment_data.get('date_approved'))
        date_last_modified = self._parse_mp_date(payment_data.get('date_last_modified'))
        
        # Obtener datos del pagador
        payer = payment_data.get('payer', {})
        identification = payer.get('identification', {})
        
        # Calcular comisiones
        transaction_details = payment_data.get('transaction_details', {})
        mp_fee = abs(float(transaction_details.get('net_received_amount', 0) - 
                          payment_data.get('transaction_amount', 0)))
        
        # Preparar valores
        values = {
            'payment_id': str(payment_data.get('id')),
            'external_reference': payment_data.get('external_reference', False),
            'date_created': date_created,
            'date_approved': date_approved or fields.Datetime.now(),
            'date_last_modified': date_last_modified,
            'status': payment_data.get('status', 'pending'),
            'status_detail': payment_data.get('status_detail', False),
            'transaction_amount': float(payment_data.get('transaction_amount', 0)),
            'mp_fee': mp_fee,
            'shipping_cost': float(payment_data.get('shipping_cost', 0) or 0),
            'financing_fee': float(payment_data.get('fee_details', [{}])[0].get('amount', 0) if payment_data.get('fee_details') else 0),
            'taxes_amount': float(payment_data.get('taxes_amount', 0) or 0),
            'currency_id': currency.id,
            'currency_code': currency_code,
            'payment_method_id': payment_data.get('payment_method_id', False),
            'payment_type': payment_data.get('payment_type_id', False),
            'installments': payment_data.get('installments', 1),
            'installment_amount': float(payment_data.get('transaction_details', {}).get('installment_amount', 0) or 0),
            'issuer_id': payment_data.get('issuer_id', False),
            'authorization_code': payment_data.get('authorization_code', False),
            'payer_id': str(payer.get('id', '')),
            'payer_email': payer.get('email', False),
            'payer_first_name': payer.get('first_name', False),
            'payer_last_name': payer.get('last_name', False),
            'payer_identification_type': identification.get('type', False),
            'payer_identification_number': identification.get('number', False),
            'order_id': str(payment_data.get('order', {}).get('id', '')) if payment_data.get('order') else False,
            'description': payment_data.get('description', False),
            'statement_descriptor': payment_data.get('statement_descriptor', False),
            'raw_json': json.dumps(payment_data, indent=2, ensure_ascii=False),
        }
        
        return values

    @staticmethod
    def _parse_mp_date(date_string):
        """Parsea una fecha de Mercado Pago a datetime de Odoo"""
        if not date_string:
            return None
        
        try:
            # Formato: 2026-01-05T08:53:58.000-04:00
            # Remover timezone para simplificar
            if '+' in date_string or date_string.count('-') > 2:
                date_string = date_string.rsplit('-', 1)[0] if date_string.count('-') > 2 else date_string.split('+')[0]
            
            # Parsear
            dt = datetime.strptime(date_string.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            return dt
        except Exception as e:
            _logger.warning(f"Error parsing date {date_string}: {str(e)}")
            return None
