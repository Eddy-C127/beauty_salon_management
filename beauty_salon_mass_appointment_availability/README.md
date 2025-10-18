# Gestión de Disponibilidad de Citas

## 📋 Descripción

Módulo para Odoo 18 Enterprise que permite gestionar la disponibilidad de citas de forma masiva, facilitando cerrar y abrir períodos de agenda para múltiples tipos de cita simultáneamente usando la lógica nativa de Odoo.

## ✨ Características

### Acciones Disponibles

1. **Cerrar Disponibilidad**
   - Bloquea las citas en un período específico
   - Define fechas de inicio y fin
   - Especifica motivo del cierre
   - Clientes NO pueden agendar durante el período

2. **Abrir Disponibilidad**
   - Restaura la disponibilidad normal de citas
   - Dos opciones nativas:
     - **Disponible Ahora**: Configurar días en el futuro
     - **Intervalo de Fechas**: Definir período específico de disponibilidad
   - Clientes PUEDEN agendar según configuración

### Modos de Selección

1. **Modo Masivo**
   - Selección automática por:
     - Sucursal (stock.warehouse)
     - Categoría de servicio (Pestañas, Cejas, Tattoo Lips, Tattoo Brows)
   - Aplica cambios a todos los appointment.type que coincidan

2. **Modo Individual**
   - Selección manual de appointment.type específicos
   - Control total sobre qué tipos de cita se modifican

### Funcionalidades Adicionales

- ✅ Campo de **categoría de servicio** en appointment.type
- ✅ Campo **Estado de Disponibilidad** visible (computado)
- ✅ Registro de **todos los cambios en el chatter**
- ✅ **Validaciones** completas (fechas, campos requeridos)
- ✅ **Contador en tiempo real** de tipos afectados
- ✅ **Mensajes detallados** de confirmación
- ✅ **Filtros y agrupaciones** por categoría y estado
- ✅ Acceso desde **múltiples vistas**: Calendar, Gantt, List, Appointment Type

## 🏗️ Arquitectura Técnica

### Usa Campos Nativos de Odoo

El módulo NO crea registros adicionales. En su lugar, usa los campos nativos de `appointment.type`:

```python
# Para CERRAR disponibilidad:
appointment.type.write({
    'category_time_display': 'punctual_fields',  # Campo nativo
    'start_datetime': fecha_inicio,              # Campo nativo
    'end_datetime': fecha_fin,                   # Campo nativo
})

# Para ABRIR disponibilidad (ilimitada):
appointment.type.write({
    'category_time_display': 'recurring_fields',  # Campo nativo
    'start_datetime': False,
    'end_datetime': False,
})

# Para ABRIR con intervalo personalizado:
appointment.type.write({
    'category_time_display': 'punctual_fields',
    'start_datetime': fecha_inicio_disponibilidad,
    'end_datetime': fecha_fin_disponibilidad,
})
```

### Ventajas de Este Enfoque

| Aspecto | Beneficio |
|---------|-----------|
| **Simplicidad** | Usa lógica nativa de Odoo |
| **Reversibilidad** | Cambio en 2 clicks |
| **Sin registros extra** | Solo actualiza campos existentes |
| **Auditoría** | Todo registrado en chatter |
| **Mantenimiento** | Código mínimo, máxima eficiencia |

## 🚀 Instalación

### 1. Requisitos Previos

Asegúrate de tener instalados estos módulos:
- ✅ `appointment` - Módulo de Citas
- ✅ `calendar` - Módulo de Calendario
- ✅ `stock` - Para sucursales (stock.warehouse)

### 2. Instalación del Módulo

```bash
# Copiar módulo a addons
cp -r mass_appointment_availability /ruta/odoo/addons/

# Reiniciar Odoo
sudo systemctl restart odoo

# O con docker
docker-compose restart odoo
```

### 3. Activar en Odoo

1. Ir a **Apps**
2. Actualizar Lista de Aplicaciones
3. Buscar "Gestión de Disponibilidad de Citas"
4. Hacer clic en **Instalar**

