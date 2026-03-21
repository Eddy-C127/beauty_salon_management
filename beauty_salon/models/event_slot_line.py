from odoo import models, fields

_logger = __import__('logging').getLogger(__name__)


class BeautySalonEventSlotLine(models.TransientModel):
    """
    Slot disponible para selección inline en el formulario de calendar.event.
    Se crea en tiempo real via _compute_available_slots (store=False Many2many).
    El usuario selecciona via widget radio — el onchange escribe start/stop en el padre.
    """
    _name = 'beauty_salon.event_slot_line'
    _description = 'Slot disponible (inline)'
    _rec_name = 'slot_label'
    _order = 'slot_start asc'

    slot_start = fields.Datetime(string='Inicio (UTC)', required=True)
    slot_label = fields.Char(string='Horario')
