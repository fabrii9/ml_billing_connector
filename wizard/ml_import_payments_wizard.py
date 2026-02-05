# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class MlImportPaymentsWizard(models.TransientModel):
    _name = 'ml.import.payments.wizard'
    _description = 'Wizard para Importar Pagos de Mercado Pago'

    config_id = fields.Many2one('ml.api.config', string='Configuración ML',
                                required=True,
                                default=lambda self: self.env['ml.api.config'].search([], limit=1))
    
    date_from = fields.Datetime(string='Fecha Desde', required=True,
                                default=lambda self: fields.Datetime.now() - timedelta(days=30))
    
    date_to = fields.Datetime(string='Fecha Hasta', required=True,
                              default=fields.Datetime.now)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_('La fecha desde no puede ser mayor que la fecha hasta'))

    def action_import(self):
        """Ejecuta la importación de pagos"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError(_('Debe configurar primero la conexión con Mercado Pago'))
        
        # Verificar que tengamos el access token de Mercado Pago
        if not self.config_id.mp_access_token:
            raise UserError(_('Debe configurar el Access Token de Mercado Pago en la configuración'))
        
        try:
            # Importar pagos
            stats = self.env['ml.payment'].import_payments(
                self.config_id.id,
                self.date_from,
                self.date_to
            )
            
            # Mostrar resultado
            message = _(
                'Importación completada:\n'
                '- Pagos nuevos: %(created)s\n'
                '- Pagos actualizados: %(updated)s\n'
                '- Errores: %(errors)s\n'
                '- Total procesados: %(total)s'
            ) % {
                'created': stats['created'],
                'updated': stats['updated'],
                'errors': stats['errors'],
                'total': stats['total_fetched'],
            }
            
            # Retornar acción para ver pagos importados
            return {
                'type': 'ir.actions.act_window',
                'name': _('Pagos Importados'),
                'res_model': 'ml.payment',
                'view_mode': 'tree,form',
                'domain': [('config_id', '=', self.config_id.id)],
                'context': {
                    'search_default_approved': 1,
                },
            }
            
        except Exception as e:
            raise UserError(_(f'Error durante la importación: {str(e)}'))
