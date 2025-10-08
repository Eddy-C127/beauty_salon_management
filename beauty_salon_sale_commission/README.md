# Beauty Salon - Sale Commission Extension

## Descripción

Este módulo extiende el módulo nativo `sale_commission` de Odoo 18 Enterprise para agregar nuevos tipos de cálculo de comisiones específicos para el negocio de Beauty Salon.

## Características

### Nuevos Tipos de Achievement

1. **Amount Sold - Fully Invoiced** (`amount_sold_invoiced`)
   - Calcula comisiones basadas en el **monto** de órdenes de venta
   - Solo considera órdenes con:
     - `state = 'sale'` (confirmadas)
     - `invoice_status = 'invoiced'` (totalmente facturadas)

2. **Quantity Sold - Fully Invoiced** (`qty_sold_invoiced`)
   - Calcula comisiones basadas en la **cantidad** de productos vendidos
   - Solo considera órdenes con:
     - `state = 'sale'` (confirmadas)
     - `invoice_status = 'invoiced'` (totalmente facturadas)

## Instalación

1. Copia el módulo en tu directorio de addons de Odoo
2. Actualiza la lista de aplicaciones
3. Instala el módulo `beauty_salon_sale_commission`

```bash
# Desde línea de comandos
./odoo-bin -d tu_database -u beauty_salon_sale_commission
```

## Dependencias

- `sale_commission` (Odoo Enterprise)
- `sale_management`
- `account`

## Uso

### Configuración de Plan de Comisiones

1. Ve a **Ventas > Comisiones > Commission Plans**
2. Crea o edita un plan de comisiones
3. En la pestaña **Achievements**, agrega un nuevo achievement
4. Selecciona uno de los nuevos tipos:
   - **Amount Sold - Fully Invoiced**
   - **Quantity Sold - Fully Invoiced**
5. Define el porcentaje de comisión (rate)
6. Opcionalmente filtra por producto o categoría

### Ejemplo de Configuración

**Scenario:** Comisión del 5% sobre ventas totalmente facturadas

```
Plan Name: Q1 2025 - Fully Invoiced Sales
Type: Achievements
Achievement:
  - Type: Amount Sold - Fully Invoiced
  - Rate: 5%
  - Product: [Todos]
```

## Comportamiento

### Órdenes que NO cuentan para comisiones (nuevos tipos):
- Órdenes en borrador (`state='draft'`)
- Órdenes confirmadas pero sin facturar (`invoice_status='to_invoice'`)
- Órdenes parcialmente facturadas (`invoice_status='partial'`)
- Órdenes canceladas

### Órdenes que SÍ cuentan para comisiones (nuevos tipos):
- Órdenes confirmadas Y totalmente facturadas
  - `state='sale'` AND `invoice_status='invoiced'`

## Estructura Técnica

```
beauty_salon_sale_commission/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── commission_achievement.py          # Extiende tipos para ajustes manuales
│   ├── commission_plan_achievement.py     # Extiende tipos en planes
│   └── achievement_report.py              # Lógica SQL para cálculo
├── views/
│   └── commission_plan_achievement_views.xml
├── security/
│   └── ir.model.access.csv
└── README.md
```

## Testing

### Caso de Prueba 1: Orden Confirmada pero No Facturada

```python
# Crear orden de venta
so = env['sale.order'].create({...})
so.action_confirm()
# invoice_status = 'to_invoice'
# Resultado: NO genera comisión con nuevos tipos
```

### Caso de Prueba 2: Orden Confirmada y Totalmente Facturada

```python
# Crear orden de venta
so = env['sale.order'].create({...})
so.action_confirm()
# Crear factura
invoice = so._create_invoices()
invoice.action_post()
# invoice_status = 'invoiced'
# Resultado: SÍ genera comisión con nuevos tipos
```

### Caso de Prueba 3: Orden Parcialmente Facturada

```python
# Crear orden con múltiples líneas
so = env['sale.order'].create({...})
so.action_confirm()
# Facturar solo una línea
# invoice_status = 'partial'
# Resultado: NO genera comisión con nuevos tipos
```

## Troubleshooting

### Las comisiones no se calculan

1. Verifica que el plan esté en estado **Approved**
2. Confirma que el usuario/equipo está asignado al plan
3. Verifica que la fecha de la orden esté dentro del rango del plan
4. Confirma que `invoice_status='invoiced'` en la orden

### Comisiones duplicadas

- Los nuevos tipos (`amount_sold_invoiced`, `qty_sold_invoiced`) son **independientes** de los tipos originales
- No mezcles tipos originales con nuevos tipos en el mismo plan a menos que sea intencional

## Soporte

Para soporte técnico, contacta a: tu-email@empresa.com

## Licencia

LGPL-3

## Changelog

### Version 1.0.0 (2025-01-XX)
- Implementación inicial
- Nuevos tipos de achievement para ventas facturadas
- Herencia limpia del módulo sale_commission