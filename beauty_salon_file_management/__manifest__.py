# -*- coding: utf-8 -*-
{
    'name': 'Beauty Salon - File Management',
    'summary': 'Gestión de Expedientes Clínicos de Clientas para Salones de Belleza',
    'description': """
        Módulo para la gestión integral de expedientes clínicos de clientas
        en salones de belleza y estéticas.
        Cumple con NOM-004-SSA3-2012 y LFPDPPP (México).

        Funcionalidades:
        - Expediente clínico por clienta (alergias, tipo de piel, condiciones médicas)
        - Historial de sesiones con fotos antes/después
        - Flujo de trabajo: Iniciar/Concluir cita con wizards mobile-first
        - Firma digital de consentimiento informado
        - Auditoría automatizada para validación de comisiones
        - Dashboard con métricas de cumplimiento por artista
        - Alertas automáticas vía Odoo Bot
    """,
    'author': 'Smartgeeks',
    'website': 'https://smartgeeks.mx',
    'support': 'contacto@smartgeeks.mx',
    'category': 'Healthcare/Beauty',
    'version': '18.0.3.0.0',
    'license': 'LGPL-3',

    'depends': [
        'beauty_salon',
        'mail',
        'contacts',
        'board',
        'account',
    ],

    'data': [
        # Security
        'security/popstudio_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_cron_data.xml',

        # Views - Modelos principales
        'views/expediente_sesion_views.xml',
        'views/res_partner_views.xml',
        'views/calendar_event_views.xml',
        'views/appointment_type_views.xml',

        # Wizards
        'views/wizard_expediente_rapido_views.xml',
        'views/wizard_iniciar_cita_views.xml',
        'views/wizard_concluir_cita_views.xml',

        # Acciones de auditoría (antes de menús que las referencian)
        'views/auditoria_views.xml',

        # Dashboard (board) — después de auditoría porque referencia sus acciones
        'views/dashboard_board_views.xml',

        # Menús
        'views/menu_actions.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'beauty_salon_file_management/static/src/css/popstudio_mobile.css',
            'beauty_salon_file_management/static/src/js/components/mobile_wizard.js',
        ],
    },

    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
