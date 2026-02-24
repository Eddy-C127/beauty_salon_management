# Beauty Salon - Commission by Order Line

## 📋 Descripción

Módulo que extiende el cálculo de comisiones para funcionar a nivel de **línea de orden de venta**, permitiendo que cada servicio o producto tenga su propio vendedor asignado.

## ✨ Problema que Resuelve

### Antes (Defectuoso)
```
Orden: Paquete Promocional $1,100
  ├─ Pestañas $550 → Empleado 1
  ├─ Cejas $550 → Empleado 2
  └─ sale.order.user_id = Empleado 1

Resultado:
  ✗ Empleado 1 recibe comisión sobre $1,100 (100%)
  ✗ Empleado 2 recibe $0 (incorrecto)
```

### Después (Correcto)
```
Orden: Paquete Promocional $1,100
  ├─ Pestañas $550 → sale_order_line[0].user_id = Empleado 1
  ├─ Cejas $550 → sale_order_line[1].user_id = Empleado 2
  └─ sale.order.user_id = Empleado 1 (informativo)

Resultado:
  ✓ Empleado 1 recibe comisión sobre $550
  ✓ Empleado 2 recibe comisión sobre $550
```

## 🎯 Características

- ✅ Campo `user_id` en `sale.order.line` auto-llenado desde `calendar.event.real_employee_id`
- ✅ Permite edición manual del vendedor por línea
- ✅ Fallback automático a `sale.order.user_id` si no hay cita
- ✅ Integración perfecta con `beauty_salon_sale_commission`
- ✅ Comisiones calculadas **por línea** (cuando se combina con las modificaciones a `achievement_report`)
- ✅ Auditoría completa en chatter (tracking)
- ✅ Compatible hacia atrás (no breaking changes)

## 📦 Instalación

1. **Copiar el módulo** a addons:
```bash
cp -r beauty_salon_commission_by_order_line /ruta/odoo/addons/
```

2. **Instalar en Odoo**:
   - Apps → Actualizar lista de aplicaciones
   - Buscar "Beauty Salon - Commission by Order Line"
   - Click en Instalar

3. **Actualizar `beauty_salon_sale_commission`**:
   - Este módulo requiere cambios en `achievement_report`
   - Ver PARTE 2 del documento de implementación

## 🔄 Flujo de Funcionamiento

### Booking Website (2 servicios en 1 orden)
```
1️⃣ Cliente selecciona Pestañas
   → calendar.event[0] creada
   → real_employee_id = Empleado 1

2️⃣ Cliente selecciona Cejas
   → calendar.event[1] creada
   → real_employee_id = Empleado 2

3️⃣ Cliente paga en checkout
   → sale.order creada ($1,100)
   → sale_order_line[0] Pestañas
      └─ user_id = Empleado 1 (auto-llena desde calendar.event[0])
   → sale_order_line[1] Cejas
      └─ user_id = Empleado 2 (auto-llena desde calendar.event[1])

4️⃣ Orden confirmada y facturada
   → achievement_report calcula comisiones por línea
   → Empleado 1: Comisión sobre $550 ✅
   → Empleado 2: Comisión sobre $550 ✅
```

### Caso: Over-selling por Cajera
```
Cita: Pestañas con Empleado 1
└─ sale_order_line[0] Pestañas → user_id = Empleado 1

Cajera hace over-selling:
└─ sale_order_line[1] Kit Limpieza → user_id = ? (vacío)

Opción 1: Editar manualmente
└─ Click en línea del Kit → cambiar user_id a Cajera ✅

Opción 2: Fallback automático
└─ Si no se edita, user_id = sale.order.user_id (Empleado 1) ⚠️
└─ Mejor: Editar manualmente para precisión
```

## ✏️ Edición Manual

### En Vista de Árbol (Tree View)
```
Orden #12345
├─ [Pestañas]     [Empleado 1]  $550
├─ [Cejas]        [Empleado 2]  $550
└─ [Kit Limpieza] [Seleccionar]  $100

Hacer clic en "Seleccionar" → abre dropdown con usuarios
```

