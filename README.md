# Mercado Libre Billing Connector

**Versión:** 16.0.1.0.0  
**Autor:** Tu Empresa  
**Licencia:** LGPL-3

## Descripción

Módulo de integración completa con Mercado Libre para Odoo 16 que permite:

- 🔐 **Conexión OAuth2** segura con Mercado Libre
- 📦 **Importación automática** de operaciones/ventas por rango de fechas
- 💰 **Desglose completo** de importes (productos, comisiones, envíos, impuestos)
- 📄 **Datos fiscales del comprador** (CUIT/DNI) para facturación
- 🔄 **Renovación automática** de tokens
- 📊 **Análisis y reportes** de operaciones

## Requisitos Previos

### 1. Crear una Aplicación en Mercado Libre

Antes de instalar el módulo, necesitas crear una aplicación en el portal de desarrolladores de Mercado Libre:

1. Ingresa a: https://developers.mercadolibre.com.ar/
2. Ve a "Tus aplicaciones" y crea una nueva aplicación
3. Completa los datos solicitados:
   - **Nombre de la aplicación**
   - **Descripción corta**
   - **Redirect URI**: `https://tu-dominio-odoo.com/ml/oauth/callback`
   - **Scopes requeridos**: `read`, `offline_access`

4. Guarda tu aplicación y anota:
   - **Client ID (App ID)**
   - **Client Secret (Secret Key)**

### 2. Dependencias de Python

El módulo requiere la librería `requests`:

```bash
pip3 install requests
```

## Instalación

1. Copia el módulo `ml_billing_connector` a tu carpeta `addons` de Odoo:

```bash
cp -r ml_billing_connector /path/to/odoo/addons/
```

2. Actualiza la lista de aplicaciones en Odoo:
   - Ve a **Aplicaciones**
   - Clic en **Actualizar lista de aplicaciones**
   - Busca "Mercado Libre Billing Connector"
   - Instala el módulo

3. Asigna permisos a los usuarios:
   - **ML Manager**: Para administradores que configuran la conexión
   - **ML User**: Para usuarios que solo visualizan operaciones

## Configuración

### Paso 1: Configurar la Conexión

1. Ve a **Mercado Libre > Configuración > Conexión API**
2. Crea un nuevo registro o edita el existente
3. Completa los campos:
   - **Nombre**: Un nombre descriptivo
   - **Client ID**: El App ID de tu aplicación ML
   - **Client Secret**: El Secret Key de tu aplicación ML
   - **Entorno**: Producción (ML no tiene sandbox real)
   - **País**: Selecciona tu país (ej: Argentina - MLA)

### Paso 2: Conectar con Mercado Libre

1. En el formulario de configuración, clic en **"Conectar con Mercado Libre"**
2. Serás redirigido al sitio de ML para autorizar la aplicación
3. Acepta los permisos solicitados
4. Serás redirigido de vuelta a Odoo con la confirmación

### Paso 3: Probar la Conexión

1. En el formulario de configuración, clic en **"Probar Conexión"**
2. Deberías ver un mensaje con tu información de usuario ML

## Uso

### Importar Operaciones

1. Ve a **Mercado Libre > Operaciones > Importar Operaciones**
2. Selecciona el rango de fechas (máximo 90 días)
3. Clic en **"Importar"**
4. El sistema traerá todas las órdenes del período
5. Al finalizar, verás las estadísticas y podrás ver las operaciones importadas

### Ver Operaciones

1. Ve a **Mercado Libre > Operaciones > Todas las Operaciones**
2. Usa los filtros para buscar:
   - Por estado de pago (Pagadas, Pendientes, Canceladas)
   - Por período (Hoy, Esta semana, Este mes)
   - Por tipo de documento (CUIT, DNI)
3. Haz clic en una operación para ver el detalle completo

### Información Disponible por Operación

Cada operación importada incluye:

#### Datos Básicos
- Order ID (referencia de ML)
- Fecha de creación, cierre y aprobación
- Estado de la orden y del pago

#### Importes
- Total de la orden
- Productos
- Envío
- Impuestos
- **Comisiones ML** (desglosadas)
- **Neto a cobrar** (total - comisiones)

