# -*- coding: utf-8 -*-
{
    'name': 'Beauty Salon - Sale Commission Extension',
    'version': '18.0.1.0.0',
    'category': 'Sales/Commission',
    'summary': 'Extensión del módulo de comisiones para considerar ventas confirmadas y totalmente facturadas',
    'description': """
Beauty Salon Sale Commission Extension
=======================================

Extiende el módulo de comisiones de Odoo para incluir nuevos tipos de cálculo:

- **Amount Sold - Fully Invoiced**: Calcula comisiones basadas en el monto de órdenes de venta confirmadas Y totalmente facturadas
- **Quantity Sold - Fully Invoiced**: Calcula comisiones basadas en la cantidad de órdenes de venta confirmadas Y totalmente facturadas

Características:
----------------
* Hereda del módulo sale_commission nativo
* Agrega nuevos tipos de achievement
* Filtra órdenes por state='sale' AND invoice_status='invoiced'
* Mantiene compatibilidad con funcionalidad existente
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'sale_commission',
        'sale_management',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/commission_plan_achievement_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}