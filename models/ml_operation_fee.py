# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MlOperationFee(models.Model):
    _name = 'ml.operation.fee'
    _description = 'Comisión/Cargo de Operación ML'
    _order = 'sequence, id'

    operation_id = fields.Many2one('ml.operation', string='Operación', 
                                    required=True, ondelete='cascade')
    
    sequence = fields.Integer(string='Secuencia', default=10)
    
    fee_type = fields.Selection([
        ('marketplace_fee', 'Comisión ML'),
        ('shipping_cost', 'Costo Envío'),
        ('payment_fee', 'Comisión Pago'),
        ('tax', 'Impuesto'),
        ('refund', 'Reembolso'),
        ('other', 'Otro'),
    ], string='Tipo', required=True, default='other')
    
    description = fields.Char(string='Descripción', required=True)
    
    amount = fields.Monetary(string='Monto', currency_field='currency_id', required=True)
    
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True)
    
    notes = fields.Text(string='Notas')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.description}: {record.amount} {record.currency_id.symbol}"
            result.append((record.id, name))
        return result
