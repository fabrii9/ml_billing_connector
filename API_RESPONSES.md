# Documentación Técnica - API Responses
# Mercado Libre Billing Connector

## Estructura de Respuestas de la API de Mercado Libre

Este documento describe las respuestas JSON esperadas de los endpoints de ML
y cómo se mapean a los campos de Odoo.

---

## 1. GET /orders/search

Busca órdenes por seller y rango de fechas.

### Request
```
GET https://api.mercadolibre.com/orders/search?seller=123456&order.date_created.from=2026-01-01T00:00:00.000Z&order.date_created.to=2026-01-31T23:59:59.000Z
```

### Response Example
```json
{
  "query": "seller:123456",
  "paging": {
    "total": 125,
    "limit": 50,
    "offset": 0
  },
  "results": [
    2000003823456789,
    2000003823456790,
    2000003823456791
  ],
  "sort": {
    "id": "date_desc"
  }
}
```

### Mapeo a Odoo
- `results[]`: Array de Order IDs a procesar individualmente
- `paging.total`: Total de órdenes encontradas
- `paging.offset`: Control de paginación

---

## 2. GET /orders/{order_id}

Obtiene el detalle completo de una orden.

### Request
```
GET https://api.mercadolibre.com/orders/2000003823456789
```

### Response Example
```json
{
  "id": 2000003823456789,
  "status": "paid",
  "status_detail": null,
  "date_created": "2026-01-15T10:30:45.000-03:00",
  "date_closed": "2026-01-15T10:35:22.000-03:00",
  "last_updated": "2026-01-15T11:00:00.000-03:00",
  "expiration_date": "2026-02-14T10:30:45.000-03:00",
  "feedback": {
    "buyer": null,
    "seller": null
  },
  "mediations": [],
  "fulfilled": false,
  "total_amount": 17499.99,
  "paid_amount": 17499.99,
  "currency_id": "ARS",
  "buyer": {
    "id": 123456789,
    "nickname": "COMPRADOR_TEST",
    "email": "comprador@example.com",
    "phone": {
      "area_code": "11",
      "number": "12345678",
      "extension": ""
    },
    "first_name": "Juan",
    "last_name": "Pérez",
    "billing_info": {
      "doc_type": "DNI",
      "doc_number": "12345678"
    }
  },
  "seller": {
    "id": 987654321,
    "nickname": "VENDEDOR_TEST",
    "email": "vendedor@example.com",
    "first_name": "Empresa",
    "last_name": "S.A."
  },
  "payments": [
    {
      "id": 12345678901,
      "transaction_amount": 17499.99,
      "currency_id": "ARS",
      "status": "approved",
      "date_approved": "2026-01-15T10:32:15.000-03:00",
      "date_created": "2026-01-15T10:31:00.000-03:00",
      "date_last_modified": "2026-01-15T10:32:20.000-03:00",
      "payment_method_id": "account_money",
      "payment_type": "account_money",
      "reason": "Pago de orden",
      "status_code": null,
      "status_detail": "accredited",
      "marketplace_fee": 2624.99,
      "shipping_cost": 0,
      "transaction_amount_refunded": 0,
      "installments": 1,
      "deferred_period": null,
      "collector": {
        "id": 987654321
      }
    }
  ],
  "order_items": [
    {
      "item": {
        "id": "MLA987654321",
        "title": "Notebook Gamer 15.6\" Intel Core i7",
        "category_id": "MLA1652",
        "variation_id": null,
        "seller_custom_field": "SKU-NB-001",
        "variation_attributes": [],
        "warranty": "Garantía del vendedor: 12 meses"
      },
      "quantity": 1,
      "requested_quantity": {
        "value": 1,
        "measure": "unit"
      },
      "picked_quantity": null,
      "unit_price": 15999.99,
      "full_unit_price": 15999.99,
      "currency_id": "ARS",
      "manufacturing_days": null,
      "sale_fee": 2399.99,
      "listing_type_id": "gold_special"
    }
  ],
  "shipping": {
    "id": 40123456789,
    "shipment_type": "shipping",
    "date_created": "2026-01-15T10:30:50.000-03:00",
    "last_modified": "2026-01-15T10:35:30.000-03:00",
    "status": "shipped",
    "substatus": "ready_to_ship",
    "cost": 1500.00,
    "base_cost": 1500.00,
    "receiver_address": {
      "id": 789123456,
      "address_line": "Av. Siempre Viva 742 Piso 3",
      "street_name": "Av. Siempre Viva",
      "street_number": "742",
      "comment": "Piso 3, Timbre A",
      "zip_code": "1234",
      "city": {
        "id": "TUxBQkNBUGZlZG0",
        "name": "Capital Federal"
      },
      "state": {
        "id": "AR-C",
        "name": "Capital Federal"
      },
      "country": {
        "id": "AR",
        "name": "Argentina"
      },
      "neighborhood": {
        "id": null,
        "name": null
      },
      "municipality": {
        "id": null,
        "name": null
      },
      "agency": null,
      "types": [
        "billing",
        "shipping"
      ],
      "latitude": -34.603722,
      "longitude": -58.381592,
      "receiver_name": "Juan Pérez",
      "receiver_phone": "1112345678"
    }
  },
  "tags": [
    "paid",
    "not_delivered"
  ],
  "pack_id": null,
  "taxes": {
    "amount": null,
    "currency_id": null,
    "id": null
  }
}
```

