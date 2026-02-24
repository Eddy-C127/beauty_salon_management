# 🤖 CLAUDE CODE — Tareas Delegadas: `popstudio_expediente`

**Módulo:** `popstudio_expediente` — Expediente Clínico Pop Studio  
**Odoo version:** 18.0  
**Fecha:** 2026-02-23  
**Entorno:** Docker — contenedor `odoo18_dev` en `localhost:8069`  
**Path local:** `/home/eduardo/odoo18-dev/addons/custom_addons/popstudio_expediente/`  
**Path en contenedor:** `/mnt/custom-addons/popstudio_expediente/`

---

## 🔧 CONTEXTO DEL ENTORNO

```bash
# Comandos útiles de entorno
docker exec odoo18_dev bash                              # Entrar al contenedor
docker exec odoo18_dev odoo shell -d <DB_NAME>          # Shell ORM de Odoo
docker logs odoo18_dev --tail 50                        # Ver logs recientes

# Conexión directa a PostgreSQL
docker exec postgres_odoo18 psql -U odoo -d <DB_NAME>

# Reiniciar Odoo (para refrescar módulos)
docker restart odoo18_dev
```

> **Nota:** Reemplaza `<DB_NAME>` con el nombre real de la base de datos.  
> Para encontrarlo: `docker exec postgres_odoo18 psql -U odoo -c "\l"`

---

## 📋 TAREA 0 — Identificar la Base de Datos Activa

```bash
# Listar todas las bases de datos disponibles
docker exec postgres_odoo18 psql -U odoo -c "\l"

# Verificar qué DB tiene los módulos de Odoo instalados
docker exec postgres_odoo18 psql -U odoo -d <DB_NAME> -c \
  "SELECT name, state FROM ir_module_module WHERE name LIKE '%beauty%' OR name LIKE '%pop%' LIMIT 20;"
```

**Entregable:** Confirmar el `DB_NAME` correcto para todas las tareas siguientes.

---

## 📋 TAREA 1 — Instalar/Actualizar el Módulo vía CLI

### 1.1 Primera instalación

```bash
# Instalar el módulo (primera vez)
docker exec odoo18_dev odoo -d <DB_NAME> -i popstudio_expediente \
  --stop-after-init --no-http 2>&1 | tail -50
```

### 1.2 Actualizar módulo (si ya existe)

```bash
# Actualizar el módulo
docker exec odoo18_dev odoo -d <DB_NAME> -u popstudio_expediente \
  --stop-after-init --no-http 2>&1 | tail -50
```

### 1.3 Verificar instalación exitosa

```bash
docker exec postgres_odoo18 psql -U odoo -d <DB_NAME> -c \
  "SELECT name, state, latest_version FROM ir_module_module WHERE name = 'popstudio_expediente';"
```

**✅ Resultado esperado:** `state = installed`, `latest_version = 18.0.1.0.0`

### 1.4 Si hay errores en la instalación

Revisar el log completo:
```bash
docker logs odoo18_dev 2>&1 | grep -A 20 "ERROR\|Traceback\|popstudio"
```

**Corregir errores encontrados antes de continuar.** Los errores más comunes a revisar:
- Campos `Many2one` con referencias incorrectas
- XML con `ref` a IDs que no existen
- Dependencias faltantes en `__manifest__.py`

---

## 📋 TAREA 2 — Tests de Modelos vía Base de Datos

### 2.1 Verificar que las tablas se crearon correctamente

```sql
-- Conectar: docker exec postgres_odoo18 psql -U odoo -d <DB_NAME>

-- Verificar tabla principal de sesiones
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'popstudio_expediente_sesion'
ORDER BY ordinal_position;
```

**✅ Esperado:** Debe mostrar columnas: `id`, `partner_id`, `calendar_event_id`, `artista_id`, `fecha_sesion`, `foto_antes`, `foto_despues`, `notas_internas`, `nivel_satisfaccion`, `consentimiento_aceptado`, `firma_consentimiento`, `state`, etc.

