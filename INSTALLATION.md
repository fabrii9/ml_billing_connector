# Guía de Instalación y Configuración
# Mercado Libre Billing Connector

## Pre-requisitos

### 1. Aplicación en Mercado Libre

Antes de comenzar, necesitas crear una aplicación en el portal de desarrolladores:

URL: https://developers.mercadolibre.com.ar/

Pasos:
1. Inicia sesión con tu cuenta de Mercado Libre
2. Ve a "Mis aplicaciones"
3. Clic en "Crear nueva aplicación"
4. Completa el formulario:
   - Nombre: "Odoo Integration" (o el que prefieras)
   - Descripción corta: "Integración con sistema Odoo"
   - Redirect URI: https://TU-DOMINIO-ODOO.com/ml/oauth/callback
     IMPORTANTE: Debe ser HTTPS y coincidir exactamente con tu dominio
   - Scopes: read, offline_access

5. Guarda y anota:
   - Client ID (App ID)
   - Client Secret (Secret Key)

### 2. Configuración de Odoo

Asegúrate de que el parámetro web.base.url esté correctamente configurado:

```bash
# En línea de comandos de Odoo o en Settings > Technical > Parameters > System Parameters
# Key: web.base.url
# Value: https://tu-dominio-odoo.com
```

## Instalación del Módulo

### Opción 1: Instalación Manual

```bash
# 1. Copiar el módulo a addons
cd /path/to/odoo/addons
cp -r /path/to/ml_billing_connector .

# 2. Verificar permisos
chown -R odoo:odoo ml_billing_connector

# 3. Reiniciar Odoo
sudo systemctl restart odoo
# o si usas odoo-bin directamente:
./odoo-bin -u ml_billing_connector -d tu_database
```

### Opción 2: Desde interfaz de Odoo

1. Activar modo desarrollador: Settings > Activate Developer Mode
2. Apps > Update Apps List
3. Buscar "Mercado Libre"
4. Instalar

## Configuración Inicial

### Paso 1: Crear Configuración

1. Ir a: **Mercado Libre > Configuración > Conexión API**
2. Crear nuevo registro
3. Completar:

```
Nombre: Configuración ML Principal
Entorno: Producción
País: Argentina (MLA)  # Ajustar según tu país
Client ID: [TU_CLIENT_ID_DE_ML]
Client Secret: [TU_CLIENT_SECRET_DE_ML]
```

4. Guardar

### Paso 2: Conectar

1. En el formulario guardado, clic en botón **"Conectar con Mercado Libre"**
2. Se abrirá una ventana de Mercado Libre
3. Iniciar sesión si es necesario
4. Autorizar la aplicación
5. Serás redirigido a Odoo con confirmación de éxito

### Paso 3: Verificar Conexión

1. Clic en botón **"Probar Conexión"**
2. Deberías ver una notificación con tu información de usuario ML
3. El estado debe mostrar "Conectado" (ribbon verde)

## Configuración de Usuarios

### Asignar Permisos

Ir a: **Settings > Users & Companies > Users**

Para cada usuario que necesite acceso:

1. Editar usuario
2. En pestaña "Access Rights"
3. Buscar sección "Mercado Libre"
4. Asignar grupo:
   - **ML User**: Solo ver operaciones (usuarios normales)
   - **ML Manager**: Configuración + operaciones (administradores)

## Primer Uso

### Importar Operaciones de Prueba

1. Ir a: **Mercado Libre > Operaciones > Importar Operaciones**
2. Configurar:
   - Fecha Desde: Hace 7 días
   - Fecha Hasta: Hoy
3. Clic en **"Importar"**
4. Esperar a que termine (puede tardar varios minutos)
5. Clic en **"Ver Operaciones"**

### Verificar Datos

1. Abrir una operación de la lista
2. Verificar que se vean:
   - Order ID
   - Fechas
   - Importes (total, comisiones, neto)
   - Datos del comprador
   - Si hay CUIT/DNI: revisar campos de documento

## Configuración Avanzada

### Multi-Compañía

Si usas multi-compañía en Odoo:

1. Crea una configuración ML por compañía
2. Cada configuración debe tener su propia aplicación ML
3. Las operaciones se filtran automáticamente por compañía

### Automatización

Para importar operaciones automáticamente:

