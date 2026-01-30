# Comandos Útiles - ML Billing Connector

## Instalación y Actualización

### Instalar el módulo
```bash
# Opción 1: Desde línea de comandos
./odoo-bin -d tu_database -i ml_billing_connector --stop-after-init

# Opción 2: Con actualización
./odoo-bin -d tu_database -u ml_billing_connector --stop-after-init

# Opción 3: Desde interfaz de Odoo
# Apps > Update Apps List > Buscar "Mercado Libre" > Instalar
```

### Actualizar el módulo después de cambios
```bash
./odoo-bin -d tu_database -u ml_billing_connector --stop-after-init
```

### Desinstalar
```bash
# Mejor desde interfaz: Apps > ML Billing Connector > Uninstall
# O desde línea de comandos:
./odoo-bin -d tu_database --uninstall ml_billing_connector --stop-after-init
```

---

## Testing y Debugging

### Activar modo desarrollador
```bash
# Desde interfaz: Settings > Activate Developer Mode
# O agregar ?debug=1 a la URL
```

### Ver logs en tiempo real
```bash
# Si Odoo corre como servicio
sudo journalctl -u odoo -f

# Si Odoo corre con odoo-bin
# Los logs aparecen en la terminal o en el archivo especificado en config
tail -f /var/log/odoo/odoo.log
```

### Shell de Odoo (para testing manual)
```bash
./odoo-bin shell -d tu_database -c /path/to/odoo.conf

# Luego en el shell de Python:
>>> config = env['ml.api.config'].browse(1)
>>> config.action_test_connection()
>>> orders = env['ml.operation'].search([])
>>> print(orders)
```

---

## Gestión de Base de Datos

### Backup antes de instalar
```bash
pg_dump tu_database > backup_antes_ml_$(date +%Y%m%d).sql
```

### Restaurar backup si algo sale mal
```bash
dropdb tu_database
createdb tu_database
psql tu_database < backup_antes_ml_20260130.sql
```

---

## Comandos de Python para Testing

### Desde Odoo Shell

```python
# Obtener configuración activa
config = env['ml.api.config'].get_active_config()
print(config.name, config.state)

# Test de conexión
try:
    user_info = config._make_api_request('/users/me')
    print(f"Usuario: {user_info['nickname']}, ID: {user_info['id']}")
except Exception as e:
    print(f"Error: {e}")

# Buscar órdenes manualmente
from datetime import datetime, timedelta
params = {
    'seller': config.seller_id,
    'order.date_created.from': (datetime.now() - timedelta(days=7)).isoformat(),
    'order.date_created.to': datetime.now().isoformat(),
    'limit': 5
}
orders = config._make_api_request('/orders/search', params=params)
print(f"Órdenes encontradas: {orders['paging']['total']}")
print(f"IDs: {orders['results']}")

# Detalle de una orden específica
order_id = '2000003823456789'  # Reemplazar con un ID real
order_detail = config._make_api_request(f'/orders/{order_id}')
print(json.dumps(order_detail, indent=2))

# Importar operaciones de un período
from datetime import datetime, timedelta
stats = env['ml.operation'].import_operations_from_ml(
    config=config,
    date_from=datetime.now() - timedelta(days=7),
    date_to=datetime.now(),
    limit=50
)
print(f"Stats: {stats}")

# Listar operaciones importadas
operations = env['ml.operation'].search([], limit=10, order='date_created desc')
for op in operations:
    print(f"{op.order_id} - {op.buyer_name} - ${op.net_amount}")

# Refrescar token manualmente
config.refresh_access_token()
print(f"Token expiración: {config.token_expiration}")

# Ver comisiones de una operación
operation = env['ml.operation'].browse(1)  # ID de una operación
for fee in operation.fee_ids:
    print(f"{fee.description}: ${fee.amount}")
```

---

## Verificación de Permisos

### Asignar grupo ML Manager a usuario
```python
# Desde Odoo Shell
user = env['res.users'].search([('login', '=', 'admin')], limit=1)
ml_manager_group = env.ref('ml_billing_connector.group_ml_manager')
user.write({'groups_id': [(4, ml_manager_group.id)]})
print(f"Usuario {user.name} ahora es ML Manager")
```