### 2.2 Verificar campos extendidos en `res_partner`

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'res_partner'
  AND column_name IN (
    'alergias', 'tipo_piel', 'condiciones_medicas',
    'medicamentos_actuales', 'aviso_privacidad_aceptado',
    'aviso_privacidad_fecha', 'proxima_visita_recomendada',
    'notas_privadas_expediente'
  );
```

**✅ Esperado:** Todos los campos deben aparecer.

### 2.3 Verificar campos extendidos en `calendar_event`

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'calendar_event'
  AND column_name IN (
    'expediente_completado', 'popstudio_state', 'artista_id',
    'servicio_nombre', 'inicio_real', 'fin_real',
    'duracion_real_minutos', 'sesion_id'
  );
```

**✅ Esperado:** Todos los campos deben aparecer.

### 2.4 Verificar grupos de seguridad

```sql
SELECT g.name, g.full_name
FROM res_groups g
JOIN ir_module_category c ON g.category_id = c.id
WHERE c.name = 'Pop Studio';
```

**✅ Esperado:** 3 grupos: `Recepcionista`, `Artista / Estilista`, `Manager / Coordinador`

---

## 📋 TAREA 3 — Tests Funcionales vía Odoo Shell ORM

Todos los tests se ejecutan mediante el shell de Odoo. Iniciar con:

```bash
docker exec -it odoo18_dev odoo shell -d <DB_NAME> --no-http
```

### 3.1 TEST: Crear Clienta con Expediente

```python
# En el shell de Odoo:

# Crear partner de prueba con datos médicos
partner = env['res.partner'].create({
    'name': 'Prueba Clienta Test',
    'mobile': '+5255000000001',
    'email': 'test@popstudio.mx',
    'tipo_piel': 'sensible',
    'alergias': 'Látex, Parabenos, Tinte amoniacal',
    'condiciones_medicas': 'Sin condiciones médicas conocidas',
    'aviso_privacidad_aceptado': True,
})
env.cr.commit()

print(f"✅ Partner creado: ID={partner.id}, Name={partner.name}")
print(f"   Aviso: {partner.aviso_privacidad_aceptado}")
print(f"   Fecha aviso: {partner.aviso_privacidad_fecha}")
print(f"   Tipo piel: {partner.tipo_piel}")
print(f"   Sesiones: {partner.sesion_count}")
```

**✅ Esperado:** Partner creado, `aviso_privacidad_fecha` auto-populated.

### 3.2 TEST: Crear Sesión Manualmente

```python
# Usar el partner creado en 3.1 o buscar uno existente
partner = env['res.partner'].search([('name', '=', 'Prueba Clienta Test')], limit=1)

sesion = env['popstudio.expediente.sesion'].create({
    'partner_id': partner.id,
    'fecha_sesion': fields.Datetime.now(),
    'servicio_realizado': 'Tinte + Hidratación',
    'notas_internas': '<p>Prueba de sesión creada desde shell.</p>',
    'nivel_satisfaccion': '5',
    'state': 'en_curso',
    'artista_id': env.user.id,
})
env.cr.commit()

print(f"✅ Sesión creada: ID={sesion.id}")
print(f"   Display name: {sesion.display_name}")
print(f"   Estado: {sesion.state}")
print(f"   Partner: {sesion.partner_id.name}")
```

**✅ Esperado:** Sesión creada, `display_name` = "Prueba Clienta Test - DD/MM/YYYY"

### 3.3 TEST: Validación de Foto Obligatoria (Debe fallar sin foto)

```python
# Test: intentar marcar como completada SIN foto_despues
# Debe lanzar ValidationError
from odoo.exceptions import ValidationError

partner = env['res.partner'].search([('name', '=', 'Prueba Clienta Test')], limit=1)
sesion = env['popstudio.expediente.sesion'].search([('partner_id', '=', partner.id)], limit=1)

try:
    sesion.write({'state': 'completada'})
    env.cr.commit()
    print("❌ ERROR: Debería haber lanzado ValidationError pero no lo hizo")
except ValidationError as e:
    env.cr.rollback()
    print(f"✅ ValidationError correcto: {e.args[0][:80]}...")
```

**✅ Esperado:** Debe imprimir `ValidationError correcto`.

### 3.4 TEST: Protección de `expediente_completado` (solo sistema puede modificar)

