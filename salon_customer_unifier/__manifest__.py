# -*- coding: utf-8 -*-
{
    'name': 'Salon Customer Unifier',
    'version': '18.0.1.3.0',
    'category': 'Services/Appointment',
    'summary': 'Unifica clientes por teléfono en el flujo Cita → Pago',
    'description': """
Salon Customer Unifier
======================
Utiliza el Número de Teléfono como identificador único para evitar
duplicidad de contactos (res.partner) cuando un cliente agenda y
paga como invitado.

Características:
- Phone-First Match: busca/crea partner por teléfono (E.164)
- Integración intl-tel-input: validación y formato internacional
- Sesión unificada: el partner correcto fluye a calendar.booking y al pago
- Compatible con beauty_salon_advances_appointment
    """,
    'author': 'Pop Studio / Smargeeks',
    'website': 'https://popstudiomx.com',
    'license': 'LGPL-3',
    'depends': [
        'appointment',
        'website_appointment',
        'website_appointment_sale',
        'website_sale',
        'phone_validation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/appointment_type_views.xml',
        'views/appointment_form_template.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'salon_customer_unifier/static/src/lib/intl-tel-input/css/intlTelInput.min.css',
            'salon_customer_unifier/static/src/lib/intl-tel-input/js/intlTelInput.min.js',
            'salon_customer_unifier/static/src/css/phone_widget.css',
            'salon_customer_unifier/static/src/js/phone_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
