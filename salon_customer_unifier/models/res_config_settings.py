# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salon_public_booking_mode = fields.Boolean(
        string='Modalidad de agendamiento público',
        config_parameter='salon_customer_unifier.public_booking_mode',
    )
