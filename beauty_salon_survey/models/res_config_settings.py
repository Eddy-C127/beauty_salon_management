# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """
    Extensión de Settings para exponer configuración de encuestas.
    Los valores se guardan en el singleton pop.survey.config
    """
    _inherit = 'res.config.settings'
    
    # ============================================
    # UMBRALES DE CALIFICACIÓN
    # ============================================
    
    survey_negative_threshold = fields.Float(
        string='Umbral Negativo (<=)',
        help='Calificaciones menores o iguales a este valor son NEGATIVAS'
    )
    
    survey_positive_threshold = fields.Float(
        string='Umbral Positivo (>=)',
        help='Calificaciones mayores o iguales a este valor son POSITIVAS'
    )
    
    # ============================================
    # PENALIZACIÓN
    # ============================================
    
    survey_negative_penalty_type = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Importe Fijo'),
    ], string='Tipo de Penalización')
    
    survey_negative_commission_penalty = fields.Float(
        string='Penalización',
        help='Monto o porcentaje a restar por encuesta negativa'
    )
    
    # ============================================
    # BONUS (OPCIONAL)
    # ============================================
    
    survey_enable_positive_bonus = fields.Boolean(
        string='Activar Bonus por Positivas'
    )
    
    survey_positive_bonus_type = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Importe Fijo'),
    ], string='Tipo de Bonus')
    
    survey_positive_commission_bonus = fields.Float(
        string='Bonus',
        help='Monto o porcentaje a sumar por encuesta positiva'
    )
    
    # ============================================
    # GARANTÍAS
    # ============================================
    
    survey_warranty_deadline_days = fields.Integer(
        string='Días Límite para Garantía'
    )
    
    survey_warranty_approval_user_id = fields.Many2one(
        'res.users',
        string='Gerente (Aprobación)'
    )
    
    survey_supervisor_user_id = fields.Many2one(
        'res.users',
        string='Supervisor (Escalación)'
    )
    
    survey_auto_create_warranty = fields.Boolean(
        string='Crear Garantía Automáticamente'
    )
    
    # ============================================
    # ENCUESTAS
    # ============================================
    
    survey_default_service_survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta de Servicio'
    )
    
    survey_default_warranty_survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta de Garantía'
    )
    
    # ============================================
    # APLICACIÓN DE COMISIONES
    # ============================================
    
    survey_apply_only_when_invoiced = fields.Boolean(
        string='Aplicar Solo Cuando Esté Facturado'
    )
    
    # ============================================
    # MÉTODOS PARA PERSISTIR VALORES
    # ============================================
    
    @api.model
    def get_values(self):
        """
        Cargar valores desde el singleton pop.survey.config
        """
        res = super(ResConfigSettings, self).get_values()
        
        # Obtener configuración (crea si no existe)
        config = self.env['pop.survey.config'].get_config()
        
        # Cargar valores
        res.update({
            'survey_negative_threshold': config.negative_threshold,
            'survey_positive_threshold': config.positive_threshold,
            'survey_negative_penalty_type': config.negative_penalty_type,
            'survey_negative_commission_penalty': config.negative_commission_penalty,
            'survey_enable_positive_bonus': config.enable_positive_bonus,
            'survey_positive_bonus_type': config.positive_bonus_type,
            'survey_positive_commission_bonus': config.positive_commission_bonus,
            'survey_warranty_deadline_days': config.warranty_deadline_days,
            'survey_warranty_approval_user_id': config.warranty_approval_user_id.id,
            'survey_supervisor_user_id': config.supervisor_user_id.id,
            'survey_auto_create_warranty': config.auto_create_warranty,
            'survey_default_service_survey_id': config.default_service_survey_id.id,
            'survey_default_warranty_survey_id': config.default_warranty_survey_id.id,
            'survey_apply_only_when_invoiced': config.apply_only_when_invoiced,
        })
        
        return res
    
    def set_values(self):
        """
        Guardar valores en el singleton pop.survey.config
        """
        super(ResConfigSettings, self).set_values()
        
        # Obtener configuración (crea si no existe)
        config = self.env['pop.survey.config'].get_config()
        
        # Guardar valores
        config.write({
            'negative_threshold': self.survey_negative_threshold,
            'positive_threshold': self.survey_positive_threshold,
            'negative_penalty_type': self.survey_negative_penalty_type,
            'negative_commission_penalty': self.survey_negative_commission_penalty,
            'enable_positive_bonus': self.survey_enable_positive_bonus,
            'positive_bonus_type': self.survey_positive_bonus_type,
            'positive_commission_bonus': self.survey_positive_commission_bonus,
            'warranty_deadline_days': self.survey_warranty_deadline_days,
            'warranty_approval_user_id': self.survey_warranty_approval_user_id.id,
            'supervisor_user_id': self.survey_supervisor_user_id.id,
            'auto_create_warranty': self.survey_auto_create_warranty,
            'default_service_survey_id': self.survey_default_service_survey_id.id,
            'default_warranty_survey_id': self.survey_default_warranty_survey_id.id,
            'apply_only_when_invoiced': self.survey_apply_only_when_invoiced,
        })