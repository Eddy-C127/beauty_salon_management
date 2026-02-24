# Beauty Salon - File Management

**Gestión de Expedientes Clínicos de Clientas para Salones de Belleza**

Módulo Odoo 18 para la gestión integral de expedientes clínicos en salones de belleza y estéticas. Cumple con **NOM-004-SSA3-2012** (expedientes clínicos) y **LFPDPPP** (protección de datos personales en México).

**Versión**: 18.0.3.0.0

---

## Funcionalidades

### Expediente Clínico por Clienta
- Registro de alergias, tipo de piel, condiciones médicas y medicamentos actuales
- Pestaña dedicada "Expediente Clínico" en la ficha del contacto (primera pestaña)
- Cuestionarios dinámicos según tipo de servicio: Facial, Capilar, Corporal
- Smart button con porcentaje de completitud del expediente (verde = completo, rojo = incompleto)
- Notas privadas visibles solo para managers

### Progreso y Vigencia del Expediente _(Nuevo en v3)_
- **Barra de progreso** visual (0-100%) calculada sobre los campos clínicos clave:
  - Aviso de privacidad aceptado → 40 pts (obligatorio LFPDPPP)
  - Alergias documentadas → 30 pts
  - Condiciones médicas → 20 pts
  - Tipo de piel → 10 pts
- Badge **Expediente Completo** (verde) / **Incompleto** (rojo) en la pestaña
- Badge **Requiere Actualización** (amarillo) si el expediente tiene más de 12 meses sin actualizarse
- Fecha de última actualización registrada automáticamente al modificar campos clínicos

### Intercepción Inteligente antes de Iniciar Cita _(Nuevo en v3)_
- Al pulsar **Iniciar Cita**, el sistema verifica el expediente según el nivel requerido por el servicio
- Si está incompleto, abre el **Wizard de Expediente Rápido** mostrando _solo los campos que faltan_
- Dos opciones:
  - **Guardar y Continuar**: guarda los datos al partner y abre el wizard normal
  - **Omitir (Emergencia)**: continúa sin completar, registra en el chatter con usuario, motivo y timestamp (auditable)
- Si el expediente ya está completo → el wizard de inicio de cita se abre directamente sin interrupciones

### Nivel de Expediente por Tipo de Servicio _(Nuevo en v3)_
- Campo **Nivel de Expediente Requerido** en cada tipo de cita (`appointment.type`):
  - **Básico**: Solo aviso de privacidad (ej. corte, uñas)
  - **Intermedio**: Aviso + alergias (ej. tintes, tratamientos)
  - **Clínico**: Expediente completo (ej. micropigmentación, químicos, láser)
- La intercepción solo pide los campos necesarios para ese nivel — no más, no menos

### Historial de Sesiones con Fotos Antes/Después
- Cada sesión registra: fotos (antes y después), productos usados, notas internas, recomendaciones de cuidado, reacciones adversas y nivel de satisfacción
- Firma digital de consentimiento informado por sesión
- Trazabilidad completa vía mail.thread

### Flujo de Trabajo: Iniciar / Concluir Cita
- **Wizard Iniciar Cita**: Captura foto antes, muestra alertas médicas, solicita firma de consentimiento
- **Wizard Concluir Cita**: Captura foto después (obligatoria), notas de sesión, productos usados, nivel de satisfacción
- Estados de cita: Reservada → En Curso → Concluida / Cancelada
- Botones de acción rápida en vista kanban, lista y formulario

### Vista Kanban Mobile-First
- Tarjetas ordenadas de más antigua a más reciente (horario del día)
- **Badges de urgencia** visuales basados en el reloj:
  - Rojo neón pulsante + badge "AHORA": cita en los próximos 30 minutos
  - Naranja + badge "PROXIMA": cita entre 30 min y 2 horas
  - Normal: más de 2 horas
- Muestra clienta, hora, servicio, artista asignada y estado del expediente

### Dashboard y Auditoría _(Tablero Pop Studio)_
- **Tablero Pop Studio** (módulo board): 4 bloques en layout 2-1
  - Gráfica de barras apiladas: Citas por Artista (Completos vs Faltantes)
  - Tabla pivot: Detalle por Artista × Periodo
  - Gráfica de pie: Proporción general
  - Lista: Expedientes faltantes que requieren atención
- **Dashboard de Citas**: gráficas individuales con filtros de fecha
- **Reporte de Cumplimiento**: pivot por artista y mes
- Filtros: Hoy / Esta Semana / Quincena / Este Mes / Mes Anterior
- Agrupación: Artista / Servicio / Día / Semana / Mes / Trimestre

