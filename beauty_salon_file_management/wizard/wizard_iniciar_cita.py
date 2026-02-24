# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class WizardIniciarCita(models.TransientModel):
    """
    Wizard para iniciar una cita en Pop Studio.
    Captura Foto Antes, muestra alertas médicas y solicita firma de consentimiento.
    Diseñado Mobile-First con apertura de cámara automática en móvil.
    """
    _name = 'popstudio.wizard.iniciar.cita'
    _description = 'Wizard: Iniciar Cita Pop Studio'

    # ─── RELACIONES ───────────────────────────────────────────────────────────

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

    # ─── DATOS DEL EXPEDIENTE ─────────────────────────────────────────────────

    foto_antes_ids = fields.Many2many(
        'ir.attachment',
        'wizard_iniciar_foto_antes_rel',
        'wizard_id',
        'attachment_id',
        string='📸 Fotos Antes del Servicio',
        required=True,
        help='Sube las fotos del estado inicial.',
    )

    # ─── ALERTAS MÉDICAS (solo lectura, viene del partner) ────────────────────

    alergias_display = fields.Text(
        string='⚠️ Alergias Conocidas',
        compute='_compute_datos_medicos',
        readonly=True,
    )
    condiciones_medicas_display = fields.Text(
        string='🩺 Condiciones Médicas',
        compute='_compute_datos_medicos',
        readonly=True,
    )
    tiene_alertas_medicas = fields.Boolean(
        string='Tiene Alertas Médicas',
        compute='_compute_datos_medicos',
    )
    aviso_privacidad_ok = fields.Boolean(
        string='Aviso de Privacidad',
        compute='_compute_datos_medicos',
        readonly=True,
    )

    # ─── CONSENTIMIENTO ───────────────────────────────────────────────────────

    firma_consentimiento = fields.Binary(
        string='✍️ Firma de Consentimiento Informado',
        required=True,
        help='La clienta debe firmar en el recuadro para continuar.',
        attachment=False,
    )
    consentimiento_leido = fields.Boolean(
        string='La clienta confirma haber leído el aviso de privacidad y el '
               'consentimiento informado para el servicio solicitado.',
        required=True,
        default=False,
    )

    # ─── SERVICIO ─────────────────────────────────────────────────────────────

    servicio_nombre = fields.Char(
        string='Servicio a Realizar',
        compute='_compute_servicio',
        store=False,
    )
    artista_id = fields.Many2one(
        'res.users',
        string='Artista',
        default=lambda self: self.env.user,
    )

    # ─── COMPUTED ─────────────────────────────────────────────────────────────

    @api.depends('partner_id')
    def _compute_datos_medicos(self):
        for rec in self:
            partner = rec.partner_id
            rec.alergias_display = partner.alergias or ''
            rec.condiciones_medicas_display = partner.condiciones_medicas or ''
            rec.tiene_alertas_medicas = bool(partner.alergias or partner.condiciones_medicas)
            rec.aviso_privacidad_ok = partner.aviso_privacidad_aceptado

    @api.depends('calendar_event_id')
    def _compute_servicio(self):
        for rec in self:
            event = rec.calendar_event_id
            rec.servicio_nombre = (
                event.appointment_type_id.name if event.appointment_type_id
                else event.name or ''
            )

    # ─── CONSTRAINTS ──────────────────────────────────────────────────────────

    @api.constrains('consentimiento_leido')
    def _check_consentimiento(self):
        for rec in self:
            if not rec.consentimiento_leido:
                raise ValidationError(
                    _('⚠️ La clienta debe confirmar que ha leído el consentimiento informado '
                      'antes de iniciar la cita.')
                )

    @api.constrains('foto_antes_ids')
    def _check_foto_antes(self):
        for rec in self:
            if not rec.foto_antes_ids:
                raise ValidationError(
                    _('📸 Al menos una Foto Antes es obligatoria para iniciar la cita.')
                )

    # ─── ACCIÓN PRINCIPAL ─────────────────────────────────────────────────────

    def action_confirmar_inicio(self):
        """
        Confirma el inicio de la cita:
        1. Valida foto y firma
        2. Actualiza el estado de la cita a 'en_curso'
        3. Crea el registro de sesión en borrador con foto_antes_ids
        4. Registra inicio real
        """
        self.ensure_one()

        if not self.foto_antes_ids:
            raise ValidationError(_('📸 Al menos una Foto Antes es obligatoria.'))
        if not self.firma_consentimiento:
            raise ValidationError(_('✍️ La firma de consentimiento es obligatoria.'))
        if not self.consentimiento_leido:
            raise ValidationError(_('⚠️ Debes confirmar que la clienta aceptó el consentimiento.'))

        # Actualizar aviso de privacidad si no estaba marcado
        if not self.partner_id.aviso_privacidad_aceptado:
            self.partner_id.sudo().write({
                'aviso_privacidad_aceptado': True,
                'aviso_privacidad_fecha': fields.Datetime.now(),
            })

        # Crear sesión en estado 'en_curso'
        sesion = self.env['popstudio.expediente.sesion'].create({
            'partner_id': self.partner_id.id,
            'calendar_event_id': self.calendar_event_id.id,
            'artista_id': self.artista_id.id,
            'fecha_sesion': fields.Datetime.now(),
            'foto_antes_ids': [(6, 0, self.foto_antes_ids.ids)],
            'firma_consentimiento': self.firma_consentimiento,
            'firma_consentimiento_fecha': fields.Datetime.now(),
            'consentimiento_aceptado': True,
            'servicio_realizado': self.servicio_nombre,
            'state': 'en_curso',
        })

        # Actualizar la cita — usar appointment_status y real_employee_id del base
        event_vals = {
            'appointment_status': 'attended',
            'sesion_id': sesion.id,
            'inicio_real': fields.Datetime.now(),
        }
        # Sincronizar real_employee_id si el artista tiene employee vinculado
        if self.artista_id.employee_id:
            event_vals['real_employee_id'] = self.artista_id.employee_id.id
        self.calendar_event_id.sudo().write(event_vals)

        # Log en el chatter de la cita
        self.calendar_event_id.message_post(
            body=_(
                '🚀 <b>Cita Iniciada</b><br/>'
                'Artista: %(artista)s<br/>'
                'Consentimiento firmado por: %(clienta)s<br/>'
                'Sesión creada: <a href="/odoo/popstudio-expediente/%(sesion_id)s">%(sesion_ref)s</a>'
            ) % {
                'artista': self.artista_id.name,
                'clienta': self.partner_id.name,
                'sesion_id': sesion.id,
                'sesion_ref': sesion.display_name,
            },
            message_type='comment',
        )

        # Notificar en el expediente de la clienta
        sesion.message_post(
            body=_('✅ Sesión iniciada. Foto Antes capturada. Consentimiento firmado.'),
            message_type='comment',
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
