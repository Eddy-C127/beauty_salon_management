# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """
    Extensión del modelo res.partner para agregar Expediente Clínico.
    Cumple con LFPDPPP (Ley Federal de Protección de Datos Personales en Posesión de los Particulares).
    """
    _inherit = 'res.partner'

    # ─── DATOS MÉDICOS BÁSICOS ────────────────────────────────────────────────

    ps_ocultar_datos_contacto = fields.Boolean(
        string='Modo Expediente',
        default=True,
        help='Oculta los datos estándar del contacto para mantener la interfaz enfocada en el expediente clínico.',
    )


    tipo_expediente = fields.Selection(
        selection=[
            ('facial', 'Facial'),
            ('capilar', 'Capilar'),
            ('corporal', 'Corporal'),
            ('otro', 'Otro / General'),
        ],
        string='Tipo de Expediente',
        default='otro',
        tracking=True,
        help='El tipo de expediente determina qué preguntas de salud se le realizarán a la clienta.'
    )

    # ─── PREGUNTAS DINÁMICAS: FACIAL ──────────────────────────────────────────
    
    facial_embarazada = fields.Selection(
        selection=[('si', 'Sí'), ('no', 'No')],
        string='¿Está embarazada o en lactancia?',
        tracking=True,
    )
    facial_problemas_piel = fields.Boolean(
        string='¿Tiene problemas en la piel? (Acné, rosácea, dermatitis, etc.)',
        tracking=True,
    )
    facial_otros = fields.Char(
        string='Otras condiciones faciales / tratamientos previos',
    )

    # ─── PREGUNTAS DINÁMICAS: CAPILAR ─────────────────────────────────────────

    capilar_sensibilidad = fields.Boolean(
        string='¿Sensibilidad extrema o alergias previas en cuero cabelludo?',
        tracking=True,
    )
    capilar_alopecia = fields.Boolean(
        string='¿Sufre de caída severa o alopecia?',
    )
    capilar_otros = fields.Char(
        string='Otras condiciones o tratamientos capilares previos',
    )

    # ─── DATOS GENERALES ──────────────────────────────────────────────────────


    alergias = fields.Text(
        string='Alergias Conocidas',
        help='⚠️ Documenta alergias a productos, materiales o medicamentos.',
        tracking=True,
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
        tracking=True,
    )
    condiciones_medicas = fields.Text(
        string='Condiciones Médicas',
        help='Condiciones relevantes para el servicio: diabetes, embarazo, '
             'tratamientos activos, psoriasis, etc.',
        tracking=True,
    )
    medicamentos_actuales = fields.Text(
        string='Medicamentos Actuales',
        help='Medicamentos que puedan interferir con los tratamientos.',
    )
    fecha_nacimiento = fields.Date(
        string='Fecha de Nacimiento',
    )
    notas_privadas_expediente = fields.Html(
        string='Notas Privadas del Expediente',
        help='Información confidencial solo visible por administradores.',
    )

    # ─── CONSENTIMIENTO Y PRIVACIDAD ──────────────────────────────────────────

    aviso_privacidad_aceptado = fields.Boolean(
        string='✅ Aviso de Privacidad Aceptado',
        default=False,
        tracking=True,
        help='LFPDPPP - El cliente acepta el tratamiento de sus datos personales '
             'y de salud conforme al aviso de privacidad de Pop Studio.',
    )
    aviso_privacidad_fecha = fields.Datetime(
        string='Fecha de Aceptación del Aviso',
        readonly=True,
    )
    aviso_privacidad_ip = fields.Char(
        string='IP de Aceptación',
        readonly=True,
        help='Registro de la IP desde donde se aceptó el aviso de privacidad.',
    )

    # ─── PROGRESO Y VIGENCIA DEL EXPEDIENTE ──────────────────────────────────

    expediente_progreso = fields.Float(
        compute='_compute_expediente_progreso',
        string='Completitud del Expediente (%)',
        help='Porcentaje de campos clínicos completados. 100% = expediente listo.',
    )
    expediente_listo = fields.Boolean(
        compute='_compute_expediente_progreso',
        store=True,
        string='Expediente Listo',
        help='True cuando todos los campos obligatorios del expediente están completos.',
    )
    expediente_fecha_actualizacion = fields.Datetime(
        string='Última Actualización del Expediente',
        readonly=True,
        help='Se actualiza automáticamente al modificar campos clínicos.',
    )
    expediente_vigente = fields.Boolean(
        compute='_compute_expediente_vigente',
        string='Expediente Vigente',
        help='False si el expediente tiene más de 12 meses sin actualizarse.',
    )

    # ─── HISTORIAL DE SESIONES ────────────────────────────────────────────────

    sesion_ids = fields.One2many(
        'popstudio.expediente.sesion',
        'partner_id',
        string='Historial de Sesiones',
    )
    sesion_count = fields.Integer(
        string='Total de Sesiones',
        compute='_compute_sesion_count',
        store=True,
    )
    ultima_sesion_fecha = fields.Datetime(
        string='Última Visita',
        compute='_compute_ultima_sesion',
        store=True,
    )
    proxima_visita_recomendada = fields.Date(
        string='Próxima Visita Recomendada',
        help='Fecha sugerida para el siguiente servicio.',
    )

    # ─── COMPUTED ─────────────────────────────────────────────────────────────

    @api.depends('sesion_ids')
    def _compute_sesion_count(self):
        for partner in self:
            partner.sesion_count = len(partner.sesion_ids)

    @api.depends('sesion_ids.fecha_sesion', 'sesion_ids.state')
    def _compute_ultima_sesion(self):
        for partner in self:
            sesiones_completadas = partner.sesion_ids.filtered(
                lambda s: s.state == 'completada'
            ).sorted('fecha_sesion', reverse=True)
            partner.ultima_sesion_fecha = (
                sesiones_completadas[0].fecha_sesion
                if sesiones_completadas else False
            )

    @api.depends(
        'aviso_privacidad_aceptado', 'alergias',
        'condiciones_medicas', 'tipo_piel',
    )
    def _compute_expediente_progreso(self):
        """
        Calcula el porcentaje de completitud del expediente clínico.

        Pesos:
        - Aviso de privacidad aceptado  → 40 pts  (obligatorio LFPDPPP)
        - Alergias documentadas          → 30 pts  (seguridad)
        - Condiciones médicas            → 20 pts  (seguridad)
        - Tipo de piel                   → 10 pts  (contextual)
        Total: 100 pts
        """
        for partner in self:
            pts = 0
            if partner.aviso_privacidad_aceptado:
                pts += 40
            if partner.alergias:
                pts += 30
            if partner.condiciones_medicas:
                pts += 20
            if partner.tipo_piel:
                pts += 10
            partner.expediente_progreso = float(pts)
            partner.expediente_listo = pts >= 100

    @api.depends('expediente_fecha_actualizacion')
    def _compute_expediente_vigente(self):
        """
        El expediente caduca si fue actualizado hace más de 12 meses.
        Si nunca se actualizó se considera no vigente solo si ya tiene datos.
        """
        from datetime import timedelta
        limite = fields.Datetime.now() - timedelta(days=365)
        for partner in self:
            if not partner.expediente_fecha_actualizacion:
                partner.expediente_vigente = not partner.expediente_listo
            else:
                partner.expediente_vigente = partner.expediente_fecha_actualizacion >= limite

    def _campos_expediente_requeridos_para_nivel(self, nivel):
        """Devuelve los nombres de campos requeridos según el nivel del servicio.

        Alergias es SIEMPRE requerida — seguridad crítica en cualquier servicio.
        """
        base = ['aviso_privacidad_aceptado', 'alergias']
        if nivel in ('intermedio', 'clinico'):
            base += ['condiciones_medicas']
        if nivel == 'clinico':
            base += ['tipo_piel']
        return base

    def expediente_completo_para_nivel(self, nivel='basico'):
        """Verifica si el expediente está completo para el nivel de servicio solicitado."""
        self.ensure_one()
        for campo in self._campos_expediente_requeridos_para_nivel(nivel):
            if not getattr(self, campo, False):
                return False
        return True

    # ─── ONCHANGE ─────────────────────────────────────────────────────────────

    @api.onchange('aviso_privacidad_aceptado')
    def _onchange_aviso_privacidad(self):
        if self.aviso_privacidad_aceptado and not self.aviso_privacidad_fecha:
            self.aviso_privacidad_fecha = fields.Datetime.now()

    # ─── CONSTRAINTS ──────────────────────────────────────────────────────────

    @api.constrains('aviso_privacidad_aceptado', 'alergias')
    def _check_aviso_privacidad(self):
        """
        Si se están guardando datos médicos, el aviso de privacidad debe estar aceptado.
        Cumplimiento LFPDPPP Art. 8 - Consentimiento expreso.
        """
        for rec in self:
            if rec.alergias and not rec.aviso_privacidad_aceptado:
                raise ValidationError(
                    _('⚠️ LFPDPPP: Para registrar datos médicos de la clienta, '
                      'es obligatorio que haya aceptado el Aviso de Privacidad.')
                )

    # ─── SMART BUTTON ACTIONS ─────────────────────────────────────────────────

    def action_ver_sesiones(self):
        """Navega al historial de sesiones de la clienta."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sesiones de {self.name}',
            'res_model': 'popstudio.expediente.sesion',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_partner_id': self.id,
            },
        }

    def action_nueva_sesion(self):
        """Crea una nueva sesión directamente desde el expediente."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva Sesión',
            'res_model': 'popstudio.expediente.sesion',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
            },
            'target': 'new',
        }

    # ─── OVERRIDE WRITE ───────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('aviso_privacidad_aceptado') and not vals.get('aviso_privacidad_fecha'):
                vals['aviso_privacidad_fecha'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('aviso_privacidad_aceptado') and not vals.get('aviso_privacidad_fecha'):
            vals['aviso_privacidad_fecha'] = fields.Datetime.now()
        # Registrar fecha de actualización si se tocó algún campo clínico
        _campos_clinicos = {
            'aviso_privacidad_aceptado', 'alergias', 'condiciones_medicas',
            'tipo_piel', 'tipo_expediente', 'medicamentos_actuales',
            'facial_embarazada', 'facial_problemas_piel',
            'capilar_sensibilidad', 'capilar_alopecia',
        }
        if _campos_clinicos & set(vals.keys()):
            vals.setdefault('expediente_fecha_actualizacion', fields.Datetime.now())
        return super().write(vals)
