# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MlOAuthController(http.Controller):
    
    @http.route('/ml/oauth/callback', type='http', auth='user', website=True)
    def ml_oauth_callback(self, **kwargs):
        """
        Callback endpoint para OAuth2 de Mercado Libre
        Recibe el código de autorización y lo intercambia por tokens
        """
        code = kwargs.get('code')
        error = kwargs.get('error')
        
        if error:
            error_description = kwargs.get('error_description', 'Error desconocido')
            _logger.error(f"Error en OAuth ML: {error} - {error_description}")
            
            return request.render('ml_billing_connector.oauth_error', {
                'error': error,
                'error_description': error_description,
            })
        
        if not code:
            _logger.error("No se recibió código de autorización")
            return request.render('ml_billing_connector.oauth_error', {
                'error': 'no_code',
                'error_description': 'No se recibió código de autorización',
            })
        
        try:
            # Obtener la configuración activa
            config = request.env['ml.api.config'].sudo().get_active_config()
            
            # Intercambiar código por token
            config.exchange_code_for_token(code)
            
            _logger.info(f"OAuth exitoso para config {config.id}")
            
            return request.render('ml_billing_connector.oauth_success', {
                'config': config,
            })
            
        except Exception as e:
            _logger.error(f"Error al procesar callback OAuth: {str(e)}")
            return request.render('ml_billing_connector.oauth_error', {
                'error': 'exchange_failed',
                'error_description': str(e),
            })