## 📖 Guía de Uso

### Caso de Uso 1: Cerrar Diciembre por Vacaciones

#### Objetivo
Cerrar la agenda de todos los servicios de Pestañas en la sucursal Cumbres durante diciembre.

#### Pasos

1. **Acceder al Wizard**
   - Ir a **Calendar** → Vista Calendar/Gantt/List
   - Hacer clic en botón **"Gestión de Agenda"**

2. **Configurar el Cierre**
   - **Acción**: Cerrar Disponibilidad
   - **Modo**: Masivo (por Sucursal/Categoría)
   - **Sucursal**: Cumbres
   - **Categoría**: Pestañas
   - **Desde**: 2025-12-01 00:00:00
   - **Hasta**: 2025-12-31 23:59:59
   - **Motivo**: "Vacaciones de fin de año"

3. **Aplicar**
   - Click en **"Aplicar Cambios"**
   - Ver confirmación con tipos de cita afectados

#### Resultado
- ✅ Todos los appointment.type de Pestañas en Cumbres quedan cerrados
- ✅ Clientes NO pueden agendar en diciembre
- ✅ Campo "Estado de Disponibilidad" muestra: "🔒 CERRADA del 01/12/2025 al 31/12/2025"
- ✅ Registro en chatter de cada appointment.type

---

### Caso de Uso 2: Reabrir Agenda de Diciembre

#### Objetivo
A mediados de noviembre, decides reabrir la agenda para diciembre.

#### Pasos

1. **Acceder al Wizard**
   - Desde Calendar o Appointment Types
   - Click en **"Gestión de Agenda"**

2. **Configurar la Apertura**
   - **Acción**: Abrir Disponibilidad
   - **Modo**: Masivo (por Sucursal/Categoría)
   - **Sucursal**: Cumbres
   - **Categoría**: Pestañas
   - **Modo de Apertura**: Disponible Ahora
   - **Días en el Futuro**: 60
   - **Nota**: "Reapertura de agenda para diciembre"

3. **Aplicar**
   - Click en **"Aplicar Cambios"**

#### Resultado
- ✅ Disponibilidad restaurada a configuración normal
- ✅ Clientes PUEDEN agendar nuevamente
- ✅ Estado muestra: "✅ ABIERTA - X horario(s) configurado(s)"
- ✅ Cambio registrado en chatter

---

### Caso de Uso 3: Abrir Solo un Período Específico

#### Objetivo
Abrir disponibilidad solo del 15 al 30 de diciembre (promoción especial).

#### Pasos

1. **Acceder al Wizard**
2. **Configurar**
   - **Acción**: Abrir Disponibilidad
   - **Modo**: Masivo
   - **Sucursal**: Cumbres
   - **Categoría**: Pestañas
   - **Modo de Apertura**: Dentro de un Intervalo de Fechas
   - **Disponible Desde**: 2025-12-15 08:00:00
   - **Disponible Hasta**: 2025-12-30 20:00:00
   - **Nota**: "Promoción navideña"

3. **Aplicar**

#### Resultado
- ✅ Citas disponibles solo del 15 al 30 de diciembre
- ✅ Fuera de ese período: NO disponible
- ✅ Perfecto para promociones temporales

---

## 🎨 Interfaz de Usuario

### Campos Visibles en Appointment Type

#### Vista de Formulario
```
Tipo de Cita: Diseño de Pestañas
Categoría de Cita: [Pestañas ▼]
Estado de Disponibilidad: ✅ ABIERTA - 5 horario(s) configurado(s)
```

#### Vista de Lista
| Nombre | Categoría | Estado de Disponibilidad |
|--------|-----------|--------------------------|
| Diseño Pestañas | Pestañas | ✅ ABIERTA |
| Microblading | Cejas | 🔒 CERRADA 01/12 - 31/12 |

### Botón "Gestión de Agenda"

Disponible en:
- ✅ Vista Calendar de calendar.event (header)
- ✅ Vista Gantt de calendar.event (header)
- ✅ Vista List de calendar.event (header)
- ✅ Vista Form de appointment.type (header)

