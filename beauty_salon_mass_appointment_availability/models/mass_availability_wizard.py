# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class MassAvailabilityWizard(models.TransientModel):
    """
    Asistente para gestión masiva de disponibilidad de citas.
    
    Permite cerrar o abrir la disponibilidad de appointment types de forma masiva
    usando los campos nativos de Odoo (category_time_display, start/end_datetime).
    """
    _name = 'mass.availability.wizard'
    _description = 'Asistente de Gestión de Disponibilidad de Citas'

    # ============================================
    # CAMPOS
    # ============================================
    
    action_type = fields.Selection(
        selection=[
            ('close', 'Cerrar Disponibilidad'),
            ('open', 'Abrir Disponibilidad'),
        ],
        string='Acción',
        required=True,
        default='close',
        help='Cerrar: Bloquea las citas en un período específico.\n'
             'Abrir: Restaura la disponibilidad normal de citas.'
    )
    
    selection_mode = fields.Selection(
        selection=[
            ('mass', 'Masivo (por Sucursal/Categoría)'),
            ('individual', 'Individual (por Tipo de Cita)'),
        ],
        string='Modo de Selección',
        required=True,
        default='mass',
        help='Masivo: Selecciona appointment types automáticamente.\n'
             'Individual: Permite selección manual de appointment types.'
    )
    
    # Campos para modo MASIVO
    branch_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        string='Sucursales',
        help='Sucursales para filtrar tipos de cita. Si se deja vacío se aplica a TODAS las sucursales.'
    )
    
    # ✅ CAMBIO: Selection → Many2many
    appointment_category_ids = fields.Many2many(
        comodel_name='appointment.category',
        relation='wizard_appointment_category_rel',
        column1='wizard_id',
        column2='category_id',
        string='Categorías de Servicio',
        help='Categorías de servicio para filtrar tipos de cita. Si se deja vacío se aplica a TODAS las categorías.'
    )
    
    # Campo para modo INDIVIDUAL
    appointment_type_ids = fields.Many2many(
        comodel_name='appointment.type',
        string='Tipos de Cita',
        help='Tipos de cita a los que se aplicará el cambio de disponibilidad'
    )
    
    # Campos para CERRAR disponibilidad
    date_from = fields.Datetime(
        string='Desde',
        help='Fecha y hora de inicio del período de cierre'
    )
    
    date_to = fields.Datetime(
        string='Hasta',
        help='Fecha y hora de finalización del período de cierre'
    )
    
    close_reason = fields.Char(
        string='Motivo del Cierre',
        help='Motivo del cierre (ej: Vacaciones, Mantenimiento, Capacitación)'
    )
    
    # Campos para ABRIR disponibilidad
    open_availability_mode = fields.Selection(
        selection=[
            ('recurring', 'Disponible Ahora'),
            ('custom_range', 'Dentro de un Intervalo de Fechas'),
        ],
        string='Modo de Apertura',
        default='recurring',
        help='Recurring: Disponibilidad ilimitada con horarios configurados.\n'
             'Custom Range: Definir un período específico de disponibilidad.'
    )
    
    open_slot_ids_days = fields.Integer(
        string='Días en el Futuro',
        default=30,
        help='Número de días en el futuro que las citas estarán disponibles'
    )
    
    open_date_from = fields.Datetime(
        string='Disponible Desde',
        help='Fecha de inicio de disponibilidad (para modo intervalo)'
    )
    
    open_date_to = fields.Datetime(
        string='Disponible Hasta',
        help='Fecha de fin de disponibilidad (para modo intervalo)'
    )
    
    open_reason = fields.Char(
        string='Nota de Apertura',
        help='Nota opcional sobre la apertura de disponibilidad'
    )
    
    # Campo informativo
    appointment_count = fields.Integer(
        string='Tipos de Cita Afectados',
        compute='_compute_appointment_count',
        help='Número de tipos de cita que serán afectados'
    )

    # ============================================
    # CAMPOS COMPUTADOS
    # ============================================
    
    @api.depends('selection_mode', 'branch_ids', 'appointment_category_ids', 'appointment_type_ids')
    def _compute_appointment_count(self):
        """Calcula el número de appointment types que serán afectados."""
        for wizard in self:
            if wizard.selection_mode == 'mass':
                appointment_types = wizard._get_appointment_types_for_mass_mode()
                wizard.appointment_count = len(appointment_types)
            else:
                wizard.appointment_count = len(wizard.appointment_type_ids)

    # ============================================
    # ONCHANGES
    # ============================================
    
    @api.onchange('action_type')
    def _onchange_action_type(self):
        """Limpia campos cuando cambia el tipo de acción."""
        if self.action_type == 'close':
            self.open_availability_mode = 'recurring'
            self.open_reason = False
        else:
            self.date_from = False
            self.date_to = False
            self.close_reason = False

    # ============================================
    # VALIDACIONES
    # ============================================
    
    @api.constrains('action_type', 'date_from', 'date_to')
    def _check_dates_for_close(self):
        """Valida fechas cuando la acción es CERRAR."""
        for wizard in self:
            if wizard.action_type == 'close':
                if not wizard.date_from or not wizard.date_to:
                    raise ValidationError(
                        _('Debe especificar fecha de inicio y fin para cerrar la disponibilidad.')
                    )
                if wizard.date_from >= wizard.date_to:
                    raise ValidationError(
                        _('La fecha de inicio debe ser anterior a la fecha de fin.')
                    )
    
    @api.constrains('action_type', 'open_availability_mode', 'open_date_from', 'open_date_to')
    def _check_dates_for_open_custom_range(self):
        """Valida fechas cuando se abre con intervalo personalizado."""
        for wizard in self:
            if wizard.action_type == 'open' and wizard.open_availability_mode == 'custom_range':
                if not wizard.open_date_from or not wizard.open_date_to:
                    raise ValidationError(
                        _('Debe especificar fecha de inicio y fin para el intervalo de disponibilidad.')
                    )
                if wizard.open_date_from >= wizard.open_date_to:
                    raise ValidationError(
                        _('La fecha de inicio debe ser anterior a la fecha de fin.')
                    )

    @api.constrains('selection_mode', 'appointment_category_ids')
    def _check_mass_mode_fields(self):
        """Valida campos en modo masivo."""
        for wizard in self:
            # ✅ CAMBIO: Ahora las categorías también son opcionales (vacío = TODAS)
            # Solo validamos que esté en modo masivo
            pass  # Sin validaciones requeridas, todo es opcional

    @api.constrains('selection_mode', 'appointment_type_ids')
    def _check_individual_mode_fields(self):
        """Valida campos en modo individual."""
        for wizard in self:
            if wizard.selection_mode == 'individual' and not wizard.appointment_type_ids:
                raise ValidationError(
                    _('Debe seleccionar al menos un tipo de cita en modo individual.')
                )

    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def _get_appointment_types_for_mass_mode(self):
        """
        Obtiene appointment types basándose en sucursales y categorías.
        
        Returns:
            recordset: Appointment types que cumplen los criterios
        """
        self.ensure_one()
        
        domain = []
        
        # ✅ Si hay sucursales seleccionadas, filtrar por ellas
        if self.branch_ids:
            domain.append(('branch_id', 'in', self.branch_ids.ids))
        
        # ✅ Si hay categorías seleccionadas, filtrar por ellas
        if self.appointment_category_ids:
            domain.append(('appointment_category_ids', 'in', self.appointment_category_ids.ids))
        
        appointment_types = self.env['appointment.type'].search(domain)
        
        branch_info = ', '.join(self.branch_ids.mapped('name')) if self.branch_ids else 'TODAS las sucursales'
        category_info = ', '.join(self.appointment_category_ids.mapped('name')) if self.appointment_category_ids else 'TODAS las categorías'
        
        _logger.info(
            f'Encontrados {len(appointment_types)} tipos de cita para '
            f'{branch_info} y {category_info}'
        )
        
        return appointment_types

    # ============================================
    # ACCIÓN PRINCIPAL
    # ============================================
    
    def action_apply_availability_change(self):
        """
        Aplica el cambio de disponibilidad a los appointment types seleccionados.
        
        Returns:
            dict: Acción con mensaje de confirmación
        """
        self.ensure_one()
        
        # Determinar appointment types según modo
        if self.selection_mode == 'mass':
            appointment_types = self._get_appointment_types_for_mass_mode()
        else:
            appointment_types = self.appointment_type_ids
        
        # Validar que haya appointment types
        if not appointment_types:
            raise UserError(_(
                'No se encontraron tipos de cita que cumplan los criterios seleccionados.'
            ))
        
        # Aplicar cambios según acción
        if self.action_type == 'close':
            self._close_availability(appointment_types)
            action_msg = 'cerrada'
            icon = '🔒'
        else:
            self._open_availability(appointment_types)
            action_msg = 'abierta'
            icon = '✅'
        
        # Preparar mensaje de confirmación
        message = self._prepare_confirmation_message(
            appointment_types, 
            action_msg, 
            icon
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Disponibilidad Actualizada'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _prepare_confirmation_message(self, appointment_types, action_msg, icon):
        """Prepara el mensaje de confirmación."""
        message = _(
            '%s Disponibilidad %s exitosamente\n\n'
            '✓ Tipos de cita actualizados: %s\n'
        ) % (icon, action_msg, len(appointment_types))
        
        # Agregar información de sucursales
        if self.selection_mode == 'mass':
            if self.branch_ids:
                branch_names = ', '.join(self.branch_ids.mapped('name'))
                message += _('\n🏢 Sucursales: %s') % branch_names
            else:
                message += _('\n🏢 Sucursales: TODAS')
            
            # ✅ Agregar información de categorías
            if self.appointment_category_ids:
                category_names = ', '.join(self.appointment_category_ids.mapped('name'))
                message += _('\n📁 Categorías: %s') % category_names
            else:
                message += _('\n📁 Categorías: TODAS')
        
        # Agregar detalles según acción
        if self.action_type == 'close':
            message += _('\n📅 Período cerrado: %s - %s') % (
                self.date_from.strftime('%d/%m/%Y %H:%M'),
                self.date_to.strftime('%d/%m/%Y %H:%M')
            )
            if self.close_reason:
                message += _('\n📝 Motivo: %s') % self.close_reason
        else:
            if self.open_availability_mode == 'recurring':
                message += _('\n📅 Disponibilidad: Ilimitada (con horarios configurados)')
            else:
                message += _('\n📅 Disponible: %s - %s') % (
                    self.open_date_from.strftime('%d/%m/%Y %H:%M'),
                    self.open_date_to.strftime('%d/%m/%Y %H:%M')
                )
            if self.open_reason:
                message += _('\n📝 Nota: %s') % self.open_reason
        
        # Listar tipos afectados
        message += _('\n\n📋 Tipos de cita afectados:')
        for apt in appointment_types[:10]:
            message += f'\n  • {apt.name}'
        
        if len(appointment_types) > 10:
            message += f'\n  ... y {len(appointment_types) - 10} más'
        
        return message
    
    # ============================================
    # MÉTODOS DE APLICACIÓN
    # ============================================
    
    def _close_availability(self, appointment_types):
        """
        Cierra la disponibilidad de appointment types en un período.
        
        Args:
            appointment_types: Recordset de appointment.type a cerrar
        """
        for apt_type in appointment_types:
            try:
                # Actualizar campos nativos de Odoo
                apt_type.write({
                    'category_time_display': 'punctual_fields',
                    'start_datetime': self.date_from,
                    'end_datetime': self.date_to,
                    'is_manually_closed': True, 
                })
                
                # Registrar en chatter
                apt_type.log_availability_change(
                    action_type='close',
                    date_from=self.date_from,
                    date_to=self.date_to,
                    reason=self.close_reason
                )
                
            except Exception as e:
                _logger.error(
                    f'Error al cerrar disponibilidad para {apt_type.name}: {str(e)}'
                )
                raise UserError(_(
                    'Error al cerrar disponibilidad para %s: %s'
                ) % (apt_type.name, str(e)))
    
    def _open_availability(self, appointment_types):
        """
        Abre la disponibilidad de appointment types.
        
        Args:
            appointment_types: Recordset de appointment.type a abrir
        """
        for apt_type in appointment_types:
            try:
                if self.open_availability_mode == 'recurring':
                    # Disponibilidad ilimitada (recurring)
                    apt_type.write({
                        'category_time_display': 'recurring_fields',
                        'start_datetime': False,
                        'end_datetime': False,
                        'is_manually_closed': False,
                    })
                else:
                    # Disponibilidad en intervalo específico
                    apt_type.write({
                        'category_time_display': 'punctual_fields',
                        'start_datetime': self.open_date_from,
                        'end_datetime': self.open_date_to,
                        'is_manually_closed': False,
                    })
                
                # Registrar en chatter
                reason = self.open_reason or (
                    f'Disponibilidad configurada hasta {self.open_slot_ids_days} días en el futuro'
                    if self.open_availability_mode == 'recurring'
                    else f'Disponible del {self.open_date_from.strftime("%d/%m/%Y")} al {self.open_date_to.strftime("%d/%m/%Y")}'
                )
                
                apt_type.log_availability_change(
                    action_type='open',
                    reason=reason
                )
                
            except Exception as e:
                _logger.error(
                    f'Error al abrir disponibilidad para {apt_type.name}: {str(e)}'
                )
                raise UserError(_(
                    'Error al abrir disponibilidad para %s: %s'
                ) % (apt_type.name, str(e)))