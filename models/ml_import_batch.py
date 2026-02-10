# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MlImportBatch(models.Model):
    _name = 'ml.import.batch'
    _description = 'Lote de Importación de Mercado Libre'
    _order = 'date_import desc'
    _rec_name = 'display_name'

    name = fields.Char(string='Número de Lote', required=True, readonly=True, 
                      default='Nuevo', copy=False)
    display_name = fields.Char(string='Nombre', compute='_compute_display_name', store=True)
    
    date_import = fields.Datetime(string='Fecha de Importación', 
                                  default=fields.Datetime.now,
                                  required=True, readonly=True)
    
    user_id = fields.Many2one('res.users', string='Importado por',
                             default=lambda self: self.env.user,
                             readonly=True)
    
    config_id = fields.Many2one('ml.api.config', string='Configuración ML',
                               required=True, readonly=True)
    
    # Rango de fechas consultado
    date_from = fields.Datetime(string='Desde', required=True, readonly=True)
    date_to = fields.Datetime(string='Hasta', required=True, readonly=True)
    
    # Estadísticas
    total_operations = fields.Integer(string='Operaciones Importadas', readonly=True)
    total_payments = fields.Integer(string='Pagos Creados', readonly=True)
    total_errors = fields.Integer(string='Errores', readonly=True)
    
    state = fields.Selection([
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ], string='Estado', default='in_progress', readonly=True)
    
    # Relaciones
    payment_ids = fields.One2many('ml.payment.summary', 'import_batch_id',
                                 string='Pagos de este Lote')
    payment_count = fields.Integer(string='Cantidad de Pagos',
                                   compute='_compute_payment_count')
    
    notes = fields.Text(string='Notas')
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                required=True,
                                default=lambda self: self.env.company,
                                readonly=True)

    @api.depends('name', 'date_import')
    def _compute_display_name(self):
        for batch in self:
            if batch.date_import:
                date_str = fields.Datetime.context_timestamp(
                    batch, batch.date_import
                ).strftime('%d/%m/%Y %H:%M')
                batch.display_name = f"{batch.name} - {date_str}"
            else:
                batch.display_name = batch.name

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for batch in self:
            batch.payment_count = len(batch.payment_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            # Generar número de lote secuencial
            vals['name'] = self.env['ir.sequence'].next_by_code('ml.import.batch') or 'LOTE/001'
        return super().create(vals)

    def action_view_payments(self):
        """Abre la vista de pagos filtrada por este lote"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pagos del {self.display_name}',
            'res_model': 'ml.payment.summary',
            'view_mode': 'tree,form',
            'domain': [('import_batch_id', '=', self.id)],
            'context': {'default_import_batch_id': self.id},
        }

    def action_export_payments(self):
        """Exporta los pagos de este lote a Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/export/xlsx?model=ml.payment.summary&domain=[("import_batch_id","=",{self.id})]',
            'target': 'new',
        }