```python
# Buscar o crear una cita de prueba
from odoo.exceptions import ValidationError

events = env['calendar.event'].search([], limit=1)
if not events:
    print("⚠️ No hay citas de calendario. Crear una primero.")
else:
    event = events[0]
    try:
        # Intentar modificar directamente (sin sudo) - debe fallar
        event.write({'expediente_completado': True})
        env.cr.commit()
        print("❌ ERROR: Debería haber lanzado ValidationError")
    except ValidationError as e:
        env.cr.rollback()
        print(f"✅ Protección OK: {e.args[0][:80]}...")

    # Verificar que SÍ puede hacerse con sudo
    try:
        event.sudo().write({'expediente_completado': False})
        env.cr.commit()
        print("✅ sudo().write() funciona correctamente")
    except Exception as e:
        env.cr.rollback()
        print(f"❌ ERROR inesperado con sudo: {e}")
```

**✅ Esperado:** Sin sudo → ValidationError; Con sudo → éxito.

### 3.5 TEST: LFPDPPP — Alergias sin Aviso de Privacidad (debe fallar)

```python
from odoo.exceptions import ValidationError

try:
    partner_sin_aviso = env['res.partner'].create({
        'name': 'Test Sin Aviso Privacidad',
        'alergias': 'Prueba de alergia sin aviso',
        'aviso_privacidad_aceptado': False,
    })
    env.cr.commit()
    print("❌ ERROR: Debería haber lanzado ValidationError por LFPDPPP")
except ValidationError as e:
    env.cr.rollback()
    print(f"✅ Cumplimiento LFPDPPP OK: {e.args[0][:80]}...")
```

**✅ Esperado:** ValidationError mencionando LFPDPPP.

### 3.6 TEST: Flujo Completo Wizard Iniciar → Concluir (simulado en ORM)

```python
import base64

# Crear imagen dummy (1x1 pixel blanco)
img_data = base64.b64encode(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f'
    b'\x00\x00\x11\x00\x01\x1e\xb3`\r\x00\x00\x00\x00IEND\xaeB`\x82'
).decode()

partner = env['res.partner'].search([('name', '=', 'Prueba Clienta Test')], limit=1)

# --- PASO 1: Iniciar Cita (crear sesión) ---
sesion = env['popstudio.expediente.sesion'].create({
    'partner_id': partner.id,
    'fecha_sesion': fields.Datetime.now(),
    'foto_antes': img_data,
    'servicio_realizado': 'Keratina Premium',
    'firma_consentimiento': img_data,
    'firma_consentimiento_fecha': fields.Datetime.now(),
    'consentimiento_aceptado': True,
    'state': 'en_curso',
    'artista_id': env.user.id,
})
env.cr.commit()
print(f"✅ PASO 1 OK — Sesión iniciada: {sesion.id} | Estado: {sesion.state}")

# --- PASO 2: Concluir Cita ---
sesion.sudo().write({
    'foto_despues': img_data,
    'notas_internas': '<p>Keratina aplicada correctamente. Tiempo: 45 min.</p>',
    'recomendaciones_cuidado': '<p>No lavar en 48 horas.</p>',
    'productos_usados': 'Keratina Brazilian Blowout, Neutralizante',
    'nivel_satisfaccion': '5',
    'state': 'completada',
})
env.cr.commit()
print(f"✅ PASO 2 OK — Sesión completada | Estado: {sesion.state}")

# Verificar contador de sesiones en partner
print(f"   Sesiones del partner: {partner.sesion_count}")
print(f"   Última sesión: {partner.ultima_sesion_fecha}")
```

**✅ Esperado:** Sesión va de `en_curso` → `completada`, contadores actualizados.

### 3.7 TEST: Cron Job de Alertas (ejecución manual)

```python
# Ejecutar el cron manualmente para verificar que no da error
result = env['calendar.event']._enviar_alerta_expediente_incompleto()
env.cr.commit()
print(f"✅ Cron ejecutado sin errores: resultado = {result}")
```

**✅ Esperado:** Retorna `True` sin excepciones.

---

## 📋 TAREA 4 — Verificación de Vistas XML vía Base de Datos

### 4.1 Verificar que las vistas se registraron

