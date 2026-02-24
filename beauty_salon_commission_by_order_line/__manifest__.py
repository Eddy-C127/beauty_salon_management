# -*- coding: utf-8 -*-
{
    'name': 'Beauty Salon - Commission by Order Line',
    'version': '18.0.1.0.0',
    'category': 'Sales/Commission',
    'summary': 'Calculate commissions per sale order line based on employee responsible for each line',
    'description': """
Beauty Salon - Commission by Order Line
=======================================

Extiende el cálculo de comisiones para funcionar a nivel de línea de orden de venta.

FASE 1: Campo user_id en sale.order.line
=========================================
✨ Características:
* Campo user_id en sale.order.line auto-llenado desde calendar.event.real_employee_id
* Permite edición manual del vendedor por línea (para over-selling, ajustes)
* Fallback automático a sale.order.user_id si no hay cita asociada
* Auditoría completa con tracking en chatter
* Compatible hacia atrás (sin breaking changes)

📊 Caso de Uso:
Cliente reserva Pestañas ($550) + Cejas ($550) = $1,100 en 1 orden
- Pestañas atendidas por Empleado 1 → sale_order_line[0].user_id = E1
- Cejas atendidas por Empleado 2 → sale_order_line[1].user_id = E2
- Cada empleado tiene su user_id correcto para comisiones futuras

🔗 Relación con módulos existentes:
* Convive con beauty_salon_sale_commission (no reemplaza)
* Base para beauty_salon_commission_line_calculator (FASE 3)
* Integración perfecta con calendar.event.real_employee_id
    """,
    'author': 'Pop Studio',
    'website': 'https://popstudio.mx',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'calendar',
        'appointment',
        'beauty_salon',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}