1. Ir a: **Settings > Technical > Automation > Scheduled Actions**
2. Crear nueva acción:
   - Nombre: "Importar Operaciones ML Diarias"
   - Model: ml.import.operations.wizard
   - Execute every: 1 Day
   - Python Code:
   
```python
# Importar operaciones del día anterior
from datetime import datetime, timedelta

config = env['ml.api.config'].get_active_config()
date_from = datetime.now() - timedelta(days=1)
date_to = datetime.now()

env['ml.operation'].import_operations_from_ml(
    config=config,
    date_from=date_from,
    date_to=date_to,
    limit=50
)
```

3. Guardar y activar

### Notificaciones por Email

Para recibir notificaciones de nuevas operaciones:

1. Ir a: **Settings > Technical > Email > Activity Types**
2. Configurar según necesidad
3. Agregar seguidores a operaciones

### Webhooks (Futuro)

Esta versión no incluye webhooks, pero puedes configurar polling frecuente:
- Usar Scheduled Action cada 1 hora
- Importar operaciones de las últimas 2 horas

## Troubleshooting

### Error: Redirect URI mismatch

**Síntoma**: Error al hacer OAuth

**Solución**:
1. Verifica que web.base.url en Odoo coincida exactamente con el dominio
2. Verifica que la Redirect URI en ML sea exactamente: https://dominio.com/ml/oauth/callback
3. Debe ser HTTPS (no HTTP)
4. Sin barra final "/"

### Error: Invalid credentials

**Síntoma**: No se puede conectar

**Solución**:
1. Verifica Client ID y Client Secret
2. Cópialos nuevamente desde el portal de ML
3. No debe haber espacios al inicio o final

### No se importan datos fiscales

**Síntoma**: buyer_doc_type y buyer_doc_number vacíos

**Solución**:
- Esto es normal para compradores sin CUIT registrado en ML
- Solo algunos compradores tienen estos datos
- ML no siempre provee esta información

### Token expira constantemente

**Síntoma**: Estado cambia a "Token Expirado"

**Solución**:
1. Verifica conectividad de red del servidor Odoo
2. Revisa logs: puede haber error en renovación automática
3. Usa botón "Renovar Token" manualmente
4. Si persiste, vuelve a conectar desde cero

### Rate Limit alcanzado

**Síntoma**: Error "Límite de peticiones alcanzado"

**Solución**:
1. Espera 10-15 minutos
2. Reduce el rango de fechas en importaciones
3. No hacer muchas importaciones seguidas
4. Considera usar Scheduled Actions en horarios de baja demanda

## Mantenimiento

### Backup de Configuración

La configuración incluye tokens sensibles. Asegúrate de:

1. Backup regular de la base de datos
2. Proteger acceso a backups
3. No compartir tokens en texto plano

### Actualización del Módulo

Para actualizar a una nueva versión:

```bash
# 1. Backup de base de datos
pg_dump tu_database > backup_antes_update.sql

# 2. Copiar nueva versión
cp -r ml_billing_connector_new /path/to/addons/ml_billing_connector

# 3. Actualizar módulo
./odoo-bin -u ml_billing_connector -d tu_database

# 4. Verificar funcionamiento
# Ir a Configuración ML y probar conexión
```

### Limpieza de Datos Antiguos

Para limpiar operaciones antiguas (opcional):

```python
# Ejecutar desde shell de Odoo o Scheduled Action
# Borrar operaciones de hace más de 1 año

from datetime import datetime, timedelta

date_limit = datetime.now() - timedelta(days=365)
old_operations = env['ml.operation'].search([
    ('date_created', '<', date_limit)
])
old_operations.unlink()
```

## Soporte

Si necesitas ayuda adicional:

1. Revisa el README.md completo
2. Consulta logs de Odoo
3. Contacta a soporte@tuempresa.com
4. Revisa documentación oficial de ML: https://developers.mercadolibre.com.ar/

## Checklist de Configuración

- [ ] Aplicación creada en portal ML developers
- [ ] Client ID y Client Secret anotados
- [ ] Redirect URI configurada correctamente
- [ ] Módulo instalado en Odoo
- [ ] web.base.url configurado
- [ ] Configuración ML creada
- [ ] OAuth completado exitosamente
- [ ] Prueba de conexión exitosa
- [ ] Usuarios con permisos asignados
- [ ] Primera importación de operaciones completada
- [ ] Datos verificados (importes, comisiones, documentos)

¡Todo listo! Ya puedes usar el módulo de forma productiva.
