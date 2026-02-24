# -*- coding: utf-8 -*-
{
    'name': 'Beauty Salon - Commission Line Calculator',
    'version': '18.0.1.0.0',
    'category': 'Sales/Commission',
    'summary': 'Calculate commissions per sale order line',
    'description': """
Beauty Salon - Commission Line Calculator

Permite calcular comisiones por línea de orden en lugar de por orden completa.

Depende de:
- beauty_salon_sale_commission (comisiones con tipos invoiced)
- beauty_salon_commission_by_order_line (campo user_id en SO lines)
    """,
    'author': 'Pop Studio',
    'website': 'https://popstudio.mx',
    'license': 'LGPL-3',
    'depends': [
        'sale_commission',
        'beauty_salon_sale_commission',
        'beauty_salon_commission_by_order_line',
    ],
    'data': [
        'views/commission_plan_achievement_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}