#### Datos Fiscales del Comprador
- Tipo de documento (DNI, CUIT, CUIL, etc.)
- Número de documento
- Nombre/Razón social
- Email y teléfono

#### Dirección de Envío
- Dirección completa
- Ciudad, Provincia, Código postal

#### Desglose de Comisiones
- Comisión ML
- Costo de envío (si aplica)
- Otros cargos

#### Auditoría
- JSON completo de la respuesta API
- Billing info JSON
- Fecha de importación

## Estructura de Datos

### Modelos Principales

#### `ml.api.config`
Configuración de la conexión OAuth2 con ML

**Campos clave:**
- `client_id`, `client_secret`: Credenciales OAuth
- `access_token`, `refresh_token`: Tokens de autorización
- `token_expiration`: Fecha de expiración del token
- `seller_id`: ID del vendedor en ML
- `state`: Estado de la conexión (connected, disconnected, expired)

#### `ml.operation`
Operación/venta importada desde ML

**Campos clave:**
- `order_id`: ID de la orden en ML
- `date_created`: Fecha de creación
- `total_amount`: Monto total
- `net_amount`: Monto neto (total - comisiones)
- `buyer_doc_type`, `buyer_doc_number`: Datos fiscales
- `payment_status`: Estado del pago
- `raw_json`: JSON completo para auditoría

#### `ml.operation.fee`
Comisiones y cargos de una operación

**Tipos:**
- `marketplace_fee`: Comisión ML
- `shipping_cost`: Costo envío
- `payment_fee`: Comisión de pago
- `tax`: Impuesto
- `refund`: Reembolso
- `other`: Otro

## Endpoints de API Utilizados

El módulo consume los siguientes endpoints de Mercado Libre API:

### Autenticación
- `POST /oauth/token` - Obtener/refrescar tokens

### Operaciones
- `GET /orders/search` - Buscar órdenes por seller y fechas
- `GET /orders/{order_id}` - Detalle de una orden
- `GET /orders/{order_id}/billing_info` - Información fiscal del comprador
- `GET /users/me` - Información del usuario (prueba de conexión)

## Ejemplos de Respuestas API

### Ejemplo: Orden Completa

```json
{
  "id": 2000003823456789,
  "status": "paid",
  "date_created": "2026-01-15T10:30:45.000-03:00",
  "date_closed": "2026-01-15T10:35:22.000-03:00",
  "total_amount": 15999.99,
  "paid_amount": 15999.99,
  "currency_id": "ARS",
  "buyer": {
    "id": 123456789,
    "nickname": "COMPRADOR_TEST",
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan.perez@example.com"
  },
  "order_items": [
    {
      "item": {
        "id": "MLA987654321",
        "title": "Producto de Prueba",
        "seller_custom_field": "SKU-001"
      },
      "quantity": 1,
      "unit_price": 15999.99
    }
  ],
  "payments": [
    {
      "id": 12345678901,
      "status": "approved",
      "date_approved": "2026-01-15T10:32:15.000-03:00",
      "marketplace_fee": 2399.99,
      "shipping_cost": 0
    }
  ],
  "shipping": {
    "id": 987654321,
    "cost": 1500.00,
    "receiver_address": {
      "street_name": "Av. Siempre Viva",
      "street_number": "742",
      "city": {
        "name": "Springfield"
      },
      "state": {
        "name": "Buenos Aires"
      },
      "zip_code": "1234"
    }
  }
}
```

### Ejemplo: Billing Info

```json
{
  "doc_type": "CUIT",
  "doc_number": "20-12345678-9"
}
```

## Campos que Pueden Variar

Dependiendo del tipo de venta, país y configuración del vendedor, algunos campos pueden no estar disponibles:

### Campos Opcionales
- `billing_info`: No siempre está disponible, especialmente para compradores sin CUIT
- `pack_id`: Solo existe si hay múltiples órdenes agrupadas
- `shipping.cost`: Puede ser 0 si el envío es gratis
- `taxes`: No siempre desglosado en la respuesta
- `marketplace_fee`: Puede variar según el producto y categoría