### Alertas Automáticas vía Odoo Bot
- Cron job cada hora detecta citas concluidas hace +2h sin expediente
- Notificación directa al artista responsable vía mensajería interna

### Diseño Mobile-First
- Wizards con patrón Bottom Sheet en dispositivos móviles
- Botones FAB (Floating Action Button) duplicados en formulario para mobile
- Apertura automática de cámara en campos de imagen
- Lightbox viewer para fotos de expedientes
- Gesture swipe-to-close en modals

### Cumplimiento Normativo
- **NOM-004-SSA3-2012**: Estructura de expediente clínico con datos médicos básicos
- **LFPDPPP Art. 8**: Consentimiento expreso requerido antes de registrar datos médicos
- Registro automático de fecha de aceptación del aviso de privacidad
- Validación que impide guardar datos médicos sin aviso de privacidad aceptado
- Bypass de emergencia auditado con usuario, motivo y timestamp en chatter

---

## Requisitos

- Odoo 18 Community o Enterprise
- Módulos base requeridos: `beauty_salon`, `mail`, `calendar`, `appointment`, `contacts`, `board`

---

## Instalación

```bash
# Instalación vía CLI (Docker)
docker exec odoo18_dev odoo -c /etc/odoo/odoo.conf -d DEVTEST15DIC \
  -u beauty_salon_file_management --stop-after-init --no-http
```

---

## Estructura del Módulo

```
beauty_salon_file_management/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── expediente_sesion.py      # popstudio.expediente.sesion
│   ├── calendar_event.py         # Extensión de calendar.event
│   ├── res_partner.py            # Extensión de res.partner (expediente + progreso)
│   └── appointment_type.py       # Extensión de appointment.type (nivel requerido)
├── wizard/
│   ├── __init__.py
│   ├── wizard_expediente_rapido.py  # Intercepción pre-cita (nuevo v3)
│   ├── wizard_iniciar_cita.py
│   └── wizard_concluir_cita.py
├── security/
│   ├── popstudio_security.xml
│   └── ir.model.access.csv
├── data/
│   └── ir_cron_data.xml
├── views/
│   ├── expediente_sesion_views.xml
│   ├── calendar_event_views.xml
│   ├── res_partner_views.xml
│   ├── wizard_expediente_rapido_views.xml  # (nuevo v3)
│   ├── wizard_iniciar_cita_views.xml
│   ├── wizard_concluir_cita_views.xml
│   ├── auditoria_views.xml
│   ├── dashboard_board_views.xml
│   └── menu_actions.xml
└── static/
    ├── description/
    │   └── icon.png
    └── src/
        ├── css/popstudio_mobile.css
        └── js/components/mobile_wizard.js
```

---

## Grupos de Seguridad

| Grupo | Permisos |
|-------|----------|
| **Recepcionista** | Ver citas, expedientes básicos, wizard expediente rápido |
| **Artista / Estilista** | Iniciar/concluir citas, gestionar expedientes, wizard expediente rápido |
| **Manager / Coordinador** | Acceso completo: auditoría, reportes, dashboard, notas privadas, configuración de niveles |

---

## Changelog

### v3.0.0
- Barra de progreso del expediente en res.partner (0-100%)
- Campo `expediente_listo` computado por campos clínicos clave
- Vigencia del expediente: alerta de "Requiere Actualización" a los 12 meses
- Wizard de expediente rápido (intercepción pre-cita)
- Bypass de emergencia con log auditable en chatter
- Nivel de expediente requerido por tipo de servicio (Básico / Intermedio / Clínico)
- Tablero Pop Studio (board module) con 4 bloques de KPIs
- Dashboard de citas con filtros de fecha (día / semana / quincena / mes)
- Badges de urgencia en kanban (AHORA / PROXIMA) basados en reloj del servidor
- Tarjetas kanban ordenadas de más antigua a más reciente
- Artista asignada visible en tarjeta kanban
- Campo `expediente_faltante_count` para dashboards

### v2.0.0
- Vista kanban mobile-first para citas
- Lightbox viewer para fotos de expedientes
- Alertas de alergias en calendar.event form
- Pestaña expediente como primera en res.partner

### v1.1.0
- Flujo Iniciar/Concluir con wizards mobile-first
- Fotos antes/después con Many2many ir.attachment
- Firma digital de consentimiento

---

## Autor

**Smartgeeks**
- Web: [smartgeeks.mx](https://smartgeeks.mx)
- Contacto: contacto@smartgeeks.mx
