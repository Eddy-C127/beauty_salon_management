# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PopStudioExpedienteSesion(models.Model):
    """
    Registro individual de cada sesión/visita de una clienta.
    Cumple con NOM-004-SSA3-2012 para expedientes clínicos en estética.
    """
    _name = 'popstudio.expediente.sesion'
    _description = 'Expediente de Sesión - Pop Studio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_sesion desc, id desc'
    _rec_name = 'display_name'

    # ─── IDENTIFICACIÓN ───────────────────────────────────────────────────────

    partner_id = fields.Many2one(
        'res.partner',
        string='Clienta',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Cita Vinculada',
        ondelete='set null',
        tracking=True,
        index=True,
    )
    artista_id = fields.Many2one(
        'res.users',
        string='Artista / Estilista',
        tracking=True,
        index=True,
        default=lambda self: self.env.user,
    )
    fecha_sesion = fields.Datetime(
        string='Fecha de Sesión',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    display_name = fields.Char(
        string='Referencia',
        compute='_compute_display_name',
        store=True,
    )

    # ─── FOTOGRAFÍAS ──────────────────────────────────────────────────────────

    foto_antes_ids = fields.Many2many(
        'ir.attachment',
        'sesion_foto_antes_rel',
        'sesion_id',
        'attachment_id',
        string='Fotos Antes'
    )
    foto_despues_ids = fields.Many2many(
        'ir.attachment',
        'sesion_foto_despues_rel',
        'sesion_id',
        'attachment_id',
        string='Fotos Después'
    )

    # ─── SERVICIOS Y NOTAS ────────────────────────────────────────────────────

    servicio_realizado = fields.Char(
        string='Servicio Realizado',
        tracking=True,
    )
    productos_usados = fields.Text(
        string='Productos Utilizados',
        help='Lista de productos y marcas usadas en la sesión',
    )
    notas_internas = fields.Html(
        string='Notas Internas / Observaciones',
        help='Notas técnicas del procedimiento. Solo visibles por el staff.',
        sanitize_attributes=False,
    )
    recomendaciones_cuidado = fields.Html(
        string='Recomendaciones de Cuidado',
        help='Instrucciones post-tratamiento para la clienta.',
    )
    reacciones_adversas = fields.Text(
        string='Reacciones / Incidentes',
        help='Documenta cualquier reacción inesperada durante la sesión.',
    )

    # ─── SATISFACCIÓN ─────────────────────────────────────────────────────────

    nivel_satisfaccion = fields.Selection(
        selection=[
            ('5', '⭐⭐⭐⭐⭐ Excelente'),
            ('4', '⭐⭐⭐⭐ Muy Buena'),
            ('3', '⭐⭐⭐ Buena'),
            ('2', '⭐⭐ Regular'),
            ('1', '⭐ Deficiente'),
        ],
        string='Nivel de Satisfacción',
        tracking=True,
    )
    comentario_cliente = fields.Text(
        string='Comentario de la Clienta',
    )

    # ─── CONSENTIMIENTO ───────────────────────────────────────────────────────

    firma_consentimiento = fields.Binary(
        string='Firma de Consentimiento',
        attachment=True,
    )
    firma_consentimiento_fecha = fields.Datetime(
        string='Fecha de Firma',
    )
    consentimiento_aceptado = fields.Boolean(
        string='Consentimiento Firmado',
        default=False,
        tracking=True,
    )

    # ─── DATOS MÉDICOS (related desde partner) ──────────────────────────────

    partner_alergias = fields.Text(
        related='partner_id.alergias',
        string='Alergias Conocidas',
        readonly=True,
    )

    # ─── ESTADO ───────────────────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ('borrador', 'Borrador'),
            ('en_curso', 'En Curso'),
            ('completada', 'Completada'),
        ],
        string='Estado',
        default='borrador',
        tracking=True,
        readonly=True,
    )

    # ─── COMPUTED ─────────────────────────────────────────────────────────────

    @api.depends('partner_id', 'fecha_sesion')
    def _compute_display_name(self):
        for rec in self:
            if rec.partner_id and rec.fecha_sesion:
                fecha_str = rec.fecha_sesion.strftime('%d/%m/%Y')
                rec.display_name = f"{rec.partner_id.name} - {fecha_str}"
            else:
                rec.display_name = _('Nueva Sesión')

    # ─── CONSTRAINTS ──────────────────────────────────────────────────────────

    @api.constrains('foto_despues_ids', 'state')
    def _check_foto_despues_completada(self):
        for rec in self:
            if rec.state == 'completada' and not rec.foto_despues_ids:
                raise ValidationError(
                    _('⚠️ Para marcar la sesión como Completada, '
                      'es obligatorio adjuntar al menos una Foto Después.')
                )

    # ─── ACCIONES ─────────────────────────────────────────────────────────────

    def action_completar(self):
        """Marca la sesión como completada tras validación de foto."""
        self.ensure_one()
        if not self.foto_despues_ids:
            raise ValidationError(
                _('⚠️ Debes subir al menos una Foto Después antes de concluir la sesión.')
            )
        self.write({'state': 'completada'})
        # Actualizar el campo de auditoría en la cita
        if self.calendar_event_id:
            self.calendar_event_id.sudo().write({'expediente_completado': True})
        return True

    def action_ver_expediente_partner(self):
        """Acción para navegar al expediente completo de la clienta."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Expediente de {self.partner_id.name}',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
        }

    # ─── OVERRIDE ─────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'state' not in vals:
                vals['state'] = 'en_curso'
        return super().create(vals_list)