### Wizard - Interfaz

```
┌─────────────────────────────────────────┐
│ Gestión de Disponibilidad de Citas      │
├─────────────────────────────────────────┤
│ Configuración                           │
│ ◉ Cerrar Disponibilidad                │
│ ○ Abrir Disponibilidad                 │
│                                         │
│ ◉ Masivo (por Sucursal/Categoría)     │
│ ○ Individual (por Tipo de Cita)       │
│                                         │
│ Tipos de Cita Afectados: 12            │
├─────────────────────────────────────────┤
│ Criterios de Selección Masiva          │
│ Sucursal: [Cumbres ▼]                  │
│ Categoría: [Pestañas ▼]                │
├─────────────────────────────────────────┤
│ Configuración de Cierre                │
│ Desde: [01/12/2025 00:00] → Hasta: [31/12/2025 23:59] │
│ Motivo: [Vacaciones de fin de año]     │
├─────────────────────────────────────────┤
│ [Aplicar Cambios]  [Cancelar]          │
└─────────────────────────────────────────┘
```

## 🔍 Filtros y Búsquedas

### En Appointment Types

**Filtros Disponibles:**
- 🟢 Disponibles
- 🔴 Cerradas
- 📁 Pestañas
- 📁 Cejas
- 📁 Tattoo Lips
- 📁 Tattoo Brows

**Agrupaciones:**
- Por Categoría
- Por Estado de Disponibilidad
- Por Sucursal

**Búsqueda:**
- Por nombre de tipo de cita
- Por categoría
- Por estado de disponibilidad

## 🔐 Seguridad y Permisos

### Grupos de Acceso

| Grupo | Permisos |
|-------|----------|
| **Appointment Manager** | ✅ Crear, Leer, Escribir, Eliminar |
| **Usuarios Base** | ✅ Solo Lectura |

### Restricciones

- Solo usuarios del grupo `appointment.group_appointment_manager` pueden:
  - Ver el botón "Gestión de Agenda"
  - Ejecutar el wizard
  - Modificar disponibilidad de citas

## 📊 Auditoría y Trazabilidad

### Registro en Chatter

Cada cambio se registra en el chatter del appointment.type:

#### Ejemplo: Cierre
```
🔒 Disponibilidad Cerrada
• Período: 01/12/2025 00:00 - 31/12/2025 23:59
• Motivo: Vacaciones de fin de año
• Estado: Las citas están bloqueadas en este período
```

#### Ejemplo: Apertura
```
✅ Disponibilidad Abierta
• Estado: Las citas están disponibles según configuración normal
• Nota: Reapertura de agenda para diciembre
```

### Logs del Sistema

Todos los cambios también se registran en los logs de Odoo:

```python
_logger.info(
    f'Disponibilidad cerrada para Diseño de Pestañas '
    f'desde 2025-12-01 hasta 2025-12-31'
)
```

## 🛠️ Configuración Técnica

### Modelos Modificados

#### `appointment.type`

**Nuevos campos:**
```python
appointment_category = fields.Selection([
    ('pestanas', 'Pestañas'),
    ('cejas', 'Cejas'),
    ('tattoo_lips', 'Tattoo Lips'),
    ('tattoo_brows', 'Tattoo Brows'),
], tracking=True)

availability_status = fields.Text(
    compute='_compute_availability_status',
    store=True
)
```

**Nuevo método:**
```python
def log_availability_change(self, action_type, date_from=None, date_to=None, reason=None):
    """Registra cambios en el chatter"""
```

### Modelo Wizard

**Modelo:** `mass.availability.wizard` (TransientModel)

**Campos principales:**
- `action_type`: Selection (close/open)
- `selection_mode`: Selection (mass/individual)
- `branch_id`: Many2one a stock.warehouse
- `appointment_category`: Selection
- `appointment_type_ids`: Many2many a appointment.type
- Campos de fechas para cerrar/abrir
- Campos de configuración de apertura

