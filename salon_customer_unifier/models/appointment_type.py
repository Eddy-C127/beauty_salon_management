# -*- coding: utf-8 -*-
from odoo import fields, models


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    salon_correction_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='salon_correction_appointment_type_user_rel',
        column1='appointment_type_id',
        column2='user_id',
        string='Responsables de corrección de datos',
        domain=[('share', '=', False)],  # solo usuarios internos
        help=(
            'Usuarios que recibirán una actividad cuando un cliente indique '
            'que sus datos registrados son incorrectos al agendar una cita. '
            'Si no se configura ninguno, la actividad se asigna al administrador.'
        ),
    )
