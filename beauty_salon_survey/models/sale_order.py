# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ============================================
    # CAMPOS RELACIONADOS DESDE CITA
    # IMPORTANTE: Usamos related para evitar duplicación
    # ============================================
    
    survey_id = fields.Many2one(
        related='calendar_event_id.survey_id',
        string='Encuesta',
        store=True,
        readonly=True,
        help='Encuesta asignada a la cita'
    )
    
    survey_response_id = fields.Many2one(
        related='calendar_event_id.survey_response_id',
        string='Respuesta de Encuesta',
        store=True,
        readonly=True,
        help='Respuesta del cliente a la encuesta'
    )
    
    survey_score = fields.Float(
        related='calendar_event_id.survey_score',
        string='Calificación',
        store=True,
        readonly=True,
        help='Score obtenido en la encuesta (1-5)'
    )
    
    survey_status = fields.Selection(
        related='calendar_event_id.survey_status',
        string='Estado Encuesta',
        store=True,
        readonly=True
    )
    
    survey_comments = fields.Text(
        related='calendar_event_id.survey_comments',
        string='Comentarios',
        readonly=True
    )
    
    # ============================================
    # CAMPOS DE AJUSTE DE COMISIÓN POR ENCUESTA
    # IMPORTANTE: En esta iteración solo definimos los campos
    # La lógica de cálculo se implementará en Iteración 5
    # ============================================
    
    survey_commission_adjustment = fields.Monetary(
        string='Ajuste por Encuesta',
        currency_field='currency_id',
        readonly=True,
        copy=False,
        help='Monto de ajuste (positivo o negativo) por resultado de encuesta. '
             'Solo se aplica cuando invoice_status=invoiced. '
             'Se calculará automáticamente en iteraciones futuras.'
    )
    
    survey_commission_adjustment_type = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Importe Fijo'),
    ], string='Tipo de Ajuste', 
       readonly=True,
       copy=False,
       help='Tipo de ajuste aplicado por la encuesta')
    
    # ============================================
    # MÉTODOS AUXILIARES (Sin lógica todavía)
    # ============================================
    
    def _get_survey_result_badge(self):
        """
        Retorna badge HTML para mostrar resultado de encuesta.
        Útil para reportes y vistas.
        
        Returns:
            str: HTML badge
        """
        self.ensure_one()
        
        if self.survey_status == 'positive':
            return '<span class="badge badge-success">Positiva ⭐</span>'
        elif self.survey_status == 'negative':
            return '<span class="badge badge-danger">Negativa ⚠️</span>'
        elif self.survey_status == 'completed':
            return '<span class="badge badge-info">Completada</span>'
        elif self.survey_status == 'sent':
            return '<span class="badge badge-warning">Enviada</span>'
        elif self.survey_status == 'pending':
            return '<span class="badge badge-secondary">Pendiente</span>'
        else:
            return '<span class="badge badge-light">Sin encuesta</span>'