```sql
-- Verificar todas las vistas del módulo
SELECT name, model, type, active
FROM ir_ui_view
WHERE module = 'popstudio_expediente'
ORDER BY model, type;
```

**✅ Esperado:** Mínimo 10 vistas registradas (form, list, kanban, search para los 3 modelos + wizards + auditoría).

### 4.2 Verificar menús

```sql
SELECT name, complete_name, action
FROM ir_ui_menu
WHERE complete_name LIKE '%Pop Studio%' OR complete_name LIKE '%Expediente%'
ORDER BY complete_name;
```

**✅ Esperado:** Al menos 6 entradas de menú (Citas, Expedientes, Auditoría y sus submenús).

### 4.3 Verificar acciones

```sql
SELECT name, res_model, view_mode
FROM ir_act_window
WHERE res_model IN (
    'popstudio.expediente.sesion',
    'popstudio.wizard.iniciar.cita',
    'popstudio.wizard.concluir.cita'
)
ORDER BY name;
```

**✅ Esperado:** Al menos 3 acciones (una por modelo).

### 4.4 Verificar Cron registrado

```sql
SELECT name, model_id, state, active, interval_number, interval_type
FROM ir_cron
WHERE name LIKE '%Pop Studio%';
```

**✅ Esperado:** `Pop Studio: Alerta de Expedientes Incompletos`, `active = true`, `interval_type = hours`.

### 4.5 Verificar Assets CSS/JS

```sql
SELECT name, url
FROM ir_asset
WHERE bundle LIKE '%backend%' AND (url LIKE '%popstudio%')
ORDER BY name;
```

**✅ Esperado:** 2 assets: `popstudio_mobile.css` y `mobile_wizard.js`.

---

## 📋 TAREA 5 — Correcciones y Fixes Pendientes

### 5.1 FIX: Verificar compatibilidad de `_compute_color` en `calendar.event`

El modelo `calendar.event` en Odoo 18 puede no tener el método `_compute_color` heredable. Verificar:

```python
# En el shell de Odoo:
CalendarEvent = env['calendar.event']
print(hasattr(CalendarEvent, '_compute_color'))
print(type(CalendarEvent).mro()[:5])
```

**Si `_compute_color` no existe** en el padre, remover la llamada `super()` en el método.  
Editar `/home/eduardo/odoo18-dev/addons/custom_addons/popstudio_expediente/models/calendar_event.py`:

```python
# ANTES:
@api.depends('expediente_completado', 'popstudio_state', 'start')
def _compute_color(self):
    super()._compute_color() if hasattr(super(), '_compute_color') else None

# DESPUÉS (si _compute_color no existe en padre):
# Remover completamente el método o dejarlo vacío y marcar color directamente
```

### 5.2 FIX: Verificar `partner_cliente_id` computed no causa error en buscar

El campo compute de `partner_cliente_id` usa `has_group()` que puede ser lento. Verificar:

```python
# En el shell:
events = env['calendar.event'].search([], limit=5)
for e in events:
    try:
        _ = e.partner_cliente_id
        print(f"✅ Event {e.id}: partner_cliente = {e.partner_cliente_id.name or 'None'}")
    except Exception as ex:
        print(f"❌ Event {e.id}: ERROR - {ex}")
```

**Si hay errores**, simplificar el `_compute_partner_cliente` quitando el filtro de `has_group`.

### 5.3 FIX: wizard_iniciar_cita — campo `servicio_nombre` no almacenado

El campo `servicio_nombre` en el wizard es `compute` con `store=False`. Verificar que funcione en la vista:

```python
wizard = env['popstudio.wizard.iniciar.cita'].create({
    'calendar_event_id': env['calendar.event'].search([], limit=1).id,
    'partner_id': env['res.partner'].search([], limit=1).id,
})
print(f"Servicio nombre: '{wizard.servicio_nombre}'")
print(f"Alergias display: '{wizard.alergias_display}'")
```

### 5.4 FIX: base_automation_data.xml — `action_server_id` requerido

El archivo `data/base_automation_data.xml` tiene `action_server_id = False` lo cual puede causar error de validación en Odoo 18. 

