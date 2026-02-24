# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WizardConcluirCita(models.TransientModel):
    """
    Wizard para concluir una cita en Pop Studio.
    Captura Foto Después, notas y recomendaciones obligatorias.
    Al confirmar: cierra la cita, marca expediente_completado=True.
    """
    _name = 'popstudio.wizard.concluir.cita'
    _description = 'Wizard: Concluir Cita Pop Studio'

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
    sesion_id = fields.Many2one(
        'popstudio.expediente.sesion',
        string='Sesión Activa',
        readonly=True,
    )

    # ─── FOTO DESPUÉS (OBLIGATORIA) ───────────────────────────────────────────

    foto_despues_ids = fields.Many2many(
        'ir.attachment',
        'wizard_concluir_foto_despues_rel',
        'wizard_id',
        'attachment_id',
        string='📸 Fotos Después del Servicio',
        required=True,
        help='⚠️ OBLIGATORIA para validación de comisiones. '
             'Sube las fotos del resultado final.',
    )

    # ─── NOTAS Y RECOMENDACIONES (OBLIGATORIAS) ───────────────────────────────

    notas_sesion = fields.Html(
        string='📝 Notas de la Sesión',
        required=True,
        help='Descripción del trabajo realizado, técnicas aplicadas, '
             'productos usados. Campo obligatorio para auditoría.',
    )
    recomendaciones_cuidado = fields.Html(
        string='💡 Recomendaciones de Cuidado Post-Tratamiento',
        help='Instrucciones para la clienta sobre cuidados en casa.',
    )
    productos_usados = fields.Text(
        string='🧴 Productos Utilizados',
        help='Lista de productos y marcas aplicados.',
    )
    reacciones_adversas = fields.Text(
        string='⚠️ Reacciones o Incidentes',
        help='Documenta cualquier reacción no esperada.',
    )

    # ─── CALIDAD Y SATISFACCIÓN ───────────────────────────────────────────────

    nivel_satisfaccion = fields.Selection(
        selection=[
            ('5', '⭐⭐⭐⭐⭐ Excelente'),
            ('4', '⭐⭐⭐⭐ Muy Buena'),
            ('3', '⭐⭐⭐ Buena'),
            ('2', '⭐⭐ Regular'),
            ('1', '⭐ Deficiente'),
        ],
        string='Satisfacción de la Clienta',
        required=True,
    )
    comentario_cliente = fields.Text(
        string='Comentario de la Clienta',
    )

    # ─── CONFIRMACIÓN ─────────────────────────────────────────────────────────

    confirmar_cierre = fields.Boolean(
        string='Confirmo que el servicio ha sido concluido correctamente y '
               'que la información registrada es verídica.',
        required=True,
        default=False,
    )

    # ─── CONSTRAINTS ──────────────────────────────────────────────────────────

    @api.constrains('foto_despues_ids')
    def _check_foto_despues_required(self):
        """OBLIGATORIO: No se puede concluir sin foto después."""
        for rec in self:
            if not rec.foto_despues_ids:
                raise ValidationError(
                    _('📸 Al menos una Foto Después es OBLIGATORIA para validar el expediente '
                      'y el cálculo de comisiones.\n\n'
                      'Esta es una política de auditoría de Pop Studio.')
                )

    @api.constrains('notas_sesion')
    def _check_notas_required(self):
        for rec in self:
            # Verificar que el HTML no esté vacío
            if not rec.notas_sesion or rec.notas_sesion.strip() in ('', '<p><br></p>', '<p></p>'):
                raise ValidationError(
                    _('📝 Las Notas de la Sesión son obligatorias. '
                      'Describe el trabajo realizado.')
                )

    # ─── ACCIÓN PRINCIPAL ─────────────────────────────────────────────────────

    def action_confirmar_conclusion(self):
        """
        Confirma la conclusión de la cita:
        1. Valida foto_despues y notas (OBLIGATORIOS)
        2. Actualiza el registro de sesión con todos los datos
        3. Marca la sesión como 'completada'
        4. Marca calendar_event.expediente_completado = True (via sudo)
        5. Registra fin_real en la cita
        """
        self.ensure_one()

        if not self.foto_despues_ids:
            raise ValidationError(
                _('📸 Al menos una Foto Después es OBLIGATORIA para concluir la cita.')
            )
        if not self.confirmar_cierre:
            raise ValidationError(
                _('⚠️ Debes confirmar que el servicio ha concluido correctamente.')
            )

        # Verificar que existe la sesión
        sesion = self.sesion_id
        if not sesion:
            # Si no existe, buscarla por la cita
            sesion = self.env['popstudio.expediente.sesion'].search([
                ('calendar_event_id', '=', self.calendar_event_id.id),
            ], limit=1)
            if not sesion:
                # Crear una sesión de emergencia si no existe
                sesion = self.env['popstudio.expediente.sesion'].create({
                    'partner_id': self.partner_id.id,
                    'calendar_event_id': self.calendar_event_id.id,
                    'fecha_sesion': self.calendar_event_id.inicio_real or fields.Datetime.now(),
                    'state': 'en_curso',
                })

        # Actualizar la sesión con todos los datos de conclusión
        sesion.sudo().write({
            'foto_despues_ids': [(6, 0, self.foto_despues_ids.ids)],
            'notas_internas': self.notas_sesion,
            'recomendaciones_cuidado': self.recomendaciones_cuidado,
            'productos_usados': self.productos_usados,
            'reacciones_adversas': self.reacciones_adversas,
            'nivel_satisfaccion': self.nivel_satisfaccion,
            'comentario_cliente': self.comentario_cliente,
            'state': 'completada',
        })

        # Marcar la cita como concluida — usar appointment_status del base
        self.calendar_event_id.sudo().write({
            'appointment_status': 'concluded',
            'expediente_completado': True,
            'fin_real': fields.Datetime.now(),
        })

        satisfaccion_dict = dict(self._fields['nivel_satisfaccion']._description_selection(self.env))
        
        # Log en el chatter de la cita
        self.calendar_event_id.message_post(
            body=_(
                '✅ <b>Cita Concluida</b><br/>'
                '📸 Foto Después: Adjuntas<br/>'
                '⭐ Satisfacción: %(satisfaccion)s<br/>'
                '📋 Expediente: <a href="/odoo/popstudio-expediente/%(sesion_id)s">Completo</a>'
            ) % {
                'satisfaccion': satisfaccion_dict.get(self.nivel_satisfaccion, ''),
                'sesion_id': sesion.id,
            },
            message_type='comment',
        )

        # Notificar en la sesión
        sesion.message_post(
            body=_(
                '✅ <b>Sesión Completada</b><br/>'
                'Artista: %(artista)s<br/>'
                'Satisfacción: %(sat)s<br/>'
                'Expediente verificado y listo para auditoría de comisiones.'
            ) % {
                'artista': (self.calendar_event_id.real_employee_id.user_id.name
                            if self.calendar_event_id.real_employee_id else 'N/A'),
                'sat': satisfaccion_dict.get(self.nivel_satisfaccion, ''),
            },
            message_type='comment',
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
