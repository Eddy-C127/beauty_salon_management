# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class AppointmentType(models.Model):
    """
    Extensión del modelo appointment.type para gestión de disponibilidad.
    
    Agrega:
    - Campo de categorías de servicio (Many2many)
    - Campo de estado de disponibilidad (visible para usuarios)
    - Métodos para registro en chatter
    """
    _inherit = 'appointment.type'

    # ============================================
    # CAMPOS
    # ============================================
    
    # ✅ CAMBIO: Selection → Many2many
    appointment_category_ids = fields.Many2many(
        comodel_name='appointment.category',
        relation='appointment_type_category_rel',
        column1='appointment_type_id',
        column2='category_id',
        string='Categorías de Servicio',
        help='Categorías de servicio asociadas a este tipo de cita',
        tracking=True,
    )
    
    availability_status = fields.Text(
        string='Estado de Disponibilidad',
        compute='_compute_availability_status',
        store=True,
        help='Muestra el estado actual de disponibilidad de este tipo de cita.'
    )

    # ============================================
    # CAMPOS COMPUTADOS
    # ============================================
    
    @api.depends('category_time_display', 'start_datetime', 'end_datetime', 'slot_ids')
    def _compute_availability_status(self):
        """
        Calcula un mensaje legible del estado de disponibilidad.
        
        Muestra si la agenda está:
        - Abierta (disponible ahora)
        - Cerrada en un período específico
        - Configurada con horarios recurrentes
        """
        for appointment in self:
            if appointment.category_time_display == 'punctual_fields':
                # Agenda cerrada/limitada a un período
                if appointment.start_datetime and appointment.end_datetime:
                    status = f"🔒 CERRADA del {appointment.start_datetime.strftime('%d/%m/%Y %H:%M')} al {appointment.end_datetime.strftime('%d/%m/%Y %H:%M')}"
                else:
                    status = "⚠️ Configuración de período incompleta"
            else:
                # Agenda abierta con disponibilidad recurrente
                if appointment.slot_ids:
                    slot_count = len(appointment.slot_ids)
                    status = f"✅ ABIERTA - {slot_count} horario(s) configurado(s)"
                else:
                    status = "✅ ABIERTA - Disponibilidad ilimitada"
            
            appointment.availability_status = status

    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def log_availability_change(self, action_type, date_from=None, date_to=None, reason=None):
        """
        Registra cambios de disponibilidad en el chatter.
        
        Args:
            action_type: 'close' o 'open'
            date_from: Fecha de inicio (solo para close)
            date_to: Fecha de fin (solo para close)
            reason: Motivo del cambio (opcional)
        """
        self.ensure_one()
        
        if action_type == 'close':
            message = f"""
                <p><strong>🔒 Disponibilidad Cerrada</strong></p>
                <ul>
                    <li><strong>Período:</strong> {date_from.strftime('%d/%m/%Y %H:%M')} - {date_to.strftime('%d/%m/%Y %H:%M')}</li>
                    {f'<li><strong>Motivo:</strong> {reason}</li>' if reason else ''}
                    <li><strong>Estado:</strong> Las citas están bloqueadas en este período</li>
                </ul>
            """
        else:  # open
            message = f"""
                <p><strong>✅ Disponibilidad Abierta</strong></p>
                <ul>
                    <li><strong>Estado:</strong> Las citas están disponibles según configuración normal</li>
                    {f'<li><strong>Nota:</strong> {reason}</li>' if reason else ''}
                </ul>
            """
        
        self.message_post(
            body=message,
            subject=f'Cambio de Disponibilidad - {self.name}',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        _logger.info(
            f'Disponibilidad {"cerrada" if action_type == "close" else "abierta"} '
            f'para appointment type {self.name} (ID: {self.id})'
        )

    # ============================================
    # MÉTODOS SOBRESCRITOS
    # ============================================
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """
        Mejora búsqueda para incluir categorías en los resultados.
        """
        args = args or []
        
        if name:
            domain = ['|', 
                      ('name', operator, name),
                      ('appointment_category_ids.name', operator, name)]
            
            if args:
                domain = ['&'] + domain + args
            args = domain
        
        return super()._name_search(
            name=name, 
            args=args, 
            operator=operator, 
            limit=limit, 
            order=order
        )