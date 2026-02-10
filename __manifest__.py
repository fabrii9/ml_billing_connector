# -*- coding: utf-8 -*-
{
    'name': 'Mercado Libre Billing Connector',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Integración con Mercado Libre para importar operaciones y datos de facturación',
    'description': """
        Mercado Libre Billing Connector
        ================================
        
        Este módulo permite:
        
        * Configurar conexión OAuth2 con Mercado Libre
        * Importar operaciones/ventas por rango de fechas
        * Visualizar datos fiscales del comprador para facturación
        * Desglose de importes (producto, comisiones, envíos, impuestos)
        * Manejo automático de renovación de tokens
        * Logs y auditoría completa
        
        Funcionalidades principales:
        
        - Configuración segura de credenciales OAuth2
        - Importación masiva de operaciones
        - Detalles de facturación (CUIT/DNI del comprador)
        - Desglose de cargos y comisiones
        - Idempotencia en importación
        - Rate limiting y manejo de errores
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'web',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ml_config_data.xml',
        'views/ml_oauth_templates.xml',
        'views/ml_operation_views.xml',
        'views/ml_payment_views.xml',
        'views/ml_payment_summary_views.xml',
        'views/ml_api_config_views.xml',
        'wizard/ml_import_operations_wizard_views.xml',
        'wizard/ml_import_payments_wizard_views.xml',
        'views/ml_menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['requests'],
    },
}