### Manejo de Datos Faltantes

El módulo maneja estos casos:

1. **Billing info no disponible**: Se guarda `False` en campos de documento
2. **Comisiones no detalladas**: Se calculan desde payments si están disponibles
3. **Dirección incompleta**: Se concatenan los campos disponibles
4. **Fechas faltantes**: Se usa `False` en lugar de error

## Mantenimiento

### Renovación de Tokens

El módulo maneja automáticamente la renovación de tokens:

- Los tokens expiran cada 6 horas
- Se renuevan automáticamente 5 minutos antes de expirar
- Si falla la renovación, el estado cambia a "expired"
- Puedes renovar manualmente con el botón "Renovar Token"

### Logs y Debugging

Los logs se encuentran en:
- Archivo de log de Odoo (ver configuración `logfile`)
- Campo `last_error` en la configuración ML
- Campo `raw_json` en cada operación (auditoría completa)

### Límites de la API

Mercado Libre tiene límites de rate limiting:

- Máximo 50 resultados por página en búsquedas
- El módulo implementa reintentos con backoff
- Si alcanzas el límite, espera unos minutos antes de reintentar

## Troubleshooting

### Error: "No se recibió código de autorización"

**Causa**: La Redirect URI no coincide con la configurada en ML

**Solución**: 
1. Verifica que la Redirect URI en tu app ML sea exactamente: `https://tu-dominio.com/ml/oauth/callback`
2. Asegúrate de usar HTTPS (no HTTP)
3. Verifica el parámetro `web.base.url` en Odoo

### Error: "Token expirado"

**Causa**: El token de acceso ha expirado

**Solución**:
1. Clic en "Renovar Token" en la configuración
2. Si falla, vuelve a conectar con "Conectar con Mercado Libre"

### Error: "Límite de peticiones alcanzado"

**Causa**: Has excedido el rate limit de ML

**Solución**:
1. Espera 5-10 minutos antes de reintentar
2. Reduce el rango de fechas en la importación
3. Importa en horarios de menor tráfico

### No se importa billing_info

**Causa**: El comprador no tiene CUIT/CUIL registrado en ML

**Solución**:
- Esto es normal para muchas ventas B2C
- El campo quedará vacío
- Puedes solicitarlo manualmente al comprador si necesitas facturar

## Seguridad

### Almacenamiento de Credenciales

- Los tokens se almacenan en la base de datos
- Se usan campos `password=True` en la interfaz para ocultarlos
- Solo usuarios con rol "ML Manager" pueden ver/editar credenciales
- Recomendación: Limita el acceso a la base de datos

### Permisos de Usuario

- **ML Manager**: Acceso completo (configuración + operaciones)
- **ML User**: Solo lectura de operaciones
- Los grupos siguen las reglas multi-compañía de Odoo

## Roadmap / Mejoras Futuras

Posibles mejoras para futuras versiones:

- [ ] Cifrado de tokens en base de datos
- [ ] Webhooks para recibir notificaciones en tiempo real
- [ ] Integración con módulo de facturación (crear facturas automáticamente)
- [ ] Sincronización de productos (catálogo ML ↔ Odoo)
- [ ] Manejo de reclamos y preguntas
- [ ] Dashboard con KPIs y estadísticas
- [ ] Exportación de operaciones a Excel/CSV
- [ ] Filtros avanzados y búsqueda full-text
- [ ] Integración con otros módulos de Odoo (inventory, sale, etc.)

## Soporte

Para reportar bugs o solicitar features:
- Email: soporte@tuempresa.com
- GitHub: https://github.com/tuempresa/ml_billing_connector

## Licencia

LGPL-3

## Changelog

### Version 16.0.1.0.0 (2026-01-30)
- Versión inicial
- Conexión OAuth2 con ML
- Importación de operaciones por rango de fechas
- Visualización de datos fiscales
- Desglose de comisiones y cargos
- Renovación automática de tokens
- Vistas: tree, form, kanban, pivot, graph
- Seguridad: grupos ML User y ML Manager
- Multi-compañía
