# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    """
    Extensión de calendar.event para integrar el flujo de expedientes clínicos.
    Agrega botones de Iniciar/Concluir y auditoría de expedientes.

    Reutiliza campos del módulo base beauty_salon:
    - appointment_status (en vez de popstudio_state)
    - real_employee_id (en vez de artista_id)
    - manual_customer_id / partner_id (en vez de partner_cliente_id)
    - appointment_type_id.name (en vez de servicio_nombre)
    """
    _inherit = 'calendar.event'

    # ─── CAMPOS DE AUDITORÍA (únicos de este módulo) ─────────────────────────

    expediente_completado = fields.Boolean(
        string='Expediente Completado',
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
        help='Se marca automáticamente al concluir la cita y crear el expediente. '
             'NO puede modificarse manualmente.',
    )
    expediente_completado_count = fields.Integer(
        string='Expedientes Completos',
        compute='_compute_expediente_completado_count',
        store=True,
        help='1 si tiene expediente completo, 0 si no. Para sumatorias en dashboards.',
    )
    expediente_faltante_count = fields.Integer(
        string='Expedientes Faltantes',
        compute='_compute_expediente_completado_count',
        store=True,
        help='1 si NO tiene expediente completo, 0 si sí. Para sumatorias en dashboards.',
    )
    sesion_id = fields.Many2one(
        'popstudio.expediente.sesion',
        string='Sesión Vinculada',
        readonly=True,
        copy=False,
        ondelete='set null',
    )
    # ─── URGENCIA VISUAL (para kanban) ─────────────────────────────────────────

    urgencia_cita = fields.Selection(
        selection=[
            ('tarde', 'Tarde'),
            ('ahora', 'Ahora'),
            ('proxima', 'Próxima'),
            ('normal', 'Normal'),
        ],
        compute='_compute_urgencia_cita',
        string='Urgencia',
    )

    # ─── DATOS MÉDICOS (solo vista) ───────────────────────────────────────────

    alergias_cliente = fields.Text(
        string='Alergias Conocidas',
        compute='_compute_alergias_cliente',
    )

    @api.depends('expediente_completado')
    def _compute_expediente_completado_count(self):
        for record in self:
            record.expediente_completado_count = 1 if record.expediente_completado else 0
            record.expediente_faltante_count = 0 if record.expediente_completado else 1

    def _compute_urgencia_cita(self):
        """Calcula urgencia visual basada en proximidad al horario de inicio.

        Rangos:
        - ahora:   falta <= 30 min para la cita O ya se pasó la hora y sigue booked/attended
        - proxima: falta entre 30 min y 2 horas
        - normal:  falta > 2 horas, o la cita ya concluyó/canceló
        """
        now = fields.Datetime.now()
        for event in self:
            if not event.start or event.appointment_status in ('concluded', 'cancelled'):
                event.urgencia_cita = 'normal'
                continue
            delta_min = (event.start - now).total_seconds() / 60
            if delta_min < -10:
                event.urgencia_cita = 'tarde'
            elif delta_min <= 30:
                event.urgencia_cita = 'ahora'
            elif delta_min <= 120:
                event.urgencia_cita = 'proxima'
            else:
                event.urgencia_cita = 'normal'

    # ─── CAMPOS PARA AUDITORÍA (REPORTES) ────────────────────────────────────

    duracion_real_minutos = fields.Integer(
        string='Duración Real (min)',
        help='Tiempo real de la sesión en minutos.',
        readonly=True,
        copy=False,
    )
    inicio_real = fields.Datetime(
        string='Inicio Real',
        readonly=True,
        copy=False,
    )
    fin_real = fields.Datetime(
        string='Fin Real',
        readonly=True,
        copy=False,
    )

    # ─── HELPERS ─────────────────────────────────────────────────────────────

    def _get_cliente(self):
        """Obtiene la clienta principal usando el patrón del módulo base."""
        self.ensure_one()
        return self.manual_customer_id or self.partner_id

    @api.depends('manual_customer_id', 'partner_id', 'manual_customer_id.alergias', 'partner_id.alergias')
    def _compute_alergias_cliente(self):
        for event in self:
            cliente = event.manual_customer_id or event.partner_id
            event.alergias_cliente = cliente.alergias if cliente else False

    # ─── VALIDACIONES ─────────────────────────────────────────────────────────

    def _check_puede_iniciar(self):
        """Valida si la cita puede iniciarse."""
        self.ensure_one()
        if self.appointment_status != 'booked':
            raise UserError(
                _('No se puede iniciar: La cita está en estado "%s". '
                  'Solo se pueden iniciar citas con estado "Booked".',
                  self.appointment_status)
            )

    def _check_puede_concluir(self):
        """Valida si la cita puede concluirse."""
        self.ensure_one()
        if self.appointment_status != 'attended':
            raise UserError(
                _('No se puede concluir: La cita está en estado "%s". '
                  'Solo se pueden concluir citas en estado "Attended".',
                  self.appointment_status)
            )

    # ─── ACCIONES - BOTONES ───────────────────────────────────────────────────

    def action_iniciar_cita(self):
        """
        Abre el wizard de Inicio de Cita.

        Antes de abrir el wizard principal, verifica que el expediente de la
        clienta esté completo según el nivel requerido por el tipo de servicio.
        Si no lo está, abre primero el WizardExpedienteRapido.
        """
        self.ensure_one()
        self._check_puede_iniciar()

        partner = self._get_cliente() or self.partner_ids[:1]

        # Determinar nivel requerido por el tipo de servicio
        nivel = 'basico'
        if self.appointment_type_id:
            nivel = self.appointment_type_id.nivel_expediente_requerido or 'basico'

        # Verificar si el expediente está completo para el nivel
        if partner and not partner.expediente_completo_para_nivel(nivel):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Completar Expediente — %s', partner.name),
                'res_model': 'popstudio.wizard.expediente.rapido',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_calendar_event_id': self.id,
                    'default_partner_id': partner.id,
                    'default_nivel_requerido': nivel,
                    'dialog_size': 'medium',
                },
            }

        # Expediente OK — abrir wizard principal directamente
        return {
            'type': 'ir.actions.act_window',
            'name': _('Iniciar Cita'),
            'res_model': 'popstudio.wizard.iniciar.cita',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_calendar_event_id': self.id,
                'default_partner_id': partner.id if partner else False,
                'dialog_size': 'medium',
            },
        }

    def action_concluir_cita(self):
        """Abre el wizard de Conclusión de Cita."""
        self.ensure_one()
        self._check_puede_concluir()

        partner = self._get_cliente()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Concluir Cita'),
            'res_model': 'popstudio.wizard.concluir.cita',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_calendar_event_id': self.id,
                'default_partner_id': partner.id if partner else False,
                'default_sesion_id': self.sesion_id.id if self.sesion_id else False,
                'dialog_size': 'medium',
            },
        }

    def action_ver_expediente(self):
        """Smart button: Navega a la sesión o al expediente de la clienta."""
        self.ensure_one()
        if self.sesion_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Expediente de Sesión'),
                'res_model': 'popstudio.expediente.sesion',
                'res_id': self.sesion_id.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            }
        partner = self._get_cliente()
        if partner:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Expediente de %s', partner.name),
                'res_model': 'res.partner',
                'res_id': partner.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            }
        raise UserError(_('No hay clienta asignada a esta cita.'))

    def action_cancelar_cita_expediente(self):
        """Cancela la cita en el flujo de expedientes."""
        self.ensure_one()
        self.write({'appointment_status': 'cancelled'})
        self.message_post(
            body=_('Cita cancelada por %s', self.env.user.name),
            message_type='comment',
        )

    # ─── NOTIFICACIÓN AUTOMÁTICA (llamada por cron) ───────────────────────────

    @api.model
    def _enviar_alerta_expediente_incompleto(self):
        """
        Cron job: Detecta citas concluidas hace +2h sin expediente y notifica al artista.
        Se ejecuta cada hora.
        """
        hace_dos_horas = fields.Datetime.now() - timedelta(hours=2)
        hace_cuatro_horas = fields.Datetime.now() - timedelta(hours=4)

        citas_pendientes = self.search([
            ('appointment_status', '=', 'concluded'),
            ('expediente_completado', '=', False),
            ('fin_real', '>=', hace_cuatro_horas),
            ('fin_real', '<=', hace_dos_horas),
        ])

        odoobot = self.env.ref('base.partner_root')

        for cita in citas_pendientes:
            # Usar real_employee_id del módulo base
            employee = cita.real_employee_id
            user = employee.user_id if employee else False
            partner_artista = user.partner_id if user else False

            if partner_artista:
                cliente = cita.manual_customer_id or cita.partner_id
                mensaje = _(
                    '<b>Expediente Pendiente</b><br/>'
                    'La cita de <b>%(clienta)s</b> del %(fecha)s concluyó hace más de 2 horas '
                    'y el expediente aún no está completo.<br/>'
                    '<a href="/odoo/calendar/%(id)s">Ver Cita</a>'
                ) % {
                    'clienta': cliente.name if cliente else 'Sin asignar',
                    'fecha': cita.start.strftime('%d/%m/%Y %H:%M') if cita.start else '',
                    'id': cita.id,
                }
                self.env['mail.message'].sudo().create({
                    'message_type': 'comment',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'author_id': odoobot.id,
                    'partner_ids': [(4, partner_artista.id)],
                    'body': mensaje,
                    'res_id': cita.id,
                    'model': 'calendar.event',
                })
                _logger.info(
                    'Alerta de expediente incompleto enviada a %s para la cita %s',
                    user.name, cita.id
                )
        return True

    # ─── OVERRIDE ─────────────────────────────────────────────────────────────

    def write(self, vals):
        """Proteger el campo expediente_completado de modificación manual."""
        if 'expediente_completado' in vals:
            if not self.env.su:
                raise ValidationError(
                    _('El campo "Expediente Completado" es de solo lectura. '
                      'Se actualiza automáticamente al concluir la cita correctamente.')
                )
        return super().write(vals)