### Mapeo a Odoo (ml.operation)

| Campo ML | Campo Odoo | Notas |
|----------|------------|-------|
| `id` | `order_id` | String |
| `status` | `status` | Posibles: confirmed, payment_required, payment_in_process, paid, cancelled |
| `date_created` | `date_created` | Datetime, parsear ISO |
| `date_closed` | `date_closed` | Datetime |
| `last_updated` | `last_updated` | Datetime |
| `total_amount` | `total_amount` | Float |
| `paid_amount` | `paid_amount` | Float |
| `currency_id` | `currency_code` + buscar `currency_id` | Ej: "ARS" → res.currency |
| `buyer.first_name + last_name` | `buyer_name` | String concatenado |
| `buyer.nickname` | `buyer_nickname` | String |
| `buyer.email` | `buyer_email` | String |
| `buyer.phone.number` | `buyer_phone` | String |
| `payments[0].status` | `payment_status` | approved, pending, rejected, etc. |
| `payments[0].date_approved` | `date_approved` | Datetime |
| `payments[0].marketplace_fee` | Fee de tipo `marketplace_fee` | Float (crear ml.operation.fee) |
| `payments[0].shipping_cost` | Fee de tipo `shipping_cost` | Float (crear ml.operation.fee) |
| `order_items[]` | `item_count` + cálculo `item_amount` | Suma de unit_price * quantity |
| `shipping.cost` | `shipping_amount` | Float |
| `shipping.receiver_address.*` | `shipping_address`, `shipping_city`, etc. | String concatenado |
| `pack_id` | `pack_id` | String o False |
| `taxes.amount` | `tax_amount` | Float o 0 |
| *JSON completo* | `raw_json` | Text field para auditoría |

**Cálculo de net_amount:**
```python
net_amount = total_amount - total_fees
# donde total_fees = sum(fee_ids.amount)
```

---

## 3. GET /orders/{order_id}/billing_info

Obtiene información fiscal del comprador.

### Request
```
GET https://api.mercadolibre.com/orders/2000003823456789/billing_info
```

### Response Example - Con CUIT
```json
{
  "doc_type": "CUIT",
  "doc_number": "20-12345678-9",
  "business_name": "Empresa Test S.A.",
  "tax_id": null
}
```

### Response Example - Con DNI
```json
{
  "doc_type": "DNI",
  "doc_number": "12345678"
}
```

### Response - Sin información
```json
{
  "message": "billing info not found",
  "error": "not_found",
  "status": 404
}
```

