# -*- coding: utf-8 -*-
{
    'name': "Beauty Salon Advances Appointment Module",

    'summary': "Install Beauty Salon Advances Appointment Module",

    'description': """
Long description of module's purpose
    """,

    'author': "Smargeeks",
    'website': "smargeeks.mx",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.1.0.2',

    # any module necessary for this one to work correctly
    'depends': ['website_sale','payment_stripe','appointment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/appointment_view.xml',
        'views/sale_portal_view.xml',
    ],
}
