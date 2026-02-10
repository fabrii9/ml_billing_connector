# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MlPaymentSummary(models.Model):
    _name = 'ml.payment.summary'
    _description = 'Resumen de Pagos de Mercado Pago'
    _order = 'date_approved desc'
    _rec_name = 'payment_id'

    # Identificación del pago
    payment_id = fields.Char(string='ID Pago MP', required=True, index=True,
                             help='ID del pago en Mercado Pago')
    
    # Tipo de operación
    operation_type = fields.Char(string='Tipo de Operación',
                                 help='Tipo de pago (credit_card, debit_card, etc)')
    
    # Monto
    amount = fields.Monetary(string='Valor de la Compra', currency_field='currency_id',
                            help='Monto de la transacción')
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True,
                                  default=lambda self: self.env.company.currency_id)
    
    # Fecha
    date_approved = fields.Datetime(string='Fecha de Aprobación',
                                   help='Fecha y hora de aprobación del pago')
    
    # Datos del comprador
    buyer_id = fields.Char(string='ID Comprador', help='ID del comprador en ML')
    buyer_nickname = fields.Char(string='Nickname Comprador')
    buyer_document_type = fields.Char(string='Tipo Documento',
                                     help='Tipo de documento (DNI, CUIT, etc)')
    buyer_document_number = fields.Char(string='Identificación del Comprador',
                                       help='DNI o CUIT del comprador')
    
    # Referencias
    order_id = fields.Char(string='ID Orden', help='ID de la orden en Mercado Libre')
    operation_id = fields.Many2one('ml.operation', string='Operación ML',
                                  ondelete='cascade',
                                  help='Referencia a la operación importada')
    config_id = fields.Many2one('ml.api.config', string='Configuración',
                               required=True, ondelete='cascade')
    
    # Metadatos
    company_id = fields.Many2one('res.company', string='Compañía',
                                required=True,
                                default=lambda self: self.env.company)
    imported_date = fields.Datetime(string='Fecha de Importación',
                                   default=fields.Datetime.now,
                                   readonly=True)
    
    _sql_constraints = [
        ('payment_id_unique', 'unique(payment_id, config_id)',
         'Este pago ya fue importado.')
    ]

    @api.model
    def create_from_operation(self, operation):
        """
        Crea registros de resumen de pagos desde una operación importada
        
        :param operation: Registro de ml.operation
        :return: Registros de ml.payment.summary creados
        """
        if not operation.raw_json:
            return self.env['ml.payment.summary']
        
        import json
        order_data = json.loads(operation.raw_json)
        payments_data = order_data.get('payments', [])
        
        if not payments_data:
            _logger.info(f"Orden {operation.order_id} no tiene pagos")
            return self.env['ml.payment.summary']
        
        # Obtener datos del comprador (DNI/CUIT)
        buyer_doc_type, buyer_doc_number = self._get_buyer_document(
            operation.config_id,
            operation.order_id,
            order_data.get('buyer', {}).get('id')
        )
        
        created_payments = self.env['ml.payment.summary']
        
        for payment_data in payments_data:
            payment_id = str(payment_data.get('id'))
            
            # Verificar si ya existe
            existing = self.search([
                ('payment_id', '=', payment_id),
                ('config_id', '=', operation.config_id.id)
            ], limit=1)
            
            if existing:
                _logger.debug(f"Pago {payment_id} ya existe, saltando")
                continue
            
            # Obtener moneda
            currency_code = payment_data.get('currency_id', 'ARS')
            currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
            if not currency:
                currency = self.env.company.currency_id
            
            # Crear registro
            vals = {
                'payment_id': payment_id,
                'operation_type': payment_data.get('payment_type', 'N/A'),
                'amount': payment_data.get('transaction_amount', 0.0),
                'currency_id': currency.id,
                'date_approved': self._parse_ml_date(payment_data.get('date_approved')),
                'buyer_id': str(order_data.get('buyer', {}).get('id', '')),
                'buyer_nickname': order_data.get('buyer', {}).get('nickname', ''),
                'buyer_document_type': buyer_doc_type,
                'buyer_document_number': buyer_doc_number,
                'order_id': operation.order_id,
                'operation_id': operation.id,
                'config_id': operation.config_id.id,
                'company_id': operation.company_id.id,
            }
            
            try:
                payment = self.create(vals)
                created_payments |= payment
                _logger.info(f"Pago {payment_id} creado exitosamente")
            except Exception as e:
                _logger.error(f"Error al crear pago {payment_id}: {str(e)}")
        
        return created_payments

    def _get_buyer_document(self, config, order_id, buyer_id):
        """
        Obtiene el tipo y número de documento del comprador
        
        :param config: Configuración de API
        :param order_id: ID de la orden
        :param buyer_id: ID del comprador
        :return: Tuple (tipo_documento, numero_documento)
        """
        try:
            # Intentar obtener billing_info de la orden
            billing_info = config._make_api_request(f'/orders/{order_id}/billing_info')
            
            doc_type = billing_info.get('doc_type', '')
            doc_number = billing_info.get('doc_number', '')
            
            if doc_number:
                return doc_type, doc_number
            
        except Exception as e:
            _logger.warning(f"No se pudo obtener billing_info de orden {order_id}: {str(e)}")
        
        # Si no hay billing_info, intentar desde buyer
        try:
            if buyer_id:
                buyer_info = config._make_api_request(f'/users/{buyer_id}')
                identification = buyer_info.get('identification', {})
                
                doc_type = identification.get('type', '')
                doc_number = identification.get('number', '')
                
                if doc_number:
                    return doc_type, doc_number
                
        except Exception as e:
            _logger.warning(f"No se pudo obtener datos de usuario {buyer_id}: {str(e)}")
        
        return '', ''

    def _parse_ml_date(self, date_str):
        """Convierte fecha de ML a datetime de Odoo (sin timezone)"""
        if not date_str:
            return False
        
        from dateutil import parser
        try:
            dt = parser.parse(date_str)
            # Convertir a naive datetime (sin timezone)
            if dt.tzinfo is not None:
                # Convertir a UTC y quitar timezone
                dt = dt.astimezone(None).replace(tzinfo=None)
            return dt
        except:
            return False
