# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class AppointmentCategory(models.Model):
    """
    Categorías de servicios para appointment types.
    
    Permite clasificar los tipos de cita por categorías de servicio
    (ej: Pestañas, Cejas, Tattoo Lips, Tattoo Brows).
    """
    _name = 'appointment.category'
    _description = 'Categoría de Servicio de Citas'
    _order = 'sequence, name'

    # ============================================
    # CAMPOS
    # ============================================
    
    name = fields.Char(
        string='Nombre',
        required=True,
        translate=True,
        help='Nombre de la categoría de servicio'
    )
    
    code = fields.Char(
        string='Código',
        help='Código único para identificar la categoría'
    )
    
    description = fields.Text(
        string='Descripción',
        translate=True,
        help='Descripción de la categoría'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está desactivado, la categoría no estará disponible para nuevos appointment types'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de visualización'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color para visualización en la interfaz'
    )
    
    # Relación inversa
    appointment_type_ids = fields.Many2many(
        comodel_name='appointment.type',
        relation='appointment_type_category_rel',
        column1='category_id',
        column2='appointment_type_id',
        string='Tipos de Cita',
        help='Tipos de cita asociados a esta categoría'
    )
    
    appointment_type_count = fields.Integer(
        string='Número de Tipos de Cita',
        compute='_compute_appointment_type_count',
        store=True
    )

    # ============================================
    # RESTRICCIONES SQL
    # ============================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código de la categoría debe ser único.'),
    ]

    # ============================================
    # CAMPOS COMPUTADOS
    # ============================================
    
    @api.depends('appointment_type_ids')
    def _compute_appointment_type_count(self):
        """Calcula el número de appointment types asociados."""
        for category in self:
            category.appointment_type_count = len(category.appointment_type_ids)

    # ============================================
    # MÉTODOS
    # ============================================
    
    def name_get(self):
        """Personaliza el nombre mostrado."""
        result = []
        for category in self:
            name = category.name
            if category.code:
                name = f'[{category.code}] {name}'
            result.append((category.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Mejora búsqueda para incluir código."""
        args = args or []
        
        if name:
            domain = ['|', 
                      ('name', operator, name),
                      ('code', operator, name)]
            
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