### Verificar permisos de un usuario
```python
user = env.user
if user.has_group('ml_billing_connector.group_ml_manager'):
    print("Usuario es ML Manager")
elif user.has_group('ml_billing_connector.group_ml_user'):
    print("Usuario es ML User")
else:
    print("Usuario no tiene permisos de ML")
```

---

## Limpieza y Mantenimiento

### Borrar operaciones de prueba
```python
# Desde Odoo Shell
# CUIDADO: Esto borra registros permanentemente

# Borrar operaciones de un período específico
from datetime import datetime
operations = env['ml.operation'].search([
    ('date_created', '>=', '2026-01-01'),
    ('date_created', '<=', '2026-01-31')
])
print(f"Se borrarán {len(operations)} operaciones")
# operations.unlink()  # Descomentar para ejecutar

# Borrar todas las operaciones (usar con precaución)
# all_operations = env['ml.operation'].search([])
# all_operations.unlink()
```

### Limpiar configuraciones inactivas
```python
# Desde Odoo Shell
inactive_configs = env['ml.api.config'].search([('active', '=', False)])
print(f"Configuraciones inactivas: {len(inactive_configs)}")
# inactive_configs.unlink()  # Descomentar para ejecutar
```

---

## Scheduled Actions (Cron Jobs)

### Crear acción programada para importación diaria
```python
# Desde Odoo Shell o crear manualmente en interfaz

cron_vals = {
    'name': 'ML: Importar Operaciones Diarias',
    'model_id': env.ref('ml_billing_connector.model_ml_operation').id,
    'state': 'code',
    'code': """
from datetime import datetime, timedelta

config = env['ml.api.config'].get_active_config()
date_from = datetime.now() - timedelta(days=1)
date_to = datetime.now()

try:
    stats = env['ml.operation'].import_operations_from_ml(
        config=config,
        date_from=date_from,
        date_to=date_to,
        limit=50
    )
    _logger.info(f"ML Import Cron: {stats}")
except Exception as e:
    _logger.error(f"ML Import Cron Error: {e}")
""",
    'interval_number': 1,
    'interval_type': 'days',
    'numbercall': -1,
    'active': True,
}

cron = env['ir.cron'].create(cron_vals)
print(f"Cron creado: {cron.name}")
```

### Ver scheduled actions del módulo
```bash
# Desde interfaz: Settings > Technical > Automation > Scheduled Actions
# Filtrar por modelo: ml.operation
```

---

## Exportar/Importar Datos

### Exportar operaciones a CSV
```python
# Desde Odoo Shell
import csv

operations = env['ml.operation'].search([])

with open('/tmp/ml_operations.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Order ID', 'Fecha', 'Comprador', 'Doc Type', 'Doc Number', 'Total', 'Neto'])
    
    for op in operations:
        writer.writerow([
            op.order_id,
            op.date_created.strftime('%Y-%m-%d') if op.date_created else '',
            op.buyer_name or '',
            op.buyer_doc_type or '',
            op.buyer_doc_number or '',
            op.total_amount,
            op.net_amount
        ])

print(f"Exportadas {len(operations)} operaciones a /tmp/ml_operations.csv")
```

---

## Verificación de Integridad

### Verificar configuración OAuth
```python
config = env['ml.api.config'].get_active_config()

checks = {
    'Client ID presente': bool(config.client_id),
    'Client Secret presente': bool(config.client_secret),
    'Access Token presente': bool(config.access_token),
    'Refresh Token presente': bool(config.refresh_token),
    'Seller ID presente': bool(config.seller_id),
    'Estado conectado': config.state == 'connected',
    'Token no expirado': config.token_expiration > datetime.now() if config.token_expiration else False,
}

for check, result in checks.items():
    status = '✓' if result else '✗'
    print(f"{status} {check}")
```

### Verificar operaciones con datos faltantes
```python
# Operaciones sin CUIT/DNI
without_doc = env['ml.operation'].search([
    '|',
    ('buyer_doc_type', '=', False),
    ('buyer_doc_number', '=', False)
])
print(f"Operaciones sin documento: {len(without_doc)}")

# Operaciones sin billing info
without_billing = env['ml.operation'].search([
    ('raw_billing_info', '=', False)
])
print(f"Operaciones sin billing info: {len(without_billing)}")

# Operaciones sin comisiones
without_fees = env['ml.operation'].search([
    ('fee_ids', '=', False)
])
print(f"Operaciones sin comisiones: {len(without_fees)}")
```

