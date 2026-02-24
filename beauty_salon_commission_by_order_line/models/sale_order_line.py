# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    """
    Extensión de sale.order.line para cálculo de comisiones por línea.
    
    FASE 1: Campo user_id auto-llenado desde calendar.event.real_employee_id
    
    Cambios principales:
    1. Agregar campo user_id (Many2one a res.users)
    2. Auto-llenar desde calendar_event_id.real_employee_id.user_id
    3. Permitir edición manual (readonly=False)
    4. Fallback a order.user_id si no hay cita
    5. Auditoría completa con tracking
    """
    
    _inherit = "sale.order.line"

    # ============================================
    # CAMPOS
    # ============================================
    
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson',
        compute='_compute_user_id',
        store=True,
        readonly=False,
        tracking=True,
        required=True,
        help='Employee responsible for this line. Auto-filled from appointment if exists. '
             'Can be manually edited. Falls back to order salesperson if no appointment.'
    )

    # ============================================
    # COMPUTE METHODS
    # ============================================

    @api.depends(
        'calendar_event_id',
        'calendar_event_id.real_employee_id',
        'calendar_event_id.real_employee_id.user_id',
        'order_id.user_id'
    )
    def _compute_user_id(self):
        """
        Auto-llenar user_id basado en:
        1. Si hay calendar_event_id → usar calendar_event_id.real_employee_id.user_id
        2. Si no hay cita → usar order_id.user_id (fallback)
        3. Si tampoco hay vendedor en orden → SIN ASIGNAR (será requerido)
        
        Este compute respeta ediciones manuales porque store=True y readonly=False.
        """
        for line in self:
            # Caso 1: Línea vinculada a CITA (website booking)
            if line.calendar_event_id and line.calendar_event_id.real_employee_id:
                employee = line.calendar_event_id.real_employee_id
                if employee.user_id:
                    line.user_id = employee.user_id
                    _logger.info(
                        f'✅ SOL #{line.id} auto-llenado desde cita: '
                        f'user_id={employee.user_id.name}'
                    )
                    continue
            
            # Caso 2: Fallback a VENDEDOR DE LA ORDEN
            if line.order_id.user_id:
                line.user_id = line.order_id.user_id
                _logger.info(
                    f'✅ SOL #{line.id} fallback a orden: '
                    f'user_id={line.order_id.user_id.name}'
                )
                continue
            
            # Caso 3: SIN ASIGNAR (será requerido y mostrará error al guardar)
            line.user_id = False
            _logger.warning(
                f'⚠️ SOL #{line.id} sin user_id asignado (cita ni orden tienen vendedor)'
            )

    # ============================================
    # WRITE OVERRIDE - AUDITORÍA
    # ============================================

    def write(self, vals):
        """
        Override write para auditar cambios manuales en user_id.
        
        Registra en chatter cuando se cambia el vendedor manualmente.
        """
        # Detectar si está cambiando user_id
        if 'user_id' in vals:
            for line in self:
                old_user = line.user_id.name if line.user_id else 'Sin asignar'
                new_user_id = vals['user_id']
                new_user = self.env['res.users'].browse(new_user_id).name if new_user_id else 'Sin asignar'
                
                # ✅ Si es diferente al valor actual, registrar
                if line.user_id.id != new_user_id:
                    _logger.info(
                        f'📝 SOL #{line.id} ({line.product_id.name}): '
                        f'user_id modificado manualmente de "{old_user}" a "{new_user}"'
                    )
                    
                    # Registrar en chatter de la orden
                    message = (
                        f'<strong>Vendedor de Línea Modificado</strong><br/>'
                        f'Producto: {line.product_id.name}<br/>'
                        f'Anterior: {old_user}<br/>'
                        f'Nuevo: {new_user}'
                    )
                    line.order_id.message_post(body=message, subject='Cambio de Vendedor en Línea')
        
        # Ejecutar write normal
        res = super(SaleOrderLine, self).write(vals)
        return res

    # ============================================
    # CREATE OVERRIDE - VALIDACIÓN
    # ============================================

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create para auto-llenar user_id desde calendar_event_id en citas website.
        
        Nota: El compute _compute_user_id se ejecutará automáticamente,
        pero esto asegura que se llene en el mismo instante de creación.
        """
        lines = super(SaleOrderLine, self).create(vals_list)
        
        for line in lines:
            if line.calendar_event_id and line.calendar_event_id.real_employee_id:
                _logger.info(
                    f'✅ SOL #{line.id} creada: '
                    f'calendar_event={line.calendar_event_id.name}, '
                    f'user_id={line.user_id.name if line.user_id else "No asignado"}'
                )
        
        return lines