### En Formulario
```
Línea: Kit Limpieza
├─ Producto: Kit Limpieza
├─ Cantidad: 1
├─ Precio: $100
├─ Vendedor: [Seleccionar usuario] ← Editar aquí
└─ [Guardar]
```

## 🔗 Dependencias

- `sale_management` - Gestión de ventas
- `calendar` - Módulo de calendario
- `appointment` - Citas
- `beauty_salon` - Módulo base
- `beauty_salon_sale_commission` - **REQUERIDO** (necesita modificaciones)

## 🔐 Permisos

| Grupo | Permisos |
|-------|----------|
| **Vendedor** | Lectura de `user_id` |
| **Gerente** | Lectura y escritura de `user_id` |

## 📊 Casos de Uso

### Caso 1: Paquetes Promocionales
```
Paquete "Belleza Total" $1,200
├─ Pestañas (Empleado 1) $600
├─ Cejas (Empleado 2) $400
└─ Limpieza facial (Empleado 3) $200

Comisiones (asumiendo 5% plan):
├─ Empleado 1: $30
├─ Empleado 2: $20
└─ Empleado 3: $10
Total: $60 ✅
```

### Caso 2: Servicio + Producto
```
Tatuaje de Cejas (Artist) $500
Kit de Cuidados (Gerente over-sell) $80

Comisiones:
├─ Artist: $25 (sobre $500)
└─ Gerente: $4 (sobre $80)
```

### Caso 3: Promoción Multi-empleado
```
Promo "Black Friday" (Vendedor 1 coordina)
├─ Pestañas (Empleado A) $300
├─ Cejas (Empleado B) $300
└─ Descuento: -$100

Comisiones recalculadas por línea:
├─ Empleado A: $15 (sobre $300)
└─ Empleado B: $15 (sobre $300)
```

## 🐛 Troubleshooting

### El campo `user_id` no se auto-llena

**Verificar:**
1. ¿Tiene `calendar_event_id` asociada la línea?
2. ¿Tiene `calendar.event.real_employee_id` asignado?

**Solución:**
```python
# Verificar en consola
sol = env['sale.order.line'].browse(line_id)
print(f"calendar_event_id: {sol.calendar_event_id}")
print(f"real_employee_id: {sol.calendar_event_id.real_employee_id}")
print(f"user_id resultante: {sol.user_id}")
```

### El campo no permite editar

**Verificar:**
1. ¿Es usuario manager (group_sale_manager)?
2. ¿Está la orden en estado 'sale'?

**Solución:**
- Cambiar a gerente si es necesario
- El campo es `readonly=False`, así que debe ser editable

### Las comisiones no se calculan correctamente

**Este es síntoma de que `beauty_salon_sale_commission` NO fue modificado correctamente.**

Ver PARTE 2 del documento de implementación para actualizar `achievement_report`.

## 📈 Performance

- ✅ Sin impacto significativo
- ✅ Solo agrega 1 campo computado (ligero)
- ✅ No afecta queries complejas
- ✅ Recomendado para cualquier volumen

## 🔄 Roadmap Futuro

- [ ] Toggle por plan de comisiones (enable_line_commission)
- [ ] Reporte de comisiones por empleado y línea
- [ ] Dashboard de comisiones desglosadas
- [ ] Sincronización con nómina

## 📝 Cambios Técnicos

### Modelos Modificados

**`sale.order.line`**
- Campo `user_id` ahora es `compute=_compute_user_id, store=True, readonly=False`
- Auto-llena desde `calendar.event.real_employee_id.user_id`
- Con tracking para auditoría

### Vistas Modificadas

- `sale.order.line` tree view → Agregar columna `user_id`
- `sale.order.line` form view → Agregar campo `user_id`
- `sale.order` form view → Agregar info sobre comisiones por línea

### Seguridad

- `sales_team.group_sale_salesman` → Solo lectura
- `sales_team.group_sale_manager` → Lectura y escritura

## 📞 Soporte

Para soporte técnico: contacto@popstudio.com

## 📄 Licencia

LGPL-3

## 👥 Autor

Pop Studio - https://popstudio.com

---

**Versión:** 18.0.1.0.0  
**Última actualización:** Noviembre 2025