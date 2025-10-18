# -*- coding: utf-8 -*-
{
    'name': 'Beauty Salon - Survey & Warranty System',
    'version': '18.0.1.0.6',
    'category': 'Services/Survey',
    'summary': 'Sistema integral de encuestas, garantías y ajuste de comisiones para Pop Studio',
    'description': """
Beauty Salon Survey & Warranty System
======================================

Sistema modular para gestión de:
- Encuestas de satisfacción al concluir servicios
- Garantías automáticas para encuestas negativas
- Ajuste de comisiones basado en satisfacción del cliente
- Integración con sistema de comisiones existente

Configuración:
--------------
Accede a Settings > General Settings > Beauty Salon Survey
    """,
    'author': 'Pop Studio',
    'website': 'https://popstudio.com',
    'license': 'LGPL-3',
    
    'depends': [
        'beauty_salon',
        'beauty_salon_sale_commission',
        'survey',
        'mail',
        'project',
    ],
    
    'data': [
        # Security
        'security/survey_security.xml',
        'security/ir.model.access.csv',
        
        # Data (valores por defecto)
        'data/pop_survey_config_data.xml',
        'data/mail_activity_type.xml',      # ← NUEVO
        
        # Views
        'views/res_config_settings_views.xml',
        'views/calendar_event_views.xml',
        'views/sale_order_views.xml',
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,
}