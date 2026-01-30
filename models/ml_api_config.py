# -*- coding: utf-8 -*-
import requests
import logging
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MlApiConfig(models.Model):
    _name = 'ml.api.config'
    _description = 'Configuración API Mercado Libre'
    _rec_name = 'name'

    name = fields.Char(string='Nombre', required=True, default='Configuración ML')
    active = fields.Boolean(string='Activo', default=True)
    
    # OAuth2 Credentials
    client_id = fields.Char(string='Client ID', required=True, help='App ID de Mercado Libre')
    client_secret = fields.Char(string='Client Secret', required=True, help='Secret Key de Mercado Libre')
    
    # Tokens
    access_token = fields.Char(string='Access Token', readonly=True, copy=False)
    refresh_token = fields.Char(string='Refresh Token', readonly=True, copy=False)
    token_expiration = fields.Datetime(string='Expiración Token', readonly=True, copy=False)
    
    # Seller Info
    seller_id = fields.Char(string='Seller ID', readonly=True, help='ID del vendedor en ML')
    
    # Environment
    environment = fields.Selection([
        ('production', 'Producción'),
        ('sandbox', 'Sandbox (Testing)'),
    ], string='Entorno', default='production', required=True)
    
    # URLs
    redirect_uri = fields.Char(
        string='Redirect URI',
        compute='_compute_redirect_uri',
        store=True,
        help='URI de retorno después de la autorización OAuth'
    )
    
    # Status
    state = fields.Selection([
        ('disconnected', 'Desconectado'),
        ('connected', 'Conectado'),
        ('expired', 'Token Expirado'),
    ], string='Estado', default='disconnected', readonly=True)
    
    # API Configuration
    country_code = fields.Selection([
        ('MLA', 'Argentina'),
        ('MLB', 'Brasil'),
        ('MLC', 'Chile'),
        ('MLM', 'México'),
        ('MLU', 'Uruguay'),
        ('MCO', 'Colombia'),
        ('MLV', 'Venezuela'),
        ('MPE', 'Perú'),
    ], string='País', default='MLA', required=True)
    
    # Logs
    last_sync_date = fields.Datetime(string='Última Sincronización', readonly=True)
    last_error = fields.Text(string='Último Error', readonly=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Compañía', 
                                  default=lambda self: self.env.company, required=True)

    _sql_constraints = [
        ('unique_config_company', 'unique(company_id)', 'Solo puede existir una configuración activa por compañía!')
    ]

    @api.depends('environment')
    def _compute_redirect_uri(self):
        """Calcula la URI de redirección basada en la URL base de Odoo"""
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record.redirect_uri = f"{base_url}/ml/oauth/callback"

    def get_api_base_url(self):
        """Retorna la URL base de la API según el entorno"""
        self.ensure_one()
        if self.environment == 'sandbox':
            return 'https://api.mercadolibre.com'  # ML no tiene sandbox separado
        return 'https://api.mercadolibre.com'

    def get_authorization_url(self):
        """Genera la URL de autorización OAuth2"""
        self.ensure_one()
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
        }
        auth_url = f"https://auth.mercadolibre.com.ar/authorization?{urlencode(params)}"
        return auth_url

    def action_connect_ml(self):
        """Abre la URL de autorización de Mercado Libre"""
        self.ensure_one()
        if not self.client_id or not self.client_secret:
            raise UserError(_('Por favor, configure Client ID y Client Secret antes de conectar.'))
        
        auth_url = self.get_authorization_url()
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }

    def exchange_code_for_token(self, code):
        """Intercambia el código de autorización por tokens de acceso"""
        self.ensure_one()
        
        url = f"{self.get_api_base_url()}/oauth/token"
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            # Calcular expiración
            expires_in = token_data.get('expires_in', 21600)  # Default 6 horas
            expiration = datetime.now() + timedelta(seconds=expires_in)
            
            # Actualizar configuración
            self.write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_expiration': expiration,
                'seller_id': str(token_data.get('user_id', '')),
                'state': 'connected',
                'last_error': False,
            })
            
            _logger.info(f"ML OAuth: Token obtenido exitosamente para seller_id: {self.seller_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error al obtener token: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nDetalle: {json.dumps(error_detail, indent=2)}"
                except:
                    error_msg += f"\nRespuesta: {e.response.text}"
            
            self.write({
                'last_error': error_msg,
                'state': 'disconnected',
            })
            _logger.error(error_msg)
            raise UserError(_(error_msg))

    def refresh_access_token(self):
        """Refresca el access token usando el refresh token"""
        self.ensure_one()
        
        if not self.refresh_token:
            raise UserError(_('No hay refresh token disponible. Debe conectar nuevamente.'))
        
        url = f"{self.get_api_base_url()}/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            # Calcular expiración
            expires_in = token_data.get('expires_in', 21600)
            expiration = datetime.now() + timedelta(seconds=expires_in)
            
            # Actualizar configuración
            self.write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_expiration': expiration,
                'state': 'connected',
                'last_error': False,
            })
            
            _logger.info(f"ML OAuth: Token refrescado exitosamente para seller_id: {self.seller_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error al refrescar token: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nDetalle: {json.dumps(error_detail, indent=2)}"
                except:
                    error_msg += f"\nRespuesta: {e.response.text}"
            
            self.write({
                'last_error': error_msg,
                'state': 'expired',
            })
            _logger.error(error_msg)
            raise UserError(_(error_msg))

    def action_refresh_token(self):
        """Acción para refrescar el token manualmente"""
        self.ensure_one()
        self.refresh_access_token()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Token refrescado correctamente'),
                'type': 'success',
                'sticky': False,
            }
        }

    def check_and_refresh_token(self):
        """Verifica si el token está por expirar y lo refresca automáticamente"""
        self.ensure_one()
        
        if not self.access_token:
            raise UserError(_('No hay token disponible. Debe conectar con Mercado Libre primero.'))
        
        # Refrescar si expira en menos de 5 minutos
        if self.token_expiration:
            time_to_expiry = self.token_expiration - datetime.now()
            if time_to_expiry.total_seconds() < 300:  # 5 minutos
                _logger.info("Token por expirar, refrescando automáticamente...")
                self.refresh_access_token()
        
        return True

    def _make_api_request(self, endpoint, method='GET', params=None, data=None, retry_on_401=True):
        """
        Realiza una petición a la API de Mercado Libre con manejo de errores
        
        :param endpoint: Endpoint de la API (ej: '/orders/search')
        :param method: Método HTTP (GET, POST, PUT, DELETE)
        :param params: Parámetros de query string
        :param data: Datos para POST/PUT
        :param retry_on_401: Si True, intenta refrescar token en caso de 401
        :return: Respuesta JSON
        """
        self.ensure_one()
        self.check_and_refresh_token()
        
        url = f"{self.get_api_base_url()}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, params=params, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, params=params, json=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            # Manejo de rate limiting
            if response.status_code == 429:
                _logger.warning("Rate limit alcanzado, esperando antes de reintentar...")
                raise UserError(_('Límite de peticiones alcanzado. Por favor, intente más tarde.'))
            
            # Manejo de token expirado
            if response.status_code == 401 and retry_on_401:
                _logger.info("Token expirado (401), intentando refrescar...")
                self.refresh_access_token()
                # Reintentar la petición una vez
                return self._make_api_request(endpoint, method, params, data, retry_on_401=False)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error en petición API ({method} {endpoint}): {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nDetalle: {json.dumps(error_detail, indent=2)}"
                except:
                    error_msg += f"\nRespuesta: {e.response.text}"
            
            self.write({'last_error': error_msg})
            _logger.error(error_msg)
            raise UserError(_(error_msg))

    def action_test_connection(self):
        """Prueba la conexión con la API de Mercado Libre"""
        self.ensure_one()
        
        try:
            # Obtener información del usuario
            user_info = self._make_api_request('/users/me')
            
            message = f"Conexión exitosa!\n\n"
            message += f"Usuario: {user_info.get('nickname', 'N/A')}\n"
            message += f"ID: {user_info.get('id', 'N/A')}\n"
            message += f"Email: {user_info.get('email', 'N/A')}\n"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Prueba de Conexión'),
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error de Conexión'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    @api.model
    def get_active_config(self):
        """Obtiene la configuración activa de la compañía actual"""
        config = self.search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)
        
        if not config:
            raise UserError(_('No hay una configuración activa de Mercado Libre. Por favor, configure primero.'))
        
        return config
