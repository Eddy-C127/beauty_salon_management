# Plan de Implementación: 7 Issues Pendientes + Addon Feature

## 📌 Contexto
Tras la investigación del trabajo previo, se identificaron 6 issues estéticos y de configuración en `TEST_RESULTS.md`, más 1 issue crítico (`TypeError` en el código Python). Además, se incorporará la propuesta para el **Addon Feature** de Auditoría de Comisiones relacionado con la validación de expedientes.

---

## 🛠️ Plan de Resolución de los 7 Issues

### Issue 1: `TypeError` Crash en `wizard_concluir_cita.py` (Crítico)
- **Problema:** En la acción `action_confirmar_conclusion` se usa `dict(self._fields['nivel_satisfaccion'].selection).get(...)`. En Odoo 18 esto lanza _TypeError_ porque `selection` puede ser estático o requerir un entorno evaluado.
- **Implementación:** Cambiar a la forma canónica de Odoo 18:
  ```python
  satisfaccion_dict = dict(self._fields['nivel_satisfaccion']._description_selection(self.env))
  'sat': satisfaccion_dict.get(self.nivel_satisfaccion, '')
  ```

### Issue 2: `base_automation_data.xml` en Odoo 18
- **Problema:** El campo `action_server_id` fue retirado/modificado en Odoo 18 en `base.automation`.
- **Implementación:** 
  1. Reescribir el XML para la acción automatizada adaptándose a la nueva estructura de Odoo 18 para acciones basadas en tiempo.
  2. Alternativamente, pasar la funcionalidad de la automatización completamente al cron `ir_cron_data.xml`.

### Issue 3: Migración de `kanban-box` a `card` (UI/UX)
- **Problema:** El template `kanban-box` está deprecado en Odoo 18.
- **Implementación:** Modificar `expediente_sesion_views.xml`.
  - Reemplazar `<t t-name="kanban-box">` por `<t t-name="card">`.
  - Ajustar las clases en el interior de los bloques Kanban al nuevo layout estándar.

### Issue 4: Accesibilidad - `role="alert"`
- **Problema:** Carencia de roles ARIA en alertas en `calendar_event_views.xml`, `wizard_iniciar_cita_views.xml` y `wizard_concluir_cita_views.xml`.
- **Implementación:** Buscar todas las etiquetas `<div class="alert ... ">` y agregar `role="alert"`.

### Issue 5: Accesibilidad - Títulos en Iconos Font Awesome
- **Problema:** Etiquetas `<i>` de iconos FontAwesome en vistas no poseen atributos `title`, lanzando warnings en los tests de Odoo.
- **Implementación:** Agregar `title="Label"` y `aria-label="Label"` en todos los `<i class="fa..."/>`.

### Issue 6: Componente JS sin template XML
- **Problema:** En `mobile_wizard.js`, la clase `PopStudioStepIndicator` asume un owl template `beauty_salon_file_management.StepIndicator` que no existe.
- **Implementación:** 
  1. Crear un archivo en `static/src/xml/mobile_wizard_templates.xml`.
  2. Definir `<t t-name="beauty_salon_file_management.StepIndicator">`.
  3. Declararlo en el `__manifest__.py` dentro de `web.assets_backend`.

### Issue 7: Unit Test de Seguridad
- **Problema:** Falta validar exhaustivamente la protección de `expediente_completado` con roles.
- **Implementación:**
  1. Añadir archivo `tests/test_expediente_security.py`.
  2. Usar `self.env['calendar.event'].with_user(non_admin_user).write({'expediente_completado': True})` y hacer assert de `ValidationError` y `AccessError`.

---

## 🚀 Addon Feature: Dashboard Interactivo de Auditoría de Comisiones

El requerimiento base contemplaba implementar un "sistema automatizado de auditoría para comisiones". Actualmente sólo existen filtros, graficos y un Pivot basico. 

### Implementación del Addon:
1. **Nuevo Tablero OWL (Dashboard)**: Crear un dashboard en Owl que muestre:
   - Tasa de cumplimiento de expedientes por artista (% expedientes completos vs incompletos).
   - "Wall of Shame": Lista en vivo de las últimas 5 citas concluidas sin revisión.
   - Acciones de un solo clic para mandar "Ping" (`message_post` recordatorio) al artista.
2. **Bloqueo Automático de Comisiones**: Interceptar la creación de líneas de comisión en los addons existentes (mediante herencia a `beauty_salon_sale_commission` o `sale.order.line`) para que:
   - **Lógica**: Si un servicio en la caja registradora proviene de una cita con `expediente_completado = False`, la comisión se calcule en % inferior o no se libere hasta que el State del Expediente pase a "Completada".

---
> **Estado:** Listo para desarrollo. Los _Todos_ han sido actualizados centralizadamente en este documento.
