{
    'name': 'Salon Push Notifications',
    'version': '18.0.1.0.0',
    'summary': 'Push notifications for appointment confirmations and reminders',
    'category': 'Beauty Salon',
    'author': 'Custom',
    'depends': ['appointment', 'social_push_notifications', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
