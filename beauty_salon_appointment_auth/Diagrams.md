# 📊 Diagramas de Flujo

## 🔄 Flujo General del Módulo

```
                          Usuario accede a Cita
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │ ¿require_login = True? │
                     └──────────┬─────────────┘
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
              SÍ │                             │ NO
                 ▼                             ▼
    ┌──────────────────────┐      ┌────────────────────┐
    │ ¿Usuario Público?    │      │ Flujo Normal Odoo  │
    └──────┬───────────────┘      │ (sin cambios)      │
           │                       └────────────────────┘
     ┌─────┴──────┐
     │            │
  SÍ │            │ NO
     ▼            ▼
┌─────────┐  ┌──────────────┐
│ Mostrar │  │ Flujo Normal │
│ Login/  │  │ Odoo         │
│ Signup  │  │ (autenticado)│
└────┬────┘  └──────────────┘
     │
     ▼
┌─────────────────────┐
│ Usuario elige:      │
│ • Login             │
│ • Signup            │
└──────┬──────────────┘
       │
       ▼
┌────────────────────────────┐
│ Redirect con URL completa  │
│ (todos los parámetros)     │
└───────────┬────────────────┘
            │
            ▼
┌────────────────────────────┐
│ Autenticación Odoo         │
│ (login/signup nativo)      │
└───────────┬────────────────┘
            │
            ▼
┌────────────────────────────┐
│ Redirige a formulario      │
│ con parámetros preservados │
└───────────┬────────────────┘
            │
            ▼
┌────────────────────────────┐
│ Autocompletar formulario   │
│ con datos del usuario      │
└───────────┬────────────────┘
            │
            ▼
┌────────────────────────────┐
│ Mostrar botón apropiado:   │
│ • Proceed to Payment       │
│ • Confirm Appointment      │
└────────────────────────────┘
```

---

## 🎯 Casos de Uso Específicos

### Caso 1: Usuario Público + Cita con Pago

```
Usuario Público
    │
    ▼
┌──────────────────────────────┐
│ Selecciona fecha/hora        │
│ (calendario normal)          │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ Llega al formulario          │
│ (appointment/X/info)         │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ 🔒 VE:                       │
│ "Inicia sesión para          │
│  continuar"                  │
│                              │
│ [Ya tengo cuenta]            │
│ [Crear cuenta]               │
│                              │
│ ❌ NO VE:                    │
│ - Proceed to Payment         │
└───────────┬──────────────────┘
            │
            ├──── Click "Ya tengo cuenta"
            │         │
            │         ▼
            │    ┌─────────────────┐
            │    │ Login Form      │
            │    │ /web/login      │
            │    └────────┬────────┘
            │             │
            │             ▼
            │    ┌─────────────────┐
            │    │ Credenciales    │
            │    └────────┬────────┘
            │             │
            └──── Click "Crear cuenta"
                      │
                      ▼
                 ┌─────────────────┐
                 │ Signup Form     │
                 │ /web/signup     │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Nueva cuenta    │
                 └────────┬────────┘
                          │
            ┌─────────────┴─────────────┐
            │ AMBOS LLEGAN AQUÍ         │
            ▼                           ▼
┌──────────────────────────────┐
│ Redirect automático a:       │
│ /appointment/X/info?...      │
│ (con TODOS los parámetros)   │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ Formulario con datos         │
│ autocompletados              │
│                              │
│ Nombre: [Juan Pérez]         │
│ Email: [juan@...]            │
│ Tel: [+52...]                │
│                              │
│ [Proceed to Payment] ✅      │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ Click "Proceed to Payment"   │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ /shop/cart                   │
│ (Carrito con producto)       │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ Checkout → Pago              │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ ✅ Cita Confirmada           │
│ 1 solo contacto creado       │
└──────────────────────────────┘
```

---

### Caso 2: Usuario Autenticado + Cita sin Pago

