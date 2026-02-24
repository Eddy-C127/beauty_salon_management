# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WizardExpedienteRapido(models.TransientModel):
    """
    Wizard de llenado rápido del expediente clínico.

    Se abre ANTES del wizard_iniciar_cita cuando la clienta no tiene su
    expediente completo para el nivel de servicio solicitado.

    Muestra dinámicamente solo los campos que faltan — si todo está llenado,
    no muestra nada y procede directamente.

    Flujo:
        action_iniciar_cita() → (expediente incompleto) → WizardExpedienteRapido
            → Guardar y Continuar → WizardIniciarCita
            → Omitir (con motivo) → WizardIniciarCita  [log en chatter]
    """
    _name = 'popstudio.wizard.expediente.rapido'
    _description = 'Wizard: Completar Expediente Antes de la Cita'

    # ─── CONTEXTO DE LA CITA ──────────────────────────────────────────────────

    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Cita',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Clienta',
        required=True,
        readonly=True,
    )
    nivel_requerido = fields.Selection(
        selection=[
            ('basico', 'Básico'),
            ('intermedio', 'Intermedio'),
            ('clinico', 'Clínico'),
        ],
        string='Nivel Requerido por el Servicio',
        default='basico',
        readonly=True,
    )

    # ─── CAMPOS DEL EXPEDIENTE A COMPLETAR ───────────────────────────────────

    aviso_privacidad_aceptado = fields.Boolean(
        string='La clienta acepta el Aviso de Privacidad (LFPDPPP)',
        default=False,
    )
    alergias = fields.Text(
        string='Alergias Conocidas',
        placeholder='Escribe "Ninguna conocida" si no tiene alergias. Documenta cualquier alergia a productos, tintes, látex, etc.',
    )
    condiciones_medicas = fields.Text(
        string='Condiciones Médicas',
        placeholder='Escribe "Ninguna" si no aplica. Diabetes, embarazo, psoriasis, tratamientos activos...',
    )
    tipo_piel = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('seca', 'Seca'),
            ('grasa', 'Grasa'),
            ('mixta', 'Mixta'),
            ('sensible', 'Sensible'),
            ('madura', 'Madura / Anti-aging'),
        ],
        string='Tipo de Piel',
    )

    # ─── INDICADORES: QUÉ FALTA ───────────────────────────────────────────────

    falta_aviso = fields.Boolean(compute='_compute_faltas')
    falta_alergias = fields.Boolean(compute='_compute_faltas')
    falta_condiciones = fields.Boolean(compute='_compute_faltas')
    falta_tipo_piel = fields.Boolean(compute='_compute_faltas')
    hay_campos_faltantes = fields.Boolean(compute='_compute_faltas')

    # Nombre de la clienta para mostrar en el wizard
    partner_nombre = fields.Char(
        related='partner_id.name',
        string='Clienta',
        readonly=True,
    )
    servicio_nombre = fields.Char(
        string='Servicio',
        compute='_compute_servicio',
        readonly=True,
    )

    # ─── BYPASS ───────────────────────────────────────────────────────────────

    motivo_bypass = fields.Char(
        string='Motivo para Omitir',
        placeholder='Ej: Clienta con prisa, datos a completar después...',
    )

    # ─── COMPUTED ─────────────────────────────────────────────────────────────

    @api.depends('partner_id', 'nivel_requerido')
    def _compute_faltas(self):
        for rec in self:
            partner = rec.partner_id
            nivel = rec.nivel_requerido or 'basico'

            # Aviso: siempre requerido (LFPDPPP)
            rec.falta_aviso = not partner.aviso_privacidad_aceptado

            # Alergias: SIEMPRE requeridas — seguridad crítica en cualquier servicio
            rec.falta_alergias = not partner.alergias

            # Condiciones médicas: requerido para intermedio y clínico
            rec.falta_condiciones = (
                nivel in ('intermedio', 'clinico') and not partner.condiciones_medicas
            )
            # Tipo de piel: solo clínico
            rec.falta_tipo_piel = (nivel == 'clinico' and not partner.tipo_piel)

            rec.hay_campos_faltantes = any([
                rec.falta_aviso,
                rec.falta_alergias,
                rec.falta_condiciones,
                rec.falta_tipo_piel,
            ])

    @api.depends('calendar_event_id')
    def _compute_servicio(self):
        for rec in self:
            event = rec.calendar_event_id
            rec.servicio_nombre = (
                event.appointment_type_id.name if event and event.appointment_type_id
                else (event.name or '') if event else ''
            )

    # ─── ACCIONES ─────────────────────────────────────────────────────────────

    def action_guardar_y_continuar(self):
        """Guarda los datos del expediente al partner y abre el wizard de inicio de cita."""
        self.ensure_one()
        vals = {}

        if self.falta_aviso and self.aviso_privacidad_aceptado:
            vals['aviso_privacidad_aceptado'] = True
            vals['aviso_privacidad_fecha'] = fields.Datetime.now()
        if self.falta_alergias and self.alergias:
            vals['alergias'] = self.alergias
        if self.falta_condiciones and self.condiciones_medicas:
            vals['condiciones_medicas'] = self.condiciones_medicas
        if self.falta_tipo_piel and self.tipo_piel:
            vals['tipo_piel'] = self.tipo_piel

        if vals:
            self.partner_id.sudo().write(vals)
            _logger.info(
                'Expediente de %s actualizado desde wizard rápido: %s',
                self.partner_id.name, list(vals.keys())
            )

        # Verificar si aún falta el aviso (bloqueante)
        if not self.partner_id.aviso_privacidad_aceptado:
            raise UserError(_(
                'El Aviso de Privacidad es obligatorio (LFPDPPP).\n'
                'La clienta debe aceptarlo antes de continuar.'
            ))

        return self._abrir_wizard_iniciar()

    def action_omitir_expediente(self):
        """Omite el llenado del expediente y continúa a la cita. Registra en el chatter."""
        self.ensure_one()
        motivo = self.motivo_bypass or 'Sin especificar'

        # Log auditable en el chatter de la cita
        self.calendar_event_id.message_post(
            body=_(
                '⚠️ <b>Expediente Incompleto — Bypass activado</b><br/>'
                'Usuario: %(user)s<br/>'
                'Motivo: %(motivo)s<br/>'
                '<small class="text-muted">El expediente de %(clienta)s no estaba '
                'completo al momento de iniciar la cita.</small>'
            ) % {
                'user': self.env.user.name,
                'motivo': motivo,
                'clienta': self.partner_id.name,
            },
            message_type='comment',
        )
        _logger.warning(
            'Bypass de expediente activado por %s para cita %s. Motivo: %s',
            self.env.user.name, self.calendar_event_id.id, motivo
        )
        return self._abrir_wizard_iniciar()

    def _abrir_wizard_iniciar(self):
        """Retorna la acción para abrir el wizard de inicio de cita."""
        partner = self.partner_id
        event = self.calendar_event_id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Iniciar Cita'),
            'res_model': 'popstudio.wizard.iniciar.cita',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_calendar_event_id': event.id,
                'default_partner_id': partner.id if partner else False,
                'dialog_size': 'medium',
            },
        }
