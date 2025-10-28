# ❓ Preguntas Frecuentes (FAQ)

## 📋 General

### ¿Qué problema resuelve este módulo?

**Problema:** Cuando un usuario público reserva una cita y luego crea una cuenta durante el pago, se crean **2 contactos duplicados**:
1. Contacto temporal (de la reserva inicial)
2. Contacto de la cuenta de usuario

**Solución:** Este módulo requiere que el usuario cree su cuenta ANTES de reservar, creando solo UN contacto desde el principio.

---

### ¿Es compatible con Odoo Community Edition?

Sí, el módulo funciona tanto en:
- ✅ Odoo Community 18.0
- ✅ Odoo Enterprise 18.0

---

### ¿Funciona con versiones anteriores de Odoo?

No, este módulo está diseñado específicamente para Odoo 18.0. Para versiones anteriores, se requeriría adaptación.

---

## ⚙️ Configuración

### ¿Puedo activar/desactivar la autenticación por tipo de cita?

**Sí**, cada tipo de cita tiene su propio campo `require_login`:
- ✅ Cita A: require_login = True (requiere cuenta)
- ❌ Cita B: require_login = False (sin cuenta)

Esto te permite tener citas públicas (talleres, eventos) y citas privadas (servicios premium).

---

### ¿Cómo activo la autenticación para todas las citas a la vez?

```bash
docker exec -it odoo odoo shell -d tu_database
```

```python
# Activar para TODOS los appointment types
appts = env['appointment.type'].search([])
appts.write({'require_login': True})
env.cr.commit()
print(f"✅ Activado en {len(appts)} tipos de cita")
exit()
```

---

### ¿Puedo personalizar el mensaje que ve el usuario?

Sí, editando las traducciones:

1. Modo desarrollador → Configuración → Traducciones
2. Buscar: "Sign in to continue"
3. Cambiar traducción a tu texto personalizado

O editar directamente: `i18n/es_MX.po`

---

## 🔧 Funcionalidad

### ¿Qué pasa con los usuarios que ya tienen cuenta?

Los usuarios autenticados **no ven ningún cambio**. El flujo es exactamente igual que antes:
1. Seleccionan fecha/hora
2. Llenan formulario (datos prellenados)
3. Confirman o pagan
4. Listo

---

### ¿Los datos del formulario se preservan después del login?

**Sí**, todos los datos se preservan:
- ✅ Fecha y hora seleccionadas
- ✅ Staff seleccionado
- ✅ Resource seleccionado
- ✅ Duración
- ✅ Capacidad solicitada

Después del login, el usuario regresa al formulario con **todo** autocompletado.

---

### ¿Funciona con pagos / website_appointment_sale?

**Sí**, totalmente compatible. El módulo detecta automáticamente si la cita tiene pago configurado y muestra el botón apropiado:
- Con pago → "Proceed to Payment"
- Sin pago → "Confirm Appointment"

---

### ¿Puedo usar login con Google/Facebook?

Actualmente no incluido, pero puedes instalarlo con el módulo `auth_oauth`:

```bash
Apps → Buscar "OAuth" → Instalar
```

Los botones de OAuth aparecerán automáticamente en el formulario de login/signup.

---

## 🐛 Troubleshooting

### Los botones de login no aparecen

**Verificar:**
1. ¿El campo `require_login` está activado?
```python
appt = env['appointment.type'].browse(ID)
print(appt.require_login)  # Debe ser True
```

2. ¿Estás en modo incógnito? (usuario público)

3. Limpia cache del navegador: `Ctrl + Shift + R`

---

### Aparecen botones duplicados

**Causa:** Otro módulo custom modificando el mismo template.

**Solución:**
1. Verifica módulos instalados que modifiquen appointments
2. Ajusta la prioridad del template si es necesario
3. Desinstala/reinstala el módulo

---

### Después del login no regresa al formulario

