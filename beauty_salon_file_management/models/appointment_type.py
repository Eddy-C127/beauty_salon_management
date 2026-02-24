# -*- coding: utf-8 -*-
from odoo import fields, models


class CalendarAppointmentType(models.Model):
    """
    Extiende calendar.appointment.type para agregar el nivel de expediente
    requerido antes de iniciar un servicio.

    Niveles:
    - basico:      Solo aviso de privacidad (ej. corte, uñas simples)
    - intermedio:  Aviso + alergias documentadas (ej. tintes, tratamientos)
    - clinico:     Todo completo (ej. micropigmentación, láser, químicos fuertes)
    """
    _inherit = 'appointment.type'

    nivel_expediente_requerido = fields.Selection(
        selection=[
            ('basico', 'Básico — Solo aviso de privacidad'),
            ('intermedio', 'Intermedio — Aviso + Alergias'),
            ('clinico', 'Clínico — Expediente completo'),
        ],
        string='Nivel de Expediente Requerido',
        default='basico',
        required=True,
        help=(
            'Define qué tan completo debe estar el expediente de la clienta '
            'antes de poder iniciar este servicio.\n\n'
            '• Básico: Solo necesita el aviso de privacidad firmado.\n'
            '• Intermedio: Aviso + alergias documentadas.\n'
            '• Clínico: Expediente completo (recomendado para servicios '
            'con productos químicos o de riesgo médico).'
        ),
    )
