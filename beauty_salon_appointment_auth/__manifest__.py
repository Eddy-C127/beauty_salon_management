# -*- coding: utf-8 -*-
{
    'name': 'Beauty Salon - Appointment Authentication',
    'version': '18.0.1.0.0',
    'category': 'Services/Appointment',
    'summary': 'Require login before booking appointments to prevent duplicate contacts',
    'description': """
Beauty Salon Appointment Authentication
========================================

Prevents duplicate contact creation by requiring users to login or sign up
before booking appointments.

Features:
---------
* Configurable per appointment type (boolean field)
* Maintains full backward compatibility
* Preserves all booking parameters during login flow
* Visual restriction: hides submit button for public users
* Clean integration with Odoo's native authentication
    """,
    'author': 'Pop Studio',
    'website': 'https://popstudio.com',
    'license': 'LGPL-3',
    'depends': [
        'appointment',
        'website',
    ],
    'data': [
        'views/appointment_type_views.xml',
        'views/appointment_form_auth_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}