**Verificar en DB:**
```sql
SELECT name, active FROM base_automation WHERE name LIKE '%Pop Studio%';
```

**Si hay error**, editar el XML para dar una acción válida o eliminar el registro y crearlo solo con código Python.

**Alternativa:** Remover el archivo `base_automation_data.xml` del manifest si causa errores de instalación:

```python
# En __manifest__.py, quitar la línea:
# 'data/base_automation_data.xml',
```

### 5.5 FIX: CSV de acceso — corregir comentarios

El archivo `security/ir.model.access.csv` tiene líneas de comentario con `#`. Verificar que Odoo 18 los acepte. Si no:

```bash
# Verificar el CSV es válido
docker exec postgres_odoo18 psql -U odoo -d <DB_NAME> -c \
  "SELECT name FROM ir_model_access WHERE name LIKE '%expediente%' OR name LIKE '%wizard%';"
```

**Si faltan registros**, editar el CSV eliminando las líneas de comentario (`# ── ...`).

---

## 📋 TAREA 6 — Tests de Regresión Post-Fix

Después de aplicar todos los fixes, ejecutar en secuencia:

```bash
# Re-actualizar el módulo
docker exec odoo18_dev odoo -d <DB_NAME> -u popstudio_expediente \
  --stop-after-init --no-http 2>&1 | grep -E "INFO|WARNING|ERROR|Traceback" | tail -30

# Verificar estado final
docker exec postgres_odoo18 psql -U odoo -d <DB_NAME> -c \
  "SELECT name, state, latest_version FROM ir_module_module WHERE name = 'popstudio_expediente';"
```

**Luego ejecutar nuevamente los tests 3.1 → 3.7** y confirmar que todos pasan.

---

## 📋 TAREA 7 — Reporte Final

Crear un archivo `TEST_RESULTS.md` en el mismo directorio con:

```markdown
# Resultados de Tests — popstudio_expediente

Fecha: [fecha]
DB: [nombre de DB]
Versión módulo: 18.0.1.0.0

## Resumen
| Test | Estado | Notas |
|------|--------|-------|
| 1.1 Instalación | ✅/❌ | ... |
| 2.1 Tablas creadas | ✅/❌ | ... |
| 2.2 Campos partner | ✅/❌ | ... |
| 2.3 Campos calendar | ✅/❌ | ... |
| 2.4 Grupos seguridad | ✅/❌ | ... |
| 3.1 Crear clienta | ✅/❌ | ... |
| 3.2 Crear sesión | ✅/❌ | ... |
| 3.3 Foto obligatoria | ✅/❌ | ... |
| 3.4 Protección campo | ✅/❌ | ... |
| 3.5 LFPDPPP | ✅/❌ | ... |
| 3.6 Flujo completo | ✅/❌ | ... |
| 3.7 Cron alertas | ✅/❌ | ... |
| 4.1 Vistas XML | ✅/❌ | ... |
| 4.4 Cron registrado | ✅/❌ | ... |

## Errores Encontrados y Corregidos
[Lista de bugs y sus fixes aplicados]

## Pendientes
[Lista de mejoras sugeridas o issues menores]
```

---

## 🚫 RESTRICCIONES IMPORTANTES

1. **NO usar el navegador web** para ningún test. Todo por shell o psql.
2. **NO modificar datos de producción.** Solo trabajar en la DB de desarrollo.
3. **NO borrar ni reinstalar módulos** que no sean `popstudio_expediente`.
4. **SÍ usar `env.cr.rollback()`** después de cada test que falle para no corromper datos.
5. **Commitear cambios de código** al terminar con un mensaje descriptivo.

---

## ✅ DEFINICIÓN DE DONE

El módulo está listo cuando:
- [ ] La instalación en Odoo 18 es limpia (0 errores en log)
- [ ] Todas las tablas y columnas existen en PostgreSQL
- [ ] Tests 3.1 → 3.7 pasan sin errores
- [ ] Vistas XML están registradas (Tarea 4)
- [ ] El archivo `TEST_RESULTS.md` está generado con todos los tests en ✅
- [ ] No hay excepciones en `docker logs odoo18_dev` relacionadas con `popstudio`
