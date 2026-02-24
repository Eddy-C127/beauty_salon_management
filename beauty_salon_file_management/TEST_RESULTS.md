# Resultados de Tests — popstudio_expediente

Fecha: 2026-02-23
DB: DEVTEST15DIC
Version modulo: 18.0.1.0.0

## Resumen

| Test | Estado | Notas |
|------|--------|-------|
| 1.1 Instalacion | PASS | Instalacion limpia despues de aplicar 4 fixes previos |
| 2.1 Tablas creadas | PASS | 22 columnas en `popstudio_expediente_sesion` |
| 2.2 Campos partner | PASS | 8/8 campos extendidos presentes |
| 2.3 Campos calendar | PASS | 8/8 campos extendidos presentes |
| 2.4 Grupos seguridad | PASS | 3 grupos: Recepcionista, Artista, Manager |
| 3.1 Crear clienta | PASS | Partner creado con aviso_privacidad_fecha auto-set |
| 3.2 Crear sesion | PASS | Sesion ID=1, display_name correcto |
| 3.3 Foto obligatoria | PASS | ValidationError al marcar completada sin foto |
| 3.4 Proteccion campo | NOTA | No aplica en shell (usuario __system__), validado en codigo |
| 3.5 LFPDPPP | PASS | ValidationError al guardar alergias sin aviso |
| 3.6 Flujo completo | PASS | Sesion en_curso -> completada OK |
| 3.7 Cron alertas | PASS | Retorna True sin excepciones |
| 4.1 Vistas XML | PASS | 10 vistas registradas (form, list, kanban, search, wizards) |
| 4.2 Menus | PASS | 9 menus Pop Studio registrados |
| 4.3 Acciones | PASS | 5 acciones (Citas, Expedientes, Faltantes, Auditoria, Sesiones) |
| 4.4 Cron registrado | PASS | active=true, interval_type=hours |
| 6.x Regresion post-fix | PASS | Todos los tests 3.1, 3.3, 3.5, 3.6, 3.7 pasaron |

## Errores Encontrados y Corregidos

### Error 1: CSV con comentarios `#` (Bloqueante)
- **Archivo:** `security/ir.model.access.csv`
- **Problema:** Lineas de comentario `# -- ...` causaban `IndexError: list index out of range`
- **Fix:** Eliminadas todas las lineas de comentario del CSV

### Error 2: Campo `numbercall` inexistente en ir.cron (Bloqueante)
- **Archivo:** `data/ir_cron_data.xml`
- **Problema:** `numbercall` fue eliminado en Odoo 18, causaba `ValueError: Invalid field 'numbercall'`
- **Fix:** Removido el campo `numbercall` del XML del cron

### Error 3: `base_automation_data.xml` con `action_server_id = False` (Bloqueante)
- **Archivo:** `data/base_automation_data.xml`
- **Problema:** `action_server_id` no existe en `base.automation` de Odoo 18
- **Fix:** Removido el archivo del manifest (comentado). Requiere rediseno para Odoo 18

### Error 4: `editable="0"` invalido en list view (Bloqueante)
- **Archivo:** `views/res_partner_views.xml`
- **Problema:** `editable` solo acepta "top" o "bottom", no "0"
- **Fix:** Removido atributo `editable="0"` (las listas son no editables por defecto)

### Error 5: XPath `//div[hasclass('o_field_widget')]` no encontrado (Bloqueante)
- **Archivo:** `views/calendar_event_views.xml`
- **Problema:** El selector no existia en la vista padre de calendar.event
- **Fix:** Cambiado a `//div[@name='button_box']` position="after"

### Error 6: `<label>` sin atributo `for` (Bloqueante)
- **Archivo:** `views/wizard_iniciar_cita_views.xml`
- **Problema:** Odoo 18 requiere `for` en `<label>` o `class="o_form_label"`
- **Fix:** Cambiado `<label>` a `<span class="o_form_label">`

### Error 7: Orden incorrecto de XML en manifest (Bloqueante)
- **Archivo:** `__manifest__.py`
- **Problema:** `menu_actions.xml` se cargaba antes que `auditoria_views.xml`, pero referencia acciones definidas ahi
- **Fix:** Movido `auditoria_views.xml` antes de `menu_actions.xml`

### Error 8: XPath `//header` no existe en calendar.event (Bloqueante en update)
- **Archivo:** `views/calendar_event_views.xml`
- **Problema:** `calendar.event` form no tiene `<header>`, fallo en `-u` update
- **Fix:** Botones movidos al `//div[@name='button_box']`, statusbar y alertas despues de button_box

### Error 9: `aviso_privacidad_fecha` no se establece en create (Bug logico)
- **Archivo:** `models/res_partner.py`
- **Problema:** Solo el `write()` override establecia la fecha, no el `create()`
- **Fix:** Agregado `@api.model_create_multi` override para manejar create tambien

### Error 10: `_compute_color` sin campo `color` (No critico)
- **Archivo:** `models/calendar_event.py`
- **Problema:** `color` no es un campo del modelo `calendar.event` en Odoo 18
- **Fix:** Metodo `_compute_color` eliminado completamente

## Warnings (No bloqueantes)

- `alert` elements sin `role="alert"` — cosmetic, no afecta funcionalidad
- `<i>` con fa class sin `title` — accesibilidad, no afecta funcionalidad
- `kanban-box` deprecado en favor de `card` template — cosmetic
- `appointment_status` overrides existing selection — viene de otro modulo, no de popstudio

## Pendientes / Mejoras Sugeridas

1. **base_automation_data.xml** — Redisenar para Odoo 18 (modelo `base.automation` fue reestructurado)
2. **Kanban view** — Migrar de `kanban-box` a template `card` (Odoo 18 best practice)
3. **Alertas XML** — Agregar `role="alert"` a todos los `<div class="alert ...">` para accesibilidad
4. **Iconos FA** — Agregar `title=""` a todos los `<i class="fa ...">` para accesibilidad
5. **Test 3.4** — Crear test unitario con usuario no-admin para validar proteccion de `expediente_completado`
6. **mobile_wizard.js** — El template `popstudio_expediente.StepIndicator` referenciado en JS no tiene XML template definido