**Método principal:**
```python
def action_apply_availability_change(self):
    """Aplica cambios de disponibilidad"""
```

### Vistas Heredadas

1. **appointment.type**
   - Form: Agrega categoría, estado, botón
   - Tree: Agrega columnas de categoría y estado
   - Search: Agrega filtros y agrupaciones

2. **calendar.event**
   - Calendar: Agrega botón en header
   - Gantt: Agrega botón en header
   - Tree: Agrega botón en header

## 🔧 Personalización

### Agregar Nuevas Categorías

Editar `models/appointment_type.py` y `models/mass_availability_wizard.py`:

```python
appointment_category = fields.Selection(
    selection=[
        ('pestanas', 'Pestañas'),
        ('cejas', 'Cejas'),
        ('tattoo_lips', 'Tattoo Lips'),
        ('tattoo_brows', 'Tattoo Brows'),
        ('nueva_categoria', 'Nueva Categoría'),  # ← AGREGAR AQUÍ
    ],
    ...
)
```

Luego actualizar los filtros en `views/appointment_type_views.xml`:

```xml
<filter string="Nueva Categoría" 
        name="filter_nueva_categoria" 
        domain="[('appointment_category', '=', 'nueva_categoria')]"/>
```

### Cambiar Grupos de Acceso

Editar `security/ir.model.access.csv`:

```csv
access_mass_availability_wizard_custom,mass.availability.wizard custom,model_mass_availability_wizard,tu_grupo_custom,1,1,1,1
```

## 🐛 Troubleshooting

### El botón no aparece en las vistas

**Síntoma:** No veo el botón "Gestión de Agenda"

**Causas posibles:**
1. Usuario no tiene permisos de Appointment Manager
2. Las vistas no se heredaron correctamente

**Solución:**
```bash
# Actualizar el módulo
odoo-bin -u mass_appointment_availability -d tu_database

# Verificar permisos del usuario
# Settings > Users > Tu Usuario > Application Accesses
# Debe tener "Appointment / Manager"
```

### No se encuentran appointment types en modo masivo

**Síntoma:** Mensaje "No se encontraron tipos de cita"

**Causas:**
1. No existen appointment.type con la combinación sucursal + categoría
2. Los appointment.type no tienen asignado `branch_id`
3. Los appointment.type no tienen asignado `appointment_category`

**Solución:**
1. Ir a Appointment Types
2. Verificar que tienen `branch_id` configurado
3. Configurar `appointment_category` para cada tipo
4. Volver a ejecutar el wizard

### Los cambios no se aplican

**Síntoma:** El wizard se ejecuta pero no cambia la disponibilidad

**Verificar:**
1. Revisar logs de Odoo: `tail -f /var/log/odoo/odoo.log`
2. Verificar que los appointment.type tienen permisos de escritura
3. Comprobar que no hay reglas de registro que bloqueen la modificación

**Solución:**
```python
# Ver en logs si hay errores:
_logger.error(f'Error al cerrar disponibilidad para {apt_type.name}: {str(e)}')
```

### El estado de disponibilidad no se muestra correctamente

**Síntoma:** El campo `availability_status` está vacío o desactualizado

**Solución:**
```python
# Recalcular el campo computado
appointment_types = env['appointment.type'].search([])
appointment_types._compute_availability_status()
```

## 📈 Casos de Uso Avanzados

### 1. Cierre Selectivo por Servicio

**Escenario:** Cerrar solo servicios de Tattoo Brows en TODAS las sucursales

**Solución:**
- Usar modo **Individual**
- Buscar todos los appointment.type de categoría "Tattoo Brows"
- Seleccionarlos manualmente
- Aplicar cierre

### 2. Gestión de Promociones Temporales

**Escenario:** Abrir disponibilidad solo durante Black Friday (24-30 Nov)

**Pasos:**
1. Acción: Abrir Disponibilidad
2. Modo de Apertura: Dentro de un Intervalo de Fechas
3. Desde: 2025-11-24 08:00
4. Hasta: 2025-11-30 23:00
5. Nota: "Promoción Black Friday"

