# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PopSurveyConfig(models.Model):
    """
    Configuración singleton para el sistema de encuestas y garantías.
    Solo puede existir UN registro de configuración.
    """
    _name = 'pop.survey.config'
    _description = 'Configuración del Sistema de Encuestas y Garantías'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # ============================================
    # SINGLETON - Solo un registro permitido
    # ============================================
    
    name = fields.Char(
        string='Nombre',
        default='Configuración del Sistema de Encuestas',
        required=True,
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    # ============================================
    # UMBRALES DE CALIFICACIÓN
    # ============================================
    
    negative_threshold = fields.Float(
        string='Umbral Negativo',
        default=3.0,
        required=True,
        tracking=True,
        help='Calificaciones <= a este valor se consideran NEGATIVAS. '
             'Ejemplo: 3.0 significa que 1, 2 y 3 son negativas.'
    )
    
    positive_threshold = fields.Float(
        string='Umbral Positivo',
        default=4.0,
        required=True,
        tracking=True,
        help='Calificaciones >= a este valor se consideran POSITIVAS. '
             'Ejemplo: 4.0 significa que 4 y 5 son positivas.'
    )
    
    # ============================================
    # PENALIZACIÓN POR ENCUESTA NEGATIVA
    # ============================================
    
    negative_commission_penalty = fields.Float(
        string='Penalización por Encuesta Negativa',
        default=0.0,
        tracking=True,
        help='Monto o porcentaje a restar de la comisión cuando la encuesta es negativa.'
    )
    
    negative_penalty_type = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Importe Fijo'),
    ], string='Tipo de Penalización',
       default='percentage',
       required=True,
       tracking=True,
       help='Si es porcentaje, se aplica sobre el total de la venta. '
            'Si es importe fijo, se resta ese monto directo.')
    
    # ============================================
    # BONUS POR ENCUESTA POSITIVA (OPCIONAL)
    # ============================================
    
    enable_positive_bonus = fields.Boolean(
        string='Activar Bonus por Encuesta Positiva',
        default=False,
        tracking=True,
        help='Si está activo, se otorga un bonus cuando la encuesta es positiva.'
    )
    
    positive_commission_bonus = fields.Float(
        string='Bonus por Encuesta Positiva',
        default=0.0,
        tracking=True,
        help='Monto o porcentaje a sumar a la comisión cuando la encuesta es positiva.'
    )
    
    positive_bonus_type = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Importe Fijo'),
    ], string='Tipo de Bonus',
       default='percentage',
       tracking=True)
    
    # ============================================
    # CONFIGURACIÓN DE GARANTÍAS
    # ============================================
    
    warranty_deadline_days = fields.Integer(
        string='Días Límite para Garantía',
        default=7,
        required=True,
        tracking=True,
        help='Número de días que el cliente tiene para agendar su garantía '
             'después de que se aprueba.'
    )
    
    warranty_approval_user_id = fields.Many2one(
        'res.users',
        string='Gerente - Aprobación de Garantías',
        tracking=True,
        help='Usuario que recibe las actividades para aprobar garantías. '
             'Usualmente el gerente del salón.'
    )
    
    supervisor_user_id = fields.Many2one(
        'res.users',
        string='Supervisor - Escalación',
        tracking=True,
        help='Usuario que recibe tareas cuando una garantía también sale negativa. '
             'Para manejo directo con el cliente.'
    )
    
    auto_create_warranty = fields.Boolean(
        string='Crear Garantía Automáticamente',
        default=False,
        tracking=True,
        help='Si está activo, al recibir una encuesta negativa se crea la actividad '
             'de aprobación automáticamente. Si está desactivado, se hace manual.'
    )
    
    # ============================================
    # ENCUESTAS POR DEFECTO
    # ============================================
    
    default_service_survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta de Servicio (Por Defecto)',
        tracking=True,
        help='Encuesta que se enviará al concluir un servicio normal. '
             'Puede ser sobrescrita por tipo de cita.'
    )
    
    default_warranty_survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta de Garantía (Por Defecto)',
        tracking=True,
        help='Encuesta que se enviará al concluir una garantía.'
    )
    
    # ============================================
    # APLICACIÓN DE AJUSTES DE COMISIÓN
    # ============================================
    
    apply_only_when_invoiced = fields.Boolean(
        string='Aplicar Solo Cuando Esté Facturado',
        default=True,
        required=True,
        tracking=True,
        help='CRÍTICO: Si está activo, los ajustes de comisión solo se aplican '
             'cuando invoice_status=invoiced. Esto mantiene consistencia con '
             'el módulo beauty_salon_sale_commission.'
    )
    
    # ============================================
    # RESTRICCIONES Y VALIDACIONES
    # ============================================
    
    @api.constrains('negative_threshold', 'positive_threshold')
    def _check_thresholds(self):
        """Validar que los umbrales sean lógicos"""
        for record in self:
            if record.negative_threshold >= record.positive_threshold:
                raise ValidationError(
                    _('El umbral negativo (%.1f) debe ser menor que el umbral positivo (%.1f).') 
                    % (record.negative_threshold, record.positive_threshold)
                )
            
            if record.negative_threshold < 0 or record.negative_threshold > 5:
                raise ValidationError(
                    _('El umbral negativo debe estar entre 0 y 5.')
                )
            
            if record.positive_threshold < 0 or record.positive_threshold > 5:
                raise ValidationError(
                    _('El umbral positivo debe estar entre 0 y 5.')
                )
    
    @api.constrains('warranty_deadline_days')
    def _check_warranty_deadline(self):
        """Validar días de garantía"""
        for record in self:
            if record.warranty_deadline_days < 1:
                raise ValidationError(
                    _('Los días límite para garantía deben ser al menos 1.')
                )
            
            if record.warranty_deadline_days > 30:
                raise ValidationError(
                    _('Los días límite para garantía no pueden exceder 30 días.')
                )
    
    @api.constrains('negative_commission_penalty', 'positive_commission_bonus')
    def _check_penalties_bonus(self):
        """Validar que penalizaciones y bonos sean positivos"""
        for record in self:
            if record.negative_commission_penalty < 0:
                raise ValidationError(
                    _('La penalización no puede ser negativa.')
                )
            
            if record.positive_commission_bonus < 0:
                raise ValidationError(
                    _('El bonus no puede ser negativo.')
                )
            
            # Si es porcentaje, validar que no exceda 100%
            if record.negative_penalty_type == 'percentage' and record.negative_commission_penalty > 100:
                raise ValidationError(
                    _('El porcentaje de penalización no puede exceder 100%%.')
                )
            
            if record.positive_bonus_type == 'percentage' and record.positive_commission_bonus > 100:
                raise ValidationError(
                    _('El porcentaje de bonus no puede exceder 100%%.')
                )
    
    # ============================================
    # MÉTODOS DE SINGLETON
    # ============================================
    
    @api.model
    def get_config(self):
        """
        Obtener la configuración actual (singleton).
        Si no existe, la crea con valores por defecto.
        
        Returns:
            pop.survey.config: Registro de configuración
        """
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                'name': 'Configuración del Sistema de Encuestas',
            })
        return config
    
    @api.model
    def create(self, vals):
        """Asegurar que solo existe un registro"""
        if self.search_count([]) >= 1:
            raise ValidationError(
                _('Solo puede existir una configuración del sistema de encuestas. '
                  'Por favor edita la existente.')
            )
        return super().create(vals)
    
    def unlink(self):
        """Prevenir eliminación del registro de configuración"""
        raise ValidationError(
            _('No puedes eliminar la configuración del sistema. '
              'Si deseas desactivarlo, usa el campo "Activo".')
        )
    
    # ============================================
    # MÉTODOS HELPER PARA USO EN OTRAS ITERACIONES
    # ============================================
    
    def is_negative_survey(self, score):
        """
        Determina si una calificación es negativa.
        
        Args:
            score (float): Calificación de 1-5
            
        Returns:
            bool: True si es negativa
        """
        self.ensure_one()
        return score <= self.negative_threshold
    
    def is_positive_survey(self, score):
        """
        Determina si una calificación es positiva.
        
        Args:
            score (float): Calificación de 1-5
            
        Returns:
            bool: True si es positiva
        """
        self.ensure_one()
        return score >= self.positive_threshold
    
    def get_commission_adjustment(self, score, sale_amount):
        """
        Calcula el ajuste de comisión basado en la calificación.
        
        Args:
            score (float): Calificación de 1-5
            sale_amount (float): Monto total de la venta
            
        Returns:
            tuple: (adjustment_amount, adjustment_type)
        """
        self.ensure_one()
        
        # Encuesta negativa - penalización
        if self.is_negative_survey(score):
            if self.negative_penalty_type == 'percentage':
                adjustment = -(sale_amount * (self.negative_commission_penalty / 100.0))
            else:
                adjustment = -self.negative_commission_penalty
            
            return (adjustment, self.negative_penalty_type)
        
        # Encuesta positiva - bonus (si está habilitado)
        if self.is_positive_survey(score) and self.enable_positive_bonus:
            if self.positive_bonus_type == 'percentage':
                adjustment = sale_amount * (self.positive_commission_bonus / 100.0)
            else:
                adjustment = self.positive_commission_bonus
            
            return (adjustment, self.positive_bonus_type)
        
        # Encuesta neutral - sin ajuste
        return (0.0, False)