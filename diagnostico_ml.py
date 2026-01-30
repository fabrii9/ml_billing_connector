#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar configuración de ML OAuth
"""

print("=" * 60)
print("DIAGNÓSTICO ML BILLING CONNECTOR")
print("=" * 60)
print()

# Verificaciones a realizar manualmente:
checklist = [
    ("1. web.base.url configurado en Odoo", 
     "Settings > Technical > System Parameters > web.base.url"),
    
    ("2. Redirect URI en app ML coincide EXACTAMENTE", 
     "https://developers.mercadolibre.com.ar/apps > Tu App > Redirect URI"),
    
    ("3. Client ID copiado correctamente (sin espacios)", 
     "Verificar en configuración ML de Odoo"),
    
    ("4. Client Secret copiado correctamente (sin espacios)", 
     "Verificar en configuración ML de Odoo"),
    
    ("5. Scopes configurados en app ML", 
     "read + offline_access en el portal de developers"),
    
    ("6. Aplicación ML está publicada/activa", 
     "Verificar estado en portal de developers"),
]

for check, ubicacion in checklist:
    print(f"☐ {check}")
    print(f"   Ubicación: {ubicacion}")
    print()

print("-" * 60)
print("PASOS PARA VERIFICAR:")
print("-" * 60)
print()

print("1. En Odoo, ve a: Mercado Libre > Configuración > Conexión API")
print()

print("2. Anota tu Redirect URI que muestra Odoo:")
print("   (debería ser algo como: http://TU-DOMINIO:8079/ml/oauth/callback)")
print()

print("3. Ve a: https://developers.mercadolibre.com.ar/apps")
print()

print("4. Selecciona tu aplicación")
print()

print("5. VERIFICA QUE LA REDIRECT URI SEA EXACTAMENTE IGUAL")
print("   - Sin espacios al inicio o final")
print("   - Con http:// o https:// según corresponda")
print("   - Con el puerto correcto (8079)")
print("   - Sin barra final /")
print()

print("6. Verifica los SCOPES marcados:")
print("   ✓ read")
print("   ✓ offline_access")
print()

print("7. Verifica Client ID y Secret:")
print("   - Copia nuevamente desde el portal")
print("   - Pega en Odoo SIN espacios extras")
print()

print("8. Si la app está en desarrollo, verifica:")
print("   - Que tu cuenta ML esté autorizada para testing")
print("   - O publica la aplicación si está lista")
print()

print("=" * 60)
print("ERRORES COMUNES:")
print("=" * 60)
print()
print("❌ Redirect URI con HTTPS cuando Odoo usa HTTP")
print("❌ Puerto incorrecto (8080 vs 8079)")
print("❌ Client Secret con espacios o copiado mal")
print("❌ App ML no publicada (solo para cuentas test)")
print("❌ Scopes insuficientes")
print()

print("=" * 60)
print("SIGUIENTE PASO:")
print("=" * 60)
print()
print("Después de verificar todo:")
print("1. Actualiza la configuración en Odoo si es necesario")
print("2. GUARDA los cambios")
print("3. Vuelve a hacer clic en 'Conectar con Mercado Libre'")
print()