### 3. Cierre de Emergencia

**Escenario:** Cerrar TODAS las citas de una sucursal por mantenimiento urgente

**Pasos:**
1. Ejecutar el wizard 4 veces (una por cada categoría)
2. O crear un script Python:

```python
# Script de cierre de emergencia
branch = env['stock.warehouse'].browse(branch_id)
categories = ['pestanas', 'cejas', 'tattoo_lips', 'tattoo_brows']

for category in categories:
    wizard = env['mass.availability.wizard'].create({
        'action_type': 'close',
        'selection_mode': 'mass',
        'branch_id': branch.id,
        'appointment_category': category,
        'date_from': datetime.now(),
        'date_to': datetime.now() + timedelta(days=1),
        'close_reason': 'Mantenimiento de emergencia',
    })
    wizard.action_apply_availability_change()
```

## 🔄 Flujo Técnico Completo

### Cerrar Disponibilidad

```
Usuario hace click en "Gestión de Agenda"
    ↓
Se abre wizard (mass.availability.wizard)
    ↓
Usuario configura:
  - Acción: Cerrar
  - Modo: Masivo
  - Sucursal + Categoría
  - Fechas + Motivo
    ↓
Click "Aplicar Cambios"
    ↓
_get_appointment_types_for_mass_mode()
  → Busca appointment.type que coincidan
    ↓
_close_availability(appointment_types)
  → Para cada appointment.type:
    • Actualiza category_time_display = 'punctual_fields'
    • Actualiza start_datetime y end_datetime
    • Llama log_availability_change()
      → Registra en chatter
    • Recomputa availability_status
    ↓
Muestra notificación de éxito con detalles
    ↓
Cierra wizard
```

### Abrir Disponibilidad

```
Usuario ejecuta wizard
    ↓
Configura:
  - Acción: Abrir
  - Modo de Apertura: Disponible Ahora o Intervalo
    ↓
_open_availability(appointment_types)
  → Para cada appointment.type:
    
    SI modo = recurring:
      • category_time_display = 'recurring_fields'
      • start_datetime = False
      • end_datetime = False
    
    SI modo = custom_range:
      • category_time_display = 'punctual_fields'
      • start_datetime = fecha_inicio
      • end_datetime = fecha_fin
    
    • Registra en chatter
    • Recomputa availability_status
    ↓
Notificación de éxito
```

## 📚 Referencias

### Documentación Odoo
- [Appointment Module](https://www.odoo.com/documentation/18.0/applications/productivity/appointments.html)
- [Calendar Module](https://www.odoo.com/documentation/18.0/applications/productivity/calendar.html)
- [TransientModel](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#transient-models)

### Campos Nativos Utilizados
- `category_time_display`: Selection ('recurring_fields' | 'punctual_fields')
- `start_datetime`: Datetime
- `end_datetime`: Datetime
- `slot_ids`: One2many a appointment.slot

## 📄 Licencia

LGPL-3

## 👥 Soporte

Para soporte técnico:
- Revisar los logs: `/var/log/odoo/odoo.log`
- Consultar el chatter de appointment.type
- Contactar al administrador del sistema

---

**Versión:** 18.0.1.0.0  
**Autor:** smartgeeks.mx 
**Última actualización:** 2025  

---

## ✅ Checklist de Instalación

- [ ] Módulos `appointment`, `calendar`, `stock` instalados
- [ ] Módulo `mass_appointment_availability` copiado a addons
- [ ] Odoo reiniciado
- [ ] Módulo instalado desde Apps
- [ ] Usuario tiene permisos de Appointment Manager
- [ ] Appointment types tienen `branch_id` configurado
- [ ] Appointment types tienen `appointment_category` configurado
- [ ] Botón visible en vistas Calendar/Gantt/List
- [ ] Wizard se abre correctamente
- [ ] Prueba de cierre realizada exitosamente
- [ ] Prueba de apertura realizada exitosamente
- [ ] Registro en chatter verificado

**¡Felicidades! El módulo está listo para usar.** 🎉