**Verificar:**
1. Console del navegador (F12) → ¿Hay errores en rojo?
2. URL de login → ¿Tiene parámetro `redirect`?
```
/web/login?redirect=%2Fappointment%2F8%2Finfo%3F...
```

3. Logs del servidor:
```bash
docker logs --tail 100 odoo_container | grep -i error
```

---

### Las traducciones no aparecen

**Solución:**
1. Verificar idioma del usuario:
   - Configuración → Usuarios → Tu usuario → Idioma: Spanish (MX)

2. Cargar traducciones:
   - Configuración → Traducciones → Cargar traducción
   - Idioma: es_MX
   - Módulo: beauty_salon_appointment_auth

3. Reiniciar servidor después de cargar

---

## 💳 Pagos

### ¿Funciona con múltiples métodos de pago?

Sí, el módulo es compatible con todos los métodos de pago de Odoo:
- ✅ Tarjeta de crédito
- ✅ PayPal
- ✅ Stripe
- ✅ Transferencia bancaria
- ✅ Pago en efectivo

---

### ¿Puedo configurar anticipos/depósitos?

Sí, si tienes instalado `beauty_salon_advances_appointment`, funciona perfectamente. El usuario:
1. Se autentica
2. Llena formulario
3. "Proceed to Payment"
4. Selecciona % de anticipo
5. Paga anticipo
6. Cita confirmada

---

### ¿Qué pasa si el pago falla?

El flujo es el mismo que Odoo nativo:
1. Usuario autenticado intenta pagar
2. Pago falla
3. Orden queda pendiente
4. Usuario puede reintentar pago
5. Cita NO se confirma hasta pago exitoso

---

## 🔐 Seguridad

### ¿Es seguro? ¿Valida en el backend también?

**Frontend:** CSS y JavaScript ocultan botones para usuarios públicos
**Backend:** Odoo maneja toda la autenticación nativamente

No hacemos override de lógica de seguridad de Odoo, solo agregamos una capa visual.

---

### ¿Los datos se envían de forma segura?

Sí, el módulo:
- ✅ Usa HTTPS (si está configurado en tu servidor)
- ✅ URL encoding correcto
- ✅ No expone datos sensibles en URLs
- ✅ Sigue mejores prácticas de Odoo

---

### ¿Puedo agregar captcha al signup?

Sí, instala el módulo `google_recaptcha`:
```bash
Apps → Buscar "reCAPTCHA" → Instalar
```

Configura tu Google reCAPTCHA key y se agregará automáticamente al formulario de signup.

---

## 📊 Reportes y Analytics

### ¿Cómo veo estadísticas de conversión?

Puedes crear un reporte personalizado:

```python
# Usuarios que crearon cuenta desde formulario de cita
users_from_appointments = env['res.users'].search([
    ('create_date', '>=', '2025-01-01'),
    # Agregar filtros adicionales
])

# Citas confirmadas
appointments = env['calendar.event'].search([
    ('appointment_type_id', '!=', False),
    ('create_date', '>=', '2025-01-01'),
])

conversion_rate = len(appointments) / len(users_from_appointments) * 100
print(f"Tasa de conversión: {conversion_rate}%")
```

---

### ¿Puedo exportar lista de usuarios que se registraron?

Sí, desde:
1. Configuración → Usuarios y Compañías → Usuarios
2. Filtros → Fecha de creación
3. Exportar → Excel/CSV

---

## 🚀 Performance

### ¿Afecta el rendimiento del sitio?

No significativamente:
- ✅ Solo carga JavaScript cuando es necesario
- ✅ CSS mínimo (< 1KB)
- ✅ Sin consultas adicionales a base de datos
- ✅ No modifica queries de Odoo

---

### ¿Funciona con muchos usuarios concurrentes?

Sí, el módulo:
- No agrega carga al servidor
- Usa caché de navegador
- Toda la lógica es frontend (JavaScript/CSS)

---

## 🌐 Multiidioma

### ¿Qué idiomas están soportados?

Actualmente:
- ✅ Español México (es_MX)

