# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MlImportOperationsWizard(models.TransientModel):
    _name = 'ml.import.operations.wizard'
    _description = 'Wizard para Importar Operaciones de Mercado Libre'

    config_id = fields.Many2one(
        'ml.api.config',
        string='Configuración ML',
        required=True,
        default=lambda self: self.env['ml.api.config'].get_active_config(),
    )
    
    date_from = fields.Datetime(
        string='Fecha Desde',
        required=True,
        default=lambda self: fields.Datetime.now() - timedelta(days=30),
        help='Fecha de inicio del rango de importación'
    )
    
    date_to = fields.Datetime(
        string='Fecha Hasta',
        required=True,
        default=fields.Datetime.now,
        help='Fecha final del rango de importación'
    )
    
    limit_per_page = fields.Integer(
        string='Resultados por Página',
        default=50,
        help='Cantidad de órdenes a procesar por solicitud (máx. 50)'
    )
    
    # Resultados
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('importing', 'Importando'),
        ('done', 'Completado'),
        ('error', 'Error'),
    ], string='Estado', default='draft', readonly=True)
    
    result_message = fields.Text(string='Resultado', readonly=True)
    
    # Estadísticas
    total_fetched = fields.Integer(string='Total Consultadas', readonly=True)
    total_created = fields.Integer(string='Nuevas Creadas', readonly=True)
    total_updated = fields.Integer(string='Actualizadas', readonly=True)
    total_errors = fields.Integer(string='Errores', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Valida que las fechas sean coherentes"""
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_('La fecha desde debe ser anterior a la fecha hasta.'))
            
            # Validar que no sea un rango muy grande (más de 90 días)
            delta = record.date_to - record.date_from
            if delta.days > 90:
                raise UserError(_('El rango de fechas no puede ser mayor a 90 días. '
                                 'Por favor, divida la importación en períodos más cortos.'))

    @api.constrains('limit_per_page')
    def _check_limit(self):
        """Valida el límite por página"""
        for record in self:
            if record.limit_per_page < 1 or record.limit_per_page > 50:
                raise UserError(_('El límite por página debe estar entre 1 y 50.'))

    def action_import_operations(self):
        """Ejecuta la importación de operaciones"""
        self.ensure_one()
        
        # Validar que la configuración esté conectada
        if self.config_id.state != 'connected':
            raise UserError(_('La configuración de Mercado Libre no está conectada. '
                             'Por favor, conecte primero desde Configuración.'))
        
        try:
            # Actualizar estado
            self.write({'state': 'importing'})
            
            # Ejecutar importación
            stats = self.env['ml.operation'].import_operations_from_ml(
                config=self.config_id,
                date_from=self.date_from,
                date_to=self.date_to,
                limit=self.limit_per_page,
            )
            
            # Actualizar estadísticas
            self.write({
                'state': 'done',
                'total_fetched': stats.get('total_fetched', 0),
                'total_created': stats.get('created', 0),
                'total_updated': stats.get('updated', 0),
                'total_errors': stats.get('errors', 0),
                'result_message': self._format_result_message(stats),
            })
            
            # Mostrar resultado y abrir operaciones importadas
            return self._show_imported_operations()
            
        except Exception as e:
            error_msg = f"Error durante la importación: {str(e)}"
            _logger.error(error_msg)
            
            self.write({
                'state': 'error',
                'result_message': error_msg,
            })
            
            raise UserError(_(error_msg))

    def _format_result_message(self, stats):
        """Formatea el mensaje de resultado"""
        message = "Importación completada:\n\n"
        message += f"• Órdenes consultadas: {stats.get('total_fetched', 0)}\n"
        message += f"• Nuevas operaciones creadas: {stats.get('created', 0)}\n"
        message += f"• Operaciones actualizadas: {stats.get('updated', 0)}\n"
        
        if stats.get('errors', 0) > 0:
            message += f"• Errores: {stats.get('errors', 0)}\n"
            message += "\nRevisar logs para más detalles sobre los errores."
        
        return message

    def _show_imported_operations(self):
        """Muestra las operaciones importadas en este wizard"""
        self.ensure_one()
        
        # Buscar operaciones del período
        operations = self.env['ml.operation'].search([
            ('config_id', '=', self.config_id.id),
            ('date_created', '>=', self.date_from),
            ('date_created', '<=', self.date_to),
        ])
        
        return {
            'name': _('Operaciones Importadas'),
            'type': 'ir.actions.act_window',
            'res_model': 'ml.operation',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', operations.ids)],
            'context': {
                'default_config_id': self.config_id.id,
            },
            'target': 'current',
        }

    def action_view_result(self):
        """Vuelve a mostrar las operaciones importadas"""
        return self._show_imported_operations()

    def action_reset(self):
        """Resetea el wizard para una nueva importación"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'result_message': False,
            'total_fetched': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
