# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    """
    Extensión de survey.user_input para vincular con citas
    """
    _inherit = 'survey.user_input'
    
    # ============================================
    # CAMPO DE RELACIÓN CON CITA
    # ============================================
    
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Cita Relacionada',
        ondelete='set null',
        index=True,
        help='Cita de beauty salon que generó esta encuesta'
    )
    
    # ============================================
    # HOOK PARA CLASIFICACIÓN AUTOMÁTICA
    # ============================================
    
    def _mark_done(self):
        """
        Override del método que marca una encuesta como completada.
        Aquí clasificamos y actualizamos la cita automáticamente.
        """
        res = super(SurveyUserInput, self)._mark_done()
        
        # Para cada respuesta completada
        for user_input in self:
            # Buscar cita vinculada directamente
            if user_input.calendar_event_id:
                user_input.calendar_event_id._process_survey_response()
            else:
                # Fallback: buscar por survey_response_id
                appointment = self.env['calendar.event'].search([
                    ('survey_response_id', '=', user_input.id)
                ], limit=1)
                
                if appointment:
                    appointment._process_survey_response()
                else:
                    _logger.info(f'No se encontró cita vinculada para user_input {user_input.id}')
        
        return res