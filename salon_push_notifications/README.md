# salon_push_notifications

## Push Notifications para Citas — Odoo 18

Módulo custom para enviar push notifications automáticas a los clientes cuando reservan una cita, y recordatorios antes de que esta ocurra.

---

## Requisitos

| Dependencia | Notas |
|---|---|
| `appointment` | Enterprise — módulo de citas |
| `social_push_notifications` | Enterprise — Firebase FCM |
| `website` | Módulo de sitio web |
| Firebase configurado | Credenciales en **Ajustes → Website → Push Notifications** |
| `pwa_public_landing` | Recomendado — PWA para que los usuarios puedan suscribirse a push |

> El cliente debe haber visitado el sitio web, aceptado el permiso de notificaciones push, y estar vinculado a un `res.partner` (lo cual ocurre automáticamente cuando hace una cita desde el website estando autenticado o al identificarse durante el booking).

---

## Funcionalidades

### 1. Confirmación de reserva (inmediata)

Cuando se crea una `calendar.event` con:
- `appointment_type_id` — es una cita, no un evento genérico
- `appointment_booker_id` — tiene un cliente asignado

Se envía automáticamente una push notification al cliente con:

```
Título: ¡Cita confirmada!
Cuerpo:  <Nombre del servicio> confirmada para el DD/MM/YYYY a las HH:MM.
```

La confirmación es **no-bloqueante**: si el cliente no tiene suscripción push activa, se omite silenciosamente sin afectar la creación de la cita.

### 2. Recordatorios automáticos (cron)

Un cron llamado **"Salon: Send Push Reminder Notifications"** corre cada 15 minutos y revisa todas las citas futuras (próximos 7 días) que no estén canceladas.

**Flujo de decisión:**

```
¿La cita tiene alarm_ids configuradas?
    SÍ → Para cada alarma no enviada:
             ¿trigger_time está en la ventana del cron?
                 SÍ → Enviar push + marcar alarma como enviada
                 NO → Esperar al próximo ciclo
    NO → Usar fallback de Settings:
             ¿trigger_time (start - fallback_hours) está en la ventana?
                 SÍ → Enviar push genérico "mañana tienes cita"
```

**Mensaje del recordatorio:**
```
Título: Recordatorio: <Nombre del servicio>
Cuerpo:  Tienes <Nombre del servicio> en <N> hora(s) (DD/MM/YYYY a las HH:MM).
```

**Anti-duplicados:** Cada alarma solo se envía una vez por evento. Se registra en la tabla `calendar_event_push_reminder_rel`.

---

## Configuración

Ve a **⚙️ Ajustes → Push Notifications Citas**:

| Campo | Descripción | Default |
|---|---|---|
| **Habilitar notificaciones push de citas** | Activa/desactiva todo el módulo | Activado |
| **Horas de recordatorio (fallback)** | Horas antes de la cita para el recordatorio cuando el Tipo de Cita no tiene alarmas configuradas | 24 horas |

### Configurar alarmas en el Tipo de Cita

El módulo lee los **Recordatorios** del `Appointment Type` (`appointment.type.reminder_ids`), que son registros de `calendar.alarm`.

Para añadirlos:
1. Ve a **Citas → Configuración → Tipos de cita**
2. Abre el tipo de cita deseado
3. En el campo **Recordatorios**, agrega las alarmas que quieras

Ejemplos comunes:
- `Email - 3 Hours` → Push 3 horas antes
- `Email - 1 Days` → Push 24 horas antes
- `Notification - 15 Minutes` → Push 15 minutos antes

> El módulo envía la push para **todos** los tipos de alarma configurados (email, notification, sms), ya que solo usa el `duration_minutes` de cada alarma para calcular el momento de envío.

---

## Instalación

```bash
# Docker
docker exec <contenedor> odoo -c /etc/odoo/odoo.conf -d <base_de_datos> \
  -i salon_push_notifications --stop-after-init

# Sin Docker
odoo -c /etc/odoo/odoo.conf -d <base_de_datos> \
  -i salon_push_notifications --stop-after-init
```

> **Prerrequisito:** El módulo `social_push_notifications` debe estar instalado y con Firebase configurado. Ver `pwa_public_landing/INSTALACION_PRODUCCION.md` para la guía completa de configuración de Firebase.

---

## Estructura del módulo

```
salon_push_notifications/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── calendar_event.py        # Override create() + métodos de push + cron
│   └── res_config_settings.py   # Campos de configuración en Settings
├── data/
│   └── ir_cron.xml              # Cron "Salon: Send Push Reminder Notifications"
├── views/
│   └── res_config_settings_views.xml
├── security/
│   └── ir.model.access.csv
└── README.md
```

---

## Campos añadidos a `calendar.event`

| Campo | Tipo | Descripción |
|---|---|---|
| `push_notif_confirmed` | Boolean | `True` si ya se envió la confirmación de reserva |
| `push_notif_reminder_sent_ids` | Many2many → `calendar.alarm` | Alarmas cuyo recordatorio ya fue enviado |
| `push_notif_fallback_reminder_sent` | Boolean | `True` si se envió el recordatorio fallback (sin alarmas configuradas) |

Estos campos son de solo rastreo interno. No se copian al duplicar un evento (`copy=False`).

---

## Parámetros de sistema (`ir.config_parameter`)

