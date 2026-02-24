# Salon Customer Unifier

**Versión:** 18.0.1.3.0
**Módulo:** `salon_customer_unifier`
**Categoría:** Services / Appointment
**Licencia:** LGPL-3
**Autor:** Pop Studio / Smargeeks

---

## Propósito

Resuelve el problema de duplicidad de contactos (`res.partner`) en el flujo de citas de salón de belleza.

El sistema nativo de Odoo usa el **correo electrónico** como identificador para usuarios públicos y crea un partner nuevo cada vez que un cliente agenda como invitado. Este módulo reemplaza ese comportamiento con un **identificador por teléfono (Phone-First Match)** que garantiza un único contacto por cliente, independientemente de si el cliente tiene cuenta, usuario de portal o agenda como invitado.

---

## Características

### 1. Phone-First Match
El número de teléfono es el identificador primario del cliente en todo el flujo de citas. Al enviar el formulario de cita, el sistema busca el partner existente por teléfono antes de crear uno nuevo, eliminando duplicados.

### 2. Formulario de cita mejorado (intl-tel-input)
- **Reordenamiento de campos:** Teléfono → Nombre → Correo (el teléfono va primero porque es el identificador)
- **Selector de bandera internacional** con [intl-tel-input](https://intl-tel-input.com/), preconfigurado para México
- **Validación en tiempo real:** error inmediato si el número nacional tiene más o menos de 10 dígitos
- **Formato E.164** automático al confirmar la cita

### 3. Autocomplete inteligente
Al salir del campo teléfono (blur con 10 dígitos válidos), el sistema consulta la API de lookup y, si encuentra un partner:
- Rellena automáticamente los campos Nombre y Correo
- Bloquea los campos para proteger los datos existentes (readonly + estilo visual)
- Muestra un mensaje de estado personalizado con el nombre del cliente

### 4. Mensaje inteligente de estado
Bajo el formulario aparece una alerta con tres posibles estados:

| Estado | Color | Condición | Acción disponible |
|--------|-------|-----------|-------------------|
| `found` | Verde | Partner encontrado con email | "¿No eres tú?" |
| `found_no_email` | Amarillo | Partner encontrado sin email | "¿No eres tú?" + campo email editable |
| `new` | Azul | Sin partner registrado con ese teléfono | — |

### 5. Flujo "¿No eres tú?" — Solicitud de corrección
Cuando el cliente indica que los datos mostrados no son los suyos:
1. Se despliega un sub-formulario con campos de nombre y correo correctos
2. El cliente puede enviar la solicitud inmediatamente (botón **Enviar solicitud**, AJAX independiente) sin necesidad de continuar al pago
3. Se crea automáticamente una **actividad "Hacer"** (`mail.activity`) en el contacto encontrado, asignada a los responsables configurados por sucursal
4. La nota de la actividad incluye el teléfono del cliente y los datos correctos indicados
5. Si ya se envió la solicitud por AJAX, el submit principal del formulario no genera una actividad duplicada

### 6. Responsables de corrección por sucursal
Cada tipo de cita (`appointment.type`) tiene un campo nuevo: **Responsables de corrección de datos**. Al configurarlo con los usuarios internos de la sucursal, las actividades de corrección se asignan directamente a ellos. Si no hay ninguno configurado, se asigna al administrador del sistema.

### 7. Asignación del partner correcto al carrito de eCommerce
El módulo `website_appointment_sale` asigna el carrito al usuario público (anónimo) durante el flujo de pago. Este módulo intercepta esa asignación y reasigna el carrito al partner real resuelto por teléfono, de modo que el pedido queda correctamente vinculado al cliente.

### 8. Modalidad de agendamiento público
Opción de configuración global (**Ajustes → Citas Salón**) que activa el modo de flujo completamente sin login:
- Oculta el enlace "Sign in" dentro del formulario de citas
- Oculta el botón "Sign Up" en la pantalla de confirmación de pedido (`/shop/confirmation`)

### 9. Búsqueda por teléfono en campos Many2one de partner
Los campos `partner_id` (sale.order), `manual_customer_id` (calendar.event) y cualquier otro Many2one a `res.partner` en el backend ahora incluyen **teléfono** y **celular** en la búsqueda predictiva del autocomplete, además de nombre y correo.

---

## Estructura de Archivos

```
salon_customer_unifier/
├── __manifest__.py
├── __init__.py
│
├── models/
│   ├── __init__.py
│   ├── res_partner.py          # Phone-First Match + búsqueda por teléfono
│   ├── appointment_type.py     # Campo salon_correction_user_ids
│   ├── res_config_settings.py  # Campo salon_public_booking_mode
│   └── res_website.py          # (vacío — reservado, no se usa)
│
├── controllers/
│   ├── __init__.py
│   ├── appointment.py          # Override submit + endpoints lookup/correction
│   └── website_sale.py         # Override _check_addresses (skip delivery step)
│
├── views/
│   ├── appointment_form_template.xml   # Herencia del form de citas
│   ├── appointment_type_views.xml      # Campo de responsables en tipo de cita
│   ├── res_config_settings_views.xml   # Sección "Citas Salón" en Ajustes
│   └── website_sale_templates.xml      # Ocultar Sign Up en confirmación
│
├── security/
│   └── ir.model.access.csv
│
└── static/src/
    ├── css/
    │   └── phone_widget.css            # Estilos del widget (.o_salon_field_locked)
    ├── js/
    │   └── phone_widget.js             # Lógica frontend (publicWidget)
    └── lib/intl-tel-input/             # Librería de selector de bandera
        ├── css/intlTelInput.min.css
        └── js/
            ├── intlTelInput.min.js
            └── utils.js
```

---

## Documentación Técnica

### Backend

#### `models/res_partner.py` — `ResPartner`

##### `_normalize_phone_e164(phone_number) → str`
Normaliza cualquier número de teléfono al formato E.164, con reglas específicas para México:
- 10 dígitos sin código → `+52XXXXXXXXXX`
- 12 dígitos comenzando con `52` → `+52XXXXXXXXXX`
- 13 dígitos comenzando con `521` → `+52XXXXXXXXXX` (elimina el `1` intermedio)

##### `find_or_create_by_phone(phone, name, email) → res.partner`
Estrategia en tres pasos:
1. **Match exacto** en `mobile` o `phone` con el número normalizado E.164
2. **Match parcial** por últimos 10 dígitos (tolera diferencias de formato entre registros)
3. **Creación** si no hay match — el nuevo partner tiene `customer_rank=1` y `lang='es_MX'`

En el paso 1 y 2, si el partner encontrado tiene campos vacíos (nombre o email), se actualizan con los datos proporcionados por el cliente (método `_update_partner_if_incomplete`).

##### `search_by_phone(phone) → res.partner`
Mismo algoritmo que `find_or_create_by_phone` pero **sin el paso de creación**. Usado por el endpoint `/appointment/partner_lookup` para el autocomplete del frontend sin efecto secundario.

##### `_search_display_name(operator, value) → domain`
Override de Odoo 18 que extiende el dominio de búsqueda predictiva de partners. En Odoo 18, el autocomplete de cualquier campo `Many2one` llama internamente a:
```
name_search → search_fetch([('display_name', op, value)]) → _search_display_name
```
El override agrega `phone` y `mobile` con OR al dominio resultante del `super()`, haciendo que todos los campos Many2one a `res.partner` (backend) busquen también por teléfono.

---

#### `models/appointment_type.py` — `AppointmentType`

```python
salon_correction_user_ids = fields.Many2many(
    comodel_name='res.users',
    relation='salon_correction_appointment_type_user_rel',
    column1='appointment_type_id',
    column2='user_id',
    string='Responsables de corrección de datos',
    domain=[('share', '=', False)],  # Solo usuarios internos
)
```

---

#### `models/res_config_settings.py` — `ResConfigSettings`

```python
salon_public_booking_mode = fields.Boolean(
    string='Modalidad de agendamiento público',
    config_parameter='salon_customer_unifier.public_booking_mode',
)
```

Almacena el valor en `ir.config_parameter` con la clave `salon_customer_unifier.public_booking_mode`. Se usa `ir.config_parameter` (y no un campo en `res.website`) para ser independiente del estado de instalación del módulo `website`.

En QWeb, la condición de visibilidad es:
```xml
request.env['ir.config_parameter'].sudo().get_param('salon_customer_unifier.public_booking_mode') != 'True'
```

---

#### `controllers/appointment.py` — `AppointmentPhoneMatch`

Hereda de `AppointmentController` (módulo `appointment`).

##### `appointment_form_submit(...)` — POST `/appointment/<id>/submit`
Cuatro pasos en el mismo request HTTP:

```
1. Extraer campos propios del kwargs (found_partner_id, correction_name, correction_email)
2. PHONE-FIRST MATCH: find_or_create_by_phone → almacenar en request._phone_matched_partner
3. super() → flujo nativo: crea calendar.booking + carrito eCommerce
4. _assign_partner_to_cart(customer) → reasignar carrito al partner real
5. Si hay solicitud de corrección → _create_data_correction_activity(...)
```

##### `_get_customer_partner()`
Hook del controller nativo para obtener el partner del cliente. Override: si existe `request._phone_matched_partner`, lo retorna directamente en lugar de ejecutar la búsqueda email-first nativa.

##### `appointment_partner_lookup(phone)` — JSON `/appointment/partner_lookup`
Endpoint público para el autocomplete del frontend. Retorna:
```json
{
  "found": true,
  "partner_id": 42,
  "name": "María García",
  "email": "maria@example.com",
  "has_email": true
}
```

##### `appointment_send_correction(...)` — JSON `/appointment/send_correction`
Endpoint AJAX independiente para enviar la solicitud de corrección sin necesidad de completar el formulario de cita. Llama internamente a `_create_data_correction_activity`.

##### `_create_data_correction_activity(found_partner_id, correction_name, correction_email, phone, appointment_type_id)`
1. Obtiene los `salon_correction_user_ids` del tipo de cita. Si no hay → fallback a `base.user_admin`
2. Construye una nota HTML con el teléfono y los datos correctos indicados por el cliente
3. Crea una `mail.activity` de tipo `mail.mail_activity_data_todo` por cada responsable:
   ```python
   partner.activity_schedule(
       act_type_xmlid='mail.mail_activity_data_todo',
       summary='Corrección de datos solicitada por el cliente',
       note=note,
       user_id=user.id,
       date_deadline=date.today(),
   )
   ```

##### `_assign_partner_to_cart(customer)`
Obtiene el carrito activo vía `request.website.sale_get_order()` y actualiza `partner_id`, `partner_invoice_id` y `partner_shipping_id` al partner resuelto por teléfono. Se ejecuta después de `super()` para garantizar que el carrito ya fue creado por `website_appointment_sale`.

---

### Frontend

#### `static/src/js/phone_widget.js` — `SalonPhoneIntlInput`

`publicWidget.Widget` con selector `.appointment_submit_form`.

##### Inicialización
- Instancia `intlTelInput` con `separateDialCode: true` (el `phoneInput.value` contiene solo el número nacional, sin el código de país)
- País inicial: México (`mx`), preferidos: MX, US, CO, AR
- Fallback nativo si intl-tel-input no está disponible

##### Validación de teléfono
`_getNationalDigits()` cuenta los dígitos del valor del input (número nacional ya separado del código de país por `separateDialCode`).

| Evento | Regla |
|--------|-------|
| `input` | Si dígitos > 10 → error inmediato. Si dígitos = 0 → limpiar nombre y email |
| `blur` | Si dígitos = 10 → trigger lookup. Si dígitos ≠ 10 y ≠ 0 → error |
| `countrychange` | Si dígitos = 10 → trigger lookup |
| Click "Confirmar" | Si dígitos ≠ 10 → prevenir submit y mostrar error |

##### Lookup y autocomplete
`_doPartnerLookup(phone)` hace un POST a `/appointment/partner_lookup` en formato JSON-RPC 2.0. Con el resultado:
- `found = true` → `_autocompleteFields()` + `_showPartnerMessage()` + guardar `found_partner_id` en hidden field
- `found = false` → mensaje estado `new`

`_triggerLookup()` incluye un guard para no repetir el lookup si el número E.164 no cambió (`_lastLookedPhone`).

##### Bloqueo de campos
`_lockField(input)`: agrega `readonly` y clase CSS `o_salon_field_locked`.
`_unlockFields()`: los quita. Se llama en `_resetPartnerState()` cuando el usuario edita el teléfono.

##### Flujo de corrección
1. Click "¿No eres tú?" → `_onNotYouClick()` → muestra `#o_salon_correction_form`
2. Click "Enviar solicitud" → `_onSendCorrection()` → AJAX a `/appointment/send_correction`
   - Si éxito: muestra confirmación en el form, oculta el botón, limpia hidden fields (evita duplicar la actividad al hacer submit del formulario principal)
3. Click "Cancelar" → `_onCancelCorrection()` → oculta form, limpia campos, re-ejecuta lookup
4. Al confirmar la cita → `_syncCorrectionHiddenFields()` copia los inputs visibles a los hidden fields `correction_name` y `correction_email` antes del submit

---

### Vistas

#### `views/appointment_form_template.xml`
Hereda `appointment.appointment_form`. Aplica 6 XPaths en orden secuencial (cada uno opera sobre el resultado del anterior):

| ID | Posición | Operación |
|----|----------|-----------|
| -1 | `replace` en `<t t-if="request.env.user._is_public()">` | Añade condición de modalidad pública |
| 0  | `after` en `input[name='csrf_token']` | Agrega hidden fields: `found_partner_id`, `correction_name`, `correction_email` |
| A  | `before` en `input[name='name']/../..` | Inserta campo Teléfono con intl-tel-input |
| B  | `attributes` en `input[name='name']` | Agrega `id="name_field"` |
| C  | `attributes` en `input[name='email']` | Agrega `id="email_field"` |
| E  | `replace` vacío en `//input[@name='email']/../../following-sibling::div[1]` | Elimina el campo Teléfono original |
| D  | `after` en `//input[@name='email']/../..` | Inserta área de mensaje inteligente + formulario de corrección |

> **Nota técnica:** Las comillas dobles en expresiones XPath dentro de atributos XML se escapan como `&quot;` (no como `\"`).

#### `views/appointment_type_views.xml`
Hereda `appointment.appointment_type_view_form`. Agrega el campo `salon_correction_user_ids` con widget `many2many_tags` en la pestaña "Opciones", después del campo `allow_guests`.

#### `views/res_config_settings_views.xml`
Hereda `base.res_config_settings_view_form`. Usa el patrón de Odoo 18:
```xml
<xpath expr="//form" position="inside">
    <app data-string="Citas Salón" name="salon_customer_unifier">
        <block title="Citas Salón">
            <setting ...>
                <field name="salon_public_booking_mode"/>
            </setting>
        </block>
    </app>
</xpath>
```
> **Nota técnica Odoo 18:** El XPath es `//form` (no `//div[hasclass('settings')]` como en Odoo 16/17). Los bloques usan `<app>`, `<block>` y `<setting>` (no `div.app_settings_block`).

#### `views/website_sale_templates.xml`
Contiene dos templates:

1. **`salon_hide_signup_confirmation`** — Hereda `website_sale.confirmation`. Agrega la condición de modalidad pública al `<t t-if>` que controla el botón "Sign Up" (visible solo cuando la modalidad pública está desactivada).

2. *(Eliminado)* — El botón "Sign In" del navbar (`portal.user_sign_in`) se dejó visible para todos ya que es útil para que el personal interno acceda al backend.

---

## Dependencias

```python
depends = [
    'appointment',              # Módulo base de citas
    'website_appointment',      # Flujo de citas en website
    'website_appointment_sale', # Integración citas + eCommerce (carrito)
    'website_sale',             # eCommerce base
    'phone_validation',         # Validación de teléfonos (Odoo)
]
```

> El módulo `website` **no** se declara explícitamente — viene como dependencia transitiva de `website_sale`. Esto permite que el módulo cargue incluso en bases de datos donde `website` no está instalado directamente.

---

## Configuración

### 1. Modalidad de agendamiento público
**Ajustes → Citas Salón → Modalidad de agendamiento público**

Al activar esta opción:
- El enlace "Sign in" desaparece del formulario de citas (el cliente no necesita cuenta)
- El botón "Sign Up" desaparece de la pantalla `/shop/confirmation`

### 2. Responsables de corrección por sucursal
**Tipo de cita → Opciones → Responsables de corrección de datos**

Seleccionar uno o más usuarios internos. Cuando un cliente pulse "¿No eres tú?" y envíe su solicitud, cada usuario configurado recibirá una actividad "Hacer" en el contacto del cliente con los datos correctos.

Si no se configura ningún usuario, la actividad se asigna al administrador del sistema.

---

## Flujo Completo — Cita de Cliente Nuevo

```
Cliente llega a /appointment
     │
     ▼
Ingresa teléfono (10 dígitos)
     │
     ▼ (blur)
GET /appointment/partner_lookup
     │
     ├─ Partner encontrado ──► Autocomplete nombre/email
     │                         Campos bloqueados (readonly)
     │                         Mensaje verde "¡Hola [Nombre]!"
     │                         Link "¿No eres tú?"
     │
     └─ No encontrado ────────► Mensaje azul "Primera visita"
                                Campos libres para captura
     │
     ▼
Cliente confirma la cita
     │
     ▼ (click "Confirmar Cita")
Validación 10 dígitos + E.164
_syncCorrectionHiddenFields()
POST /appointment/<id>/submit
     │
     ▼ (controller override)
find_or_create_by_phone()
     │
     ▼
super().appointment_form_submit()
  └─ _get_customer_partner() → retorna partner resuelto
  └─ Crea calendar.booking
  └─ Crea sale.order (carrito)
     │
     ▼
_assign_partner_to_cart()
  └─ sale_order.partner_id = cliente real
     │
     ▼ (si había solicitud de corrección)
_create_data_correction_activity()
  └─ mail.activity → responsables de sucursal
     │
     ▼
Redirect → /shop/payment
```

---

## Changelog

### 18.0.1.3.0 (actual)
- **Nuevo:** Búsqueda por teléfono en autocomplete backend (`_search_display_name`)
- **Nuevo:** Modalidad de agendamiento público en `res.config.settings` (usa `ir.config_parameter`)
- **Nuevo:** Ocultar "Sign Up" en `/shop/confirmation` en modalidad pública
- **Fix:** Migración de `res.website` field a `ir.config_parameter` (evita error de registry en DBs sin `website` instalado)
- **Fix:** Escape correcto de comillas en XPath XML (`&quot;` en lugar de `\"`)
- **Fix:** Patrón de settings Odoo 18 (`//form` + `<app>/<block>/<setting>`)

### 18.0.1.2.0
- **Nuevo:** Responsables de corrección de datos por tipo de cita (`salon_correction_user_ids`)
- **Nuevo:** Endpoint AJAX independiente `/appointment/send_correction`
- **Nuevo:** Botón "Enviar solicitud" en formulario de corrección (sin necesidad de completar la cita)
- **Nuevo:** Limpiar nombre/email al borrar el campo teléfono

### 18.0.1.1.0
- **Nuevo:** Flujo "¿No eres tú?" con formulario de corrección y actividad en el partner
- **Nuevo:** Bloqueo de campos nombre/email al encontrar partner (`_lockField`)
- **Nuevo:** Hidden fields: `found_partner_id`, `correction_name`, `correction_email`

### 18.0.1.0.0
- **Nuevo:** Phone-First Match (`find_or_create_by_phone`)
- **Nuevo:** intl-tel-input con validación de 10 dígitos nacionales
- **Nuevo:** Autocomplete nombre/email por lookup de teléfono
- **Nuevo:** Mensaje inteligente: `found` / `found_no_email` / `new`
- **Nuevo:** Reordenamiento de campos en formulario de citas (Teléfono → Nombre → Email)
- **Nuevo:** Asignación del partner correcto al carrito eCommerce (`_assign_partner_to_cart`)
- **Nuevo:** Skip del paso de delivery en eCommerce (`_check_addresses` override)