---

## Performance y Optimización

### Ver queries lentas
```bash
# Activar log de queries SQL lentas en odoo.conf
# log_level = debug
# log_db_level = debug

# Luego revisar logs
grep "Query" /var/log/odoo/odoo.log | grep -v "SELECT 1"
```

### Índices en base de datos
```sql
-- Verificar índices existentes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'ml_operation';

-- Si es necesario, agregar índices manualmente:
CREATE INDEX IF NOT EXISTS ml_operation_date_created_idx ON ml_operation (date_created);
CREATE INDEX IF NOT EXISTS ml_operation_buyer_doc_number_idx ON ml_operation (buyer_doc_number);
```

---

## Troubleshooting Rápido

### Error: ModuleNotFoundError: No module named 'requests'
```bash
pip3 install requests
# o con el entorno virtual de Odoo activo:
source /path/to/odoo-venv/bin/activate
pip install requests
```

### Error: No module named 'ml_billing_connector'
```bash
# Verificar que el módulo esté en addons_path
./odoo-bin -c /path/to/odoo.conf --stop-after-init | grep addons_path

# Actualizar lista de apps
# Apps > Update Apps List
```

### Error: Access denied
```bash
# Verificar permisos del usuario
# Settings > Users > Seleccionar usuario > Tab "Access Rights"
# Asegurarse de que tenga grupo "ML User" o "ML Manager"
```

### Error: web.base.url no configurado
```python
# Desde Odoo Shell
env['ir.config_parameter'].set_param('web.base.url', 'https://tu-dominio.com')
```

---

## URLs Útiles

### Desarrollo
- Odoo Shell: `./odoo-bin shell -d DB`
- Server con debug: `./odoo-bin -d DB --dev=all`
- Debug mode: `https://tu-odoo.com/web?debug=1`

### Mercado Libre
- Portal Developers: https://developers.mercadolibre.com.ar/
- Mis Aplicaciones: https://developers.mercadolibre.com.ar/apps
- Documentación API: https://developers.mercadolibre.com.ar/es_ar/api-docs-es
- Test de API: https://developers.mercadolibre.com.ar/es_ar/api-testing

---

## Scripts Útiles

### Script de backup automático antes de instalar
```bash
#!/bin/bash
# backup_before_ml_install.sh

DB_NAME="tu_database"
BACKUP_DIR="/backups/odoo"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "Creando backup de $DB_NAME..."
pg_dump $DB_NAME | gzip > $BACKUP_DIR/${DB_NAME}_before_ml_${DATE}.sql.gz

if [ $? -eq 0 ]; then
    echo "✓ Backup creado: ${DB_NAME}_before_ml_${DATE}.sql.gz"
    echo "Ahora puedes instalar ml_billing_connector"
else
    echo "✗ Error al crear backup"
    exit 1
fi
```

### Script de verificación post-instalación
```bash
#!/bin/bash
# verify_ml_installation.sh

DB_NAME="tu_database"

echo "Verificando instalación de ml_billing_connector..."

./odoo-bin shell -d $DB_NAME << EOF
# Verificar que el módulo esté instalado
module = env['ir.module.module'].search([('name', '=', 'ml_billing_connector')])
if module and module.state == 'installed':
    print("✓ Módulo instalado correctamente")
    
    # Verificar modelos
    models = ['ml.api.config', 'ml.operation', 'ml.operation.fee']
    for model in models:
        if env[model]:
            print(f"✓ Modelo {model} disponible")
    
    # Verificar vistas
    views = env['ir.ui.view'].search([('model', 'in', models)])
    print(f"✓ {len(views)} vistas creadas")
    
    # Verificar permisos
    groups = env['res.groups'].search([('category_id.name', '=', 'Mercado Libre')])
    print(f"✓ {len(groups)} grupos de seguridad creados")
else:
    print("✗ Módulo no instalado")
EOF
```

---

## Contacto y Soporte

Si encuentras problemas o necesitas ayuda:

1. Revisa la documentación: README.md, INSTALLATION.md, API_RESPONSES.md
2. Consulta logs de Odoo para más detalles
3. Usa estos comandos para debugging
4. Contacta soporte: soporte@tuempresa.com

---

**Nota**: Reemplaza `tu_database`, rutas y URLs con tus valores reales.