```
Usuario Autenticado
    │
    ▼
┌──────────────────────────────┐
│ Selecciona fecha/hora        │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ Llega al formulario          │
│ (datos ya prellenados)       │
│                              │
│ Nombre: [Juan Pérez] ✅      │
│ Email: [juan@...] ✅         │
│ Tel: [+52...] ✅             │
│                              │
│ [Confirm Appointment] ✅     │
│                              │
│ ❌ NO VE:                    │
│ - Botones login/signup       │
│ - Proceed to Payment         │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ Click "Confirm Appointment"  │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│ ✅ Cita Confirmada           │
│ (sin pasar por carrito)      │
└──────────────────────────────┘
```

---

## 🔐 Flujo de Autenticación Detallado

### Preservación de Parámetros en URL

```
URL Original:
/appointment/8/info?date_time=2025-10-28+11:30:00&duration=0.5&staff_user_id=26

           │
           │ Usuario click "Ya tengo cuenta"
           ▼

JavaScript captura URL completa:
var currentUrl = window.location.pathname + window.location.search

           │
           │ URL encoding
           ▼

redirectParam = encodeURIComponent(currentUrl)
// Resultado: %2Fappointment%2F8%2Finfo%3Fdate_time%3D2025-10-28...

           │
           │ Construye URL de login
           ▼

loginUrl = '/web/login?redirect=' + redirectParam
// Resultado: /web/login?redirect=%2Fappointment%2F8%2Finfo%3F...

           │
           │ Usuario hace login
           ▼

Odoo procesa 'redirect' parameter
// Decodifica: /appointment/8/info?date_time=2025-10-28+11:30:00...

           │
           │ Redirect automático
           ▼

Usuario regresa a:
/appointment/8/info?date_time=2025-10-28+11:30:00&duration=0.5&staff_user_id=26

✅ TODOS los parámetros preservados
```

---

## 🎨 Interfaz de Usuario

### Vista para Usuario Público

```
┌─────────────────────────────────────────────────────┐
│ Pop! Studio                                  [≡]    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Agregue más detalles sobre usted o                │
│  Iniciar sesión                                     │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │ Nombre completo*                          │     │
│  │ [Por ejemplo, Juan Pérez           ]      │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │ Correo electrónico*                       │     │
│  │ [Por ejemplo, juan@ejemplo.com     ]      │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │ Número de teléfono*                       │     │
│  │ [Por ejemplo, +1(605)691-3277      ]      │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 🔒 Inicia sesión para continuar            │   │
│  │                                             │   │
│  │ Necesitas tener una cuenta para reservar   │   │
│  │ Light Brows - Cumbres.                     │   │
│  │                                             │   │
│  │        [Ya tengo una cuenta]                │   │
│  │        [Crear una cuenta]                   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Vista para Usuario Autenticado

```
┌─────────────────────────────────────────────────────┐
│ Pop! Studio                    [🛒 1]  [👤 Juan] [≡] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Agregue más detalles sobre usted                  │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │ Nombre completo*                          │     │
│  │ [Juan Pérez                        ]  ✅  │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │ Correo electrónico*                       │     │
│  │ [juan@ejemplo.com                  ]  ✅  │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │ Número de teléfono*                       │     │
│  │ [+52 871 564 0952                  ]  ✅  │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│                     [Proceder al pago] ✅          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📱 Responsive Design

### Desktop (> 768px)
```
┌─────────────────────────────────────────────────┐
│         Formulario          │    Resumen Cita   │
│                             │                   │
│  [Campos del formulario]    │  📅 Fecha         │
│                             │  ⏰ Hora          │
│                             │  👤 Staff         │
│  [Botones]                  │  💰 Precio        │
└─────────────────────────────────────────────────┘
```

### Móvil (< 768px)
```
┌─────────────────┐
│   Formulario    │
│                 │
│  [Campos]       │
│                 │
│  [Botones]      │
│                 │
├─────────────────┤
│  Resumen Cita   │
│                 │
│  📅 Fecha       │
│  ⏰ Hora        │
│  👤 Staff       │
│  💰 Precio      │
└─────────────────┘
```

---

*Última actualización: 28 de Octubre, 2025*