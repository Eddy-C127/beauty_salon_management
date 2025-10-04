# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    apply_advance = fields.Boolean()
    advance_percentage = fields.Integer()