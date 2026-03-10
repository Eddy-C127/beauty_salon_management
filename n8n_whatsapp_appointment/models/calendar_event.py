# -*- coding: utf-8 -*-
from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_from_n8n = fields.Boolean(
        string='Origen: n8n/WhatsApp',
        default=False,
        help='Indica si esta cita fue creada a través de la integración de n8n (WhatsApp).',
    )
    n8n_reservation_id = fields.Char(
        string='ID Reserva n8n',
        copy=False,
        help='Identificador único de la reserva asignado por el flujo de n8n.',
    )
    n8n_status = fields.Selection(
        selection=[
            ('draft', 'Pendiente de Anticipo'),
            ('paid', 'Confirmado y Pagado'),
            ('cancelled', 'Cancelado/Expirado'),
        ],
        string='Estado n8n',
        default='draft',
        copy=False,
        help='Estado de la reserva dentro del flujo de integración con n8n.',
    )
    n8n_partner_phone = fields.Char(
        string='Teléfono WhatsApp',
        copy=False,
        help='Número de WhatsApp del cliente tal como llegó en la reserva (rawPhone). '
             'Se usa para el webhook de confirmación de pago, independientemente del partner.',
    )
