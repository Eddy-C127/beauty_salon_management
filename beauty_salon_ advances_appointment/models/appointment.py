# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    apply_advance = fields.Boolean()
    advance_percentage = fields.Integer('Porcentaje de Anticipo')
    fixed_import = fields.Float('Importe Fijo')
    advance_type = fields.Selection([
        ('fixed_import','Importe Fijo'),
        ('advance_percentage','Porcentaje de Anticipo'),
    ], string="Tipo de Anticipo")