### Mapeo a Odoo

| Campo ML | Campo Odoo | Notas |
|----------|------------|-------|
| `doc_type` | `buyer_doc_type` | Selection: DNI, CUIT, CUIL, CDI, Otro |
| `doc_number` | `buyer_doc_number` | String |
| `business_name` | `buyer_name` (actualizar si existe) | String |
| *JSON completo* | `raw_billing_info` | Text field |

**Manejo de errores:**
- Si 404 o error: campos quedan en False (no es error fatal)
- Logging: WARNING level

---

## 4. GET /users/me

Obtiene información del usuario autenticado (para test de conexión).

### Request
```
GET https://api.mercadolibre.com/users/me
Authorization: Bearer {access_token}
```

### Response Example
```json
{
  "id": 987654321,
  "nickname": "VENDEDOR_TEST",
  "registration_date": "2020-05-15T10:00:00.000-03:00",
  "country_id": "AR",
  "address": {
    "city": "Capital Federal",
    "state": "AR-C"
  },
  "user_type": "normal",
  "tags": [
    "normal",
    "credits_profile"
  ],
  "logo": null,
  "points": 100,
  "site_id": "MLA",
  "permalink": "https://www.mercadolibre.com.ar/perfil/VENDEDOR_TEST",
  "seller_reputation": {
    "level_id": "5_green",
    "power_seller_status": "gold",
    "transactions": {
      "completed": 1250,
      "canceled": 15,
      "period": "historic",
      "ratings": {
        "positive": 0.98,
        "negative": 0.01,
        "neutral": 0.01
      }
    }
  },
  "buyer_reputation": {
    "tags": []
  },
  "status": {
    "site_status": "active"
  },
  "secure_email": "vendedor-test-123@mail.mercadolibre.com",
  "first_name": "Empresa",
  "last_name": "S.A.",
  "email": "contacto@empresa.com"
}
```

### Uso en Odoo
- Se usa solo para test de conexión
- `id` se guarda en `seller_id` al hacer OAuth
- Se muestra `nickname`, `id`, `email` en notificación de prueba

---

## 5. POST /oauth/token

Obtiene o refresca tokens de acceso.

### Request - Authorization Code
```
POST https://api.mercadolibre.com/oauth/token
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "client_id": "1234567890123456",
  "client_secret": "AbCdEfGhIjKlMnOpQrStUvWxYz",
  "code": "TG-abc123def456ghi789",
  "redirect_uri": "https://tu-odoo.com/ml/oauth/callback"
}
```

### Request - Refresh Token
```
POST https://api.mercadolibre.com/oauth/token
Content-Type: application/json

{
  "grant_type": "refresh_token",
  "client_id": "1234567890123456",
  "client_secret": "AbCdEfGhIjKlMnOpQrStUvWxYz",
  "refresh_token": "TG-xyz987uvw654rst321"
}
```

### Response Example
```json
{
  "access_token": "APP_USR-1234567890123456-012345-abcdef1234567890abcdef1234567890-987654321",
  "token_type": "bearer",
  "expires_in": 21600,
  "scope": "offline_access read",
  "user_id": 987654321,
  "refresh_token": "TG-xyz987uvw654rst321"
}
```

### Mapeo a Odoo (ml.api.config)

| Campo ML | Campo Odoo | Notas |
|----------|------------|-------|
| `access_token` | `access_token` | String (password field) |
| `refresh_token` | `refresh_token` | String (password field) |
| `expires_in` | Cálculo de `token_expiration` | Datetime = now + timedelta(seconds=expires_in) |
| `user_id` | `seller_id` | String |

**Expiración:**
- Tokens duran 6 horas (21600 segundos)
- Se refrescan automáticamente 5 minutos antes de expirar
- Usar `refresh_token` para obtener nuevo `access_token`

---

## Códigos de Estado HTTP

### Exitosos
- `200 OK`: Solicitud exitosa
- `201 Created`: Recurso creado (no usado en este módulo)

### Errores del Cliente
- `400 Bad Request`: Parámetros inválidos
- `401 Unauthorized`: Token inválido o expirado → Refrescar token
- `403 Forbidden`: Sin permisos suficientes
- `404 Not Found`: Recurso no existe (ej: billing_info no disponible)

### Errores del Servidor
- `429 Too Many Requests`: Rate limit alcanzado → Esperar y reintentar
- `500 Internal Server Error`: Error de ML → Reintentar más tarde
- `503 Service Unavailable`: Servicio caído → Reintentar más tarde

---

## Rate Limiting

Mercado Libre aplica límites de peticiones:

- **Límite general**: Variable según endpoint y cuenta
- **Recomendación**: Máximo 1 petición por segundo
- **Paginación**: Máximo 50 resultados por página

### Manejo en el Módulo
```python
# En caso de 429
if response.status_code == 429:
    # Esperar antes de reintentar
    # Mostrar error al usuario
    raise UserError('Límite alcanzado, espere e intente más tarde')
```

---

## Campos que Pueden Variar

### Por País
- `doc_type`: En Argentina: DNI, CUIT, CUIL. En Brasil: CPF, CNPJ
- `currency_id`: ARS (Argentina), BRL (Brasil), MXN (México), etc.

### Por Tipo de Venta
- `billing_info`: Solo disponible para algunas ventas B2B
- `pack_id`: Solo existe si múltiples órdenes agrupadas
- `taxes`: No siempre desglosado
- `shipping.cost`: 0 si envío gratis

### Por Método de Pago
- `marketplace_fee`: Varía según categoría y método de pago
- `shipping_cost`: Puede ser 0 o negativo (si ML subsidia)

---

## Manejo de Datos Faltantes

El módulo maneja estos casos:

```python
# Ejemplo de manejo seguro
billing_info = self._fetch_billing_info(order_id)
if billing_info:
    # Procesar
else:
    # No es error, dejar campos vacíos
    _logger.warning(f"No billing info for {order_id}")

# Fechas opcionales
date_closed = self._parse_ml_date(order_data.get('date_closed'))
# Si None, el campo queda en False

# Arrays vacíos
payments = order_data.get('payments', [])
if payments:
    # Procesar primer pago
else:
    # No hay pagos aún
```

---

## Testing

### Datos de Prueba (Sandbox)

ML no tiene un sandbox real, pero puedes:

1. Crear órdenes de prueba en tu cuenta real
2. Usar órdenes antiguas para testing
3. No hay forma de simular sin cuenta real

### Validación de Mapeo

Para validar que el mapeo funciona:

```python
# Desde shell de Odoo
config = env['ml.api.config'].get_active_config()

# Test: Buscar órdenes
orders = config._make_api_request(
    '/orders/search',
    params={
        'seller': config.seller_id,
        'order.date_created.from': '2026-01-01T00:00:00.000Z',
        'order.date_created.to': '2026-01-31T23:59:59.000Z',
        'limit': 5
    }
)
print(orders)

# Test: Detalle de orden
order_detail = config._make_api_request(f'/orders/{order_id}')
print(json.dumps(order_detail, indent=2))

# Test: Billing info
billing = config._make_api_request(f'/orders/{order_id}/billing_info')
print(billing)
```

---

## Referencias

Documentación oficial de Mercado Libre:
- **API Reference**: https://developers.mercadolibre.com.ar/es_ar/api-docs-es
- **OAuth Guide**: https://developers.mercadolibre.com.ar/es_ar/autenticacion-y-autorizacion
- **Orders API**: https://developers.mercadolibre.com.ar/es_ar/ordenes-v2
- **SDK Python** (opcional): https://github.com/mercadolibre/python-sdk

---

**Nota**: Las estructuras de respuesta pueden variar ligeramente según el país (site_id).
Este documento se basa en MLA (Argentina) pero aplica a otros países con pequeñas variaciones.
