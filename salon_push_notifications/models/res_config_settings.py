from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salon_push_notif_enabled = fields.Boolean(
        string='Enable Appointment Push Notifications',
        config_parameter='salon_push_notifications.enabled',
        default=True,
    )
    salon_push_notif_reminder_hours = fields.Integer(
        string='Reminder Hours Before Appointment (fallback)',
        config_parameter='salon_push_notifications.reminder_hours',
        default=24,
        help='Used when the Appointment Type has no reminders configured.',
    )
