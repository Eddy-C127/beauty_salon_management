from odoo import models, fields
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class BeautySalonSlotLine(models.TransientModel):
    """Cada slot disponible que se muestra en el wizard"""
    _name = 'beauty_salon.slot.line'
    _description = 'Slot Disponible'
    _order = 'slot_start asc'

    wizard_id = fields.Many2one('beauty_salon.slot.selector', ondelete='cascade')
    slot_start = fields.Datetime(string='Inicio', required=True)
    slot_label = fields.Char(string='Hora')

    def action_select_this_slot(self):
        """
        Toque directo sobre un slot: aplica y cierra en un solo paso.
        slot_start está almacenado en UTC (Odoo siempre guarda Datetime en UTC).
        appointment_duration está en HORAS (float).

        Modo edición: el calendar_event_id ya existe → actualiza start/stop.
        Modo creación: no hay calendar_event_id → crea la cita completa y redirige.
        """
        self.ensure_one()
        wizard = self.wizard_id
        apt_type = wizard.appointment_type_id

        duration_hours = apt_type.appointment_duration or 1.0
        slot_start = self.slot_start
        slot_stop = slot_start + timedelta(hours=duration_hours)

        if wizard.calendar_event_id:
            # ── MODO EDICIÓN: evento ya existe en DB ──────────────────────
            event = wizard.calendar_event_id
            event.with_context(skip_overlap_check=True).write({
                'start': slot_start,
                'stop': slot_stop,
            })
            _logger.info(
                f'✅ Slot aplicado a cita #{event.id}: '
                f'{slot_start.strftime("%d/%m/%Y %H:%M")} → {slot_stop.strftime("%H:%M")}'
            )
            return {'type': 'ir.actions.act_window_close'}

        else:
            # ── MODO CREACIÓN: evento aún no existe en DB ─────────────────
            # Crear la cita completa con todos los datos del wizard
            vals = {
                'appointment_type_id': apt_type.id,
                'start': slot_start,
                'stop': slot_stop,
                'appointment_status': 'booked',
            }
            if wizard.real_employee_id:
                vals['real_employee_id'] = wizard.real_employee_id.id
            if wizard.pending_customer_id:
                vals['manual_customer_id'] = wizard.pending_customer_id.id
                vals['partner_id'] = wizard.pending_customer_id.id
            if wizard.pending_user_id:
                vals['user_id'] = wizard.pending_user_id.id

            event = self.env['calendar.event'].with_context(
                skip_overlap_check=True
            ).create(vals)

            _logger.info(
                f'✅ Cita #{event.id} creada desde slot selector: '
                f'{slot_start.strftime("%d/%m/%Y %H:%M")} → {slot_stop.strftime("%H:%M")}'
            )

            # Cerrar el wizard y abrir la cita recién creada
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'calendar.event',
                'res_id': event.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_appointment_type_id': apt_type.id},
            }


class BeautySalonSlotSelector(models.TransientModel):
    """
    COMPONENTE C: Wizard touch-friendly para seleccionar slot disponible.
    Cada slot es un botón grande que confirma en un solo toque.

    Soporta dos modos:
    - Edición: calendar_event_id apunta a una cita existente → solo actualiza start/stop
    - Creación: calendar_event_id vacío → crea la cita al confirmar el slot
    """
    _name = 'beauty_salon.slot.selector'
    _description = 'Seleccionar Slot Disponible'

    # Modo edición: cita ya existente
    calendar_event_id = fields.Many2one('calendar.event', string='Cita', required=False)

    # Campos comunes
    appointment_type_id = fields.Many2one('appointment.type', string='Tipo de Cita', required=True)
    real_employee_id = fields.Many2one('hr.employee', string='Empleado')
    selected_date = fields.Date(string='Fecha')
    available_slot_ids = fields.One2many('beauty_salon.slot.line', 'wizard_id', string='Slots Disponibles')

    # Modo creación: datos pendientes del formulario (aún no guardados)
    pending_customer_id = fields.Many2one('res.partner', string='Cliente (pendiente)')
    pending_user_id = fields.Many2one('res.users', string='Usuario (pendiente)')


class BeautySalonOverlapConfirm(models.TransientModel):
    """
    Wizard de confirmación de solapamiento.
    Se abre cuando el write() detecta que el empleado ya tiene una cita en ese horario.
    El usuario puede continuar (forzar guardado) o cancelar.
    """
    _name = 'beauty_salon.overlap.confirm'
    _description = 'Confirmar cita solapada'

    calendar_event_id = fields.Many2one('calendar.event', string='Cita', required=True)
    conflict_message = fields.Text(string='Detalle del conflicto', readonly=True)
    pending_vals = fields.Text(string='Valores pendientes (JSON)', readonly=True)

    def action_confirm(self):
        """El usuario elige continuar — guarda con skip_overlap_check."""
        self.ensure_one()
        import json as _json
        vals = _json.loads(self.pending_vals or '{}')
        if vals and self.calendar_event_id:
            self.calendar_event_id.with_context(skip_overlap_check=True).write(vals)
        return {'type': 'ir.actions.act_window_close'}
