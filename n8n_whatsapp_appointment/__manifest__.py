# -*- coding: utf-8 -*-
{
    'name': 'n8n WhatsApp Appointment Integration',
    'version': '18.0.1.1.0',
    'summary': 'Capa de integración REST entre n8n (WhatsApp) y el sistema de agendamiento de Odoo',
    'description': """
        Módulo de integración que expone una API REST JSON para que n8n pueda:
        - Consultar disponibilidad de citas (on-the-fly, sin modelos estáticos)
        - Crear reservas temporales vinculadas a anticipos de pago
        - Cancelar reservas expiradas
        - Recibir notificaciones de confirmación de pago (webhooks salientes)
    """,
    'author': 'Beauty Salon Dev',
    'category': 'Appointments/Integration',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'calendar',
        'website_appointment',
        'salon_customer_unifier',
        'beauty_salon_advances_appointment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/n8n_webhook_config_views.xml',
        'views/n8n_api_endpoint_views.xml',
        'views/calendar_event_views.xml',
        'views/n8n_company_context_views.xml',
        'views/res_partner_views.xml',
        'data/n8n_api_endpoint_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