| Clave | Descripción | Default |
|---|---|---|
| `salon_push_notifications.enabled` | Habilita el módulo (`'True'`/`'False'`) | `'True'` |
| `salon_push_notifications.reminder_hours` | Horas fallback para recordatorio | `'24'` |

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| No llega la confirmación al crear la cita | El cliente no tiene suscripción push activa | Verificar con `env['website.visitor'].search([('partner_id','=',partner.id),('has_push_notifications','=',True)])` |
| No llegan recordatorios | El cron está detenido | Ajustes → Técnico → Acciones programadas → "Salon: Send Push Reminder Notifications" → Ejecutar manualmente |
| No llegan recordatorios aunque el cron corre | Las alarmas del tipo de cita no tienen `duration_minutes` en rango | Verificar que las alarmas están configuradas y que el evento está dentro de los próximos 7 días |
| Error en logs: `no push account found` | El `social.account` de push no existe o está inactivo | Verificar en Marketing → Social Marketing → Cuentas |
| El recordatorio se envió varias veces | No debería ocurrir — tabla `calendar_event_push_reminder_rel` previene duplicados | Revisar si hay múltiples instancias del cron corriendo en paralelo |

### Verificar suscriptores con push vinculados a partner

```bash
docker exec -i <contenedor> odoo shell -c /etc/odoo/odoo.conf -d <base_de_datos> --no-http << 'EOF'
visitors = env['website.visitor'].search([
    ('has_push_notifications', '=', True),
    ('partner_id', '!=', False),
])
for v in visitors:
    print(f"Visitor {v.id} → Partner: {v.partner_id.name}")
print(f"Total: {len(visitors)}")
EOF
```

### Ejecutar el cron manualmente

```bash
docker exec -i <contenedor> odoo shell -c /etc/odoo/odoo.conf -d <base_de_datos> --no-http << 'EOF'
env['calendar.event']._cron_send_push_reminders()
env.cr.commit()
print("OK")
EOF
```

### Ver recordatorios enviados para una cita

```sql
SELECT alarm_id FROM calendar_event_push_reminder_rel WHERE event_id = <ID_EVENTO>;
```

---

## Cómo se resuelve el caso de clientes invitados (guest)

### El problema

Un visitante anónimo acepta push → `website.visitor` con `has_push_notifications=True` pero `partner_id=False`. Agenda una cita sin hacer login → Odoo crea un `res.partner` y lo asigna a `appointment_booker_id`. El módulo busca visitantes con `partner_id == booker`, pero el visitor anónimo nunca se vincula → push no llega.

### La solución: `_link_visitor_to_booker(partner)`

Al crear la cita, **antes** de enviar la confirmación, el módulo transfiere las push subscriptions del visitor de la sesión actual al visitor del partner:

```
Visitor anónimo #44576          Visitor del partner #44700
  access_token = "abc123..."  →   access_token = "113"  (= str(partner.id))
  partner_id = NULL               partner_id = res.partner#113  (computed)
  push_subscription_ids = [T1]    push_subscription_ids = [T1]  ← transferido
```

El visitor anónimo sigue existiendo (no se borra), pero sus tokens ahora pertenecen al visitor del partner. La DB tiene `UNIQUE(push_token)` en la tabla de subscripciones, lo que hace la transferencia atómica e imposible de duplicar.

### Guards de seguridad (todos deben pasar)

| Guard | Qué protege |
|---|---|
| Solo en contexto HTTP | No corre en cron ni shell — imposible mezclar sesiones inexistentes |
| Solo en website request | No corre en el backend `/web` de Odoo |
| `visitor.partner_id` debe ser vacío | Nunca sobreescribe un vínculo ya existente — protege usuarios logueados |
| `visitor.has_push_notifications` | Solo actúa si hay tokens que transferir |
| `partner_visitor.has_push_notifications == False` | Si el partner ya tiene tokens propios, no mezcla — sus tokens son correctos |
| `try/except` global | Cualquier error inesperado no afecta la reserva de la cita |

### Limitación inherente (dispositivos compartidos)

Si dos personas usan el mismo navegador/dispositivo (misma cookie de sesión), comparten el mismo `website.visitor`. En ese caso, el push token del dispositivo quedaría vinculado a las citas del último en agendar. Esto es una limitación de la tecnología push, no del módulo. La única solución completa es requerir login para agendar.

---

## Notas técnicas

- **SQL directo para actualizaciones de rastreo**: Al marcar alarmas como enviadas (`push_notif_reminder_sent_ids`) y confirmar envíos (`push_notif_confirmed`), el módulo usa `env.cr.execute()` en lugar del ORM para evitar side effects del `write()` de `calendar.event` en otros módulos (beauty_salon, appointment, google_calendar) que pueden desencadenar creación de registros `calendar.alarm` con `name=NULL`.

- **Ventana del cron**: El cron tiene una ventana de **15 minutos** (igual que su intervalo de ejecución). Solo procesa alarmas cuyo `trigger_time` (= `event.start - alarm.duration`) caiga dentro de esa ventana.

- **Alcance del cron**: Solo procesa eventos con `start` en los próximos 7 días para eficiencia. Esto cubre todos los casos prácticos de recordatorio.

- **Silencioso ante ausencias**: Si el cliente no tiene suscripción push, si Firebase no está configurado, o si el módulo está desactivado, todas las operaciones se omiten sin lanzar excepciones visibles al usuario.

---

*Módulo: salon_push_notifications v18.0.1.0.0*
*Probado en: Odoo 18.0 Enterprise*
*Depende de: pwa_public_landing + social_push_notifications (Firebase FCM)*
