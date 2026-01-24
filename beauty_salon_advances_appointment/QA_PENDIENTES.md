# Auditoría QA - Correcciones Pendientes

**Módulo:** `beauty_salon_advances_appointment`  
**Fecha de Auditoría:** 2026-01-24  
**Auditor:** Antigravity AI  

---

## 🔴 Prioridad 1 - CRÍTICAS

### 1.1 `payment_provider.py` No Está Siendo Cargado

**Archivo:** `models/__init__.py` (Línea 6)
```python
#from . import payment_provider  # ← COMENTADO
```

**Impacto:** El archivo que modifica el monto mostrado en Stripe NO SE EJECUTA. El cliente puede ver un monto diferente al que se le cobrará.

**Corrección:**
```python
from . import payment_provider  # Descomentar esta línea
```

---

### 1.2 Sin Manejo de Excepciones en Creación de Factura

**Archivo:** `models/payment_transaction.py` (Líneas 27-32)

**Problema:** Si `create_invoices()` falla, el cliente ve "pago exitoso" pero no se crea la factura de anticipo.

**Corrección:**
```python
try:
    downpayment = self.env['sale.advance.payment.inv'].with_context(ctx).create({
        'advance_payment_method': 'fixed',
        'amount': total_advance,
        'fixed_amount': total_advance,
    })
    downpayment.create_invoices()
except Exception as e:
    _logger.error(f"Error al crear factura de anticipo para orden {confirmed_orders.name}: {e}")
    # Opcional: notificar al administrador
```

---

## 🟠 Prioridad 2 - ALTAS

### 2.1 Anticipo Puede Exceder Total de la Orden

**Escenario:** Cita de $100 con anticipo fijo configurado en $500.

**Corrección en `_calculate_total_advance_amount()`:**
```python
# Al final del método, antes del return:
order_total = self.amount_total
if total_advance > order_total:
    total_advance = order_total
return total_advance, advance_count
```

---

### 2.2 Falta `sale_subscription` en Dependencias

**Archivo:** `__manifest__.py`

**Problema:** El controlador importa de `sale_subscription` pero no está en `depends`.

**Opciones:**
1. Agregar `'sale_subscription'` a `depends`
2. O eliminar la importación no utilizada del controlador

---

## 🟡 Prioridad 3 - MEDIAS

### 3.1 Campo `apply_advance` No Utilizado

**Archivo:** `models/appointment.py`
```python
apply_advance = fields.Boolean()  # ← Nunca se usa
```

**Opciones:**
1. Eliminar el campo
2. O implementar lógica que lo use como interruptor principal

---

### 3.2 Sin Validación de Montos Negativos

**Archivo:** `models/sale_order.py`

**Corrección:**
```python
advance_amount = max(0, advance_amount)  # Asegurar que nunca sea negativo
```

---

### 3.3 Sin Valor por Defecto ni Restricciones en Porcentaje

**Archivo:** `models/appointment.py`

**Corrección:**
```python
advance_percentage = fields.Integer(
    'Porcentaje de Anticipo',
    default=0
)

@api.constrains('advance_percentage')
def _check_percentage(self):
    for record in self:
        if record.advance_percentage < 0 or record.advance_percentage > 100:
            raise ValidationError("El porcentaje debe estar entre 0 y 100")
```

---

## 🟢 Prioridad 4 - BAJAS

### 4.1 Imports No Utilizados en Controlador

**Archivo:** `controllers/payment_portal.py`

Eliminar importaciones no utilizadas:
- `datetime`
- `werkzeug`
- `OrderedDict`
- `relativedelta`
- `ceil`
- `url_encode`
- `Command`
- `format_date`, `str2bool`
- `website_sale_portal`
- `payment_utils`
- `portal_pager`
- `sale_portal`
- `SUBSCRIPTION_PROGRESS_STATE`, `SUBSCRIPTION_CLOSED_STATE`

---

## 📋 Casos de Prueba Pendientes

| # | Caso de Prueba | Estado |
|---|---------------|--------|
| 1 | Carrito vacío → Checkout | ⬜ |
| 2 | 1 cita SIN anticipo | ⬜ |
| 3 | 1 cita CON anticipo fijo $100 | ⬜ |
| 4 | 1 cita CON anticipo 50% sobre $200 | ⬜ |
| 5 | 3 citas CON anticipo fijo $100 c/u | ⬜ |
| 6 | 2 citas mixtas (1 fijo, 1 porcentaje) | ⬜ |
| 7 | Producto + Cita con anticipo | ⬜ |
| 8 | advance_percentage = 0 | ⬜ |
| 9 | fixed_import = 0 | ⬜ |
| 10 | Re-pago (ya tiene factura) | ⬜ |
| 11 | Usuario guest | ⬜ |
| 12 | Stripe Form monto correcto | ⬜ |

---

## Notas

- Backup disponible en: `beauty_salon_advances_appointment_backup_20260124/`
- Versión actual: `18.0.1.0.2`