Puedes agregar fácilmente:
- Inglés (en_US)
- Español de España (es_ES)
- Otros idiomas

Siguiendo la estructura de `i18n/es_MX.po`

---

### ¿Cómo agrego un nuevo idioma?

```bash
# 1. Copiar archivo de traducción
cp i18n/es_MX.po i18n/en_US.po

# 2. Editar traducciones
nano i18n/en_US.po

# Cambiar:
"Language: es_MX" → "Language: en_US"
msgstr "Texto en español" → msgstr "Text in English"

# 3. Cargar en Odoo
Configuración → Traducciones → Cargar traducción
```

---

## 🔄 Migración y Upgrades

### ¿Qué pasa con las citas existentes si instalo el módulo?

**Nada cambia** para citas existentes:
- ✅ Citas pasadas: sin cambios
- ✅ Citas futuras: sin cambios
- ✅ Contactos existentes: sin cambios

El módulo solo afecta **nuevas reservas** con `require_login=True`.

---

### ¿Puedo desinstalar el módulo sin problemas?

Sí, es seguro desinstalar:
1. Campo `require_login` se elimina
2. Templates vuelven a versión nativa
3. Citas existentes no se afectan
4. Contactos existentes no se afectan

```bash
Apps → Beauty Salon Appointment Auth → Desinstalar
```

---

### ¿Cómo migro a una nueva versión de Odoo?

Cuando Odoo 19 salga:
1. Verificar compatibilidad
2. Actualizar `__manifest__.py`: version = '19.0.1.0.0'
3. Probar en ambiente de desarrollo
4. Migrar a producción

---

## 📞 Soporte

### ¿Dónde puedo obtener ayuda?

- 📧 Email: soporte@popstudio.com
- 🌐 Website: https://popstudio.com
- 📖 Documentación: [README.md](README.md)
- 🐛 Reportar bugs: [GitHub Issues]

---

### ¿Ofrecen servicios de personalización?

Sí, Pop Studio ofrece:
- Personalización del módulo
- Integración con otros módulos
- Desarrollo de funcionalidades custom
- Soporte prioritario
- Capacitación del equipo

Contacto: soporte@popstudio.com

---

### ¿El módulo tiene garantía?

El módulo se proporciona "tal cual" bajo licencia LGPL-3, sin garantías.

Sin embargo, **aceptamos reportes de bugs** y los corregimos en nuevas versiones.

---

## 💡 Mejores Prácticas

### ¿Cuándo DEBO activar require_login?

**Activa siempre que:**
- ✅ La cita tiene pago
- ✅ Servicios premium/personalizados
- ✅ Quieres evitar duplicados
- ✅ Necesitas seguimiento de clientes

**Mantén desactivado para:**
- ❌ Eventos públicos gratuitos
- ❌ Talleres abiertos
- ❌ Consultas de primera vez sin compromiso

---

### ¿Cómo evito que usuarios se frustren?

1. **Mensaje claro:** Explica por qué necesitan cuenta
2. **Proceso rápido:** Signup debe ser simple (3 campos)
3. **OAuth:** Ofrece login con Google/Facebook
4. **Incentivo:** "Crea cuenta y obtén 10% descuento"

---

### ¿Qué hacer con contactos duplicados existentes?

```python
# Script para fusionar duplicados
# Ejecutar con cuidado en ambiente de desarrollo primero

duplicates = env['res.partner'].search([
    ('email', '!=', False)
]).mapped('email')

from collections import Counter
duplicate_emails = [email for email, count in Counter(duplicates).items() if count > 1]

for email in duplicate_emails:
    partners = env['res.partner'].search([('email', '=', email)])
    # Fusionar manualmente o usar módulo de fusión
    print(f"Duplicado: {email} ({len(partners)} contactos)")
```

---

**¿No encuentras tu pregunta?** Abre un issue en GitHub o contáctanos directamente. 📧

---

*Última actualización: 28 de Octubre, 2025*