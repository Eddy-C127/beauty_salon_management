# -*- coding: utf-8 -*-
{
    'name': "advances_appointment_module",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['website_sale','payment','appointment_account_payment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/appointment_view.xml',
        'views/sale_portal_view.xml',
    ],
    # 'assets': {
    #     'web.assets_frontend': [
    #         'advances_appointment_module/static/src/js/appointment.js',
    #         'advances_appointment_module/static/src/js/payment_form.js',
    #     ],
    # },
}
