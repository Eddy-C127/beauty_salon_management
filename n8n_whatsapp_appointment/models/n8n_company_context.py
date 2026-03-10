# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class N8nCompanyContext(models.Model):
    """
    Contexto configurable de la empresa para el agente de IA (Valentina).
    Cada registro representa un 'tema' (topic_key) con su contenido textual.
    El agente consulta estos registros via /api/n8n/appointment/context.
    """
    _name = 'n8n.company.context'
    _description = 'Contexto de Empresa para Agente IA (n8n)'
    _order = 'sequence asc, name asc'
    _rec_name = 'name'

    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre descriptivo del tema (ej: "Política de Cancelaciones").',
    )
    topic_key = fields.Char(
        string='Clave del Tema',
        required=True,
        help=(
            'Identificador único que el agente de IA usa como parámetro. '
            'Solo minúsculas, sin espacios (ej: "cancelaciones", "horarios").'
        ),
    )
    content = fields.Text(
        string='Contenido',
        required=True,
        help='Texto completo que se devuelve al agente cuando consulta este tema.',
    )
    branch_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='n8n_company_context_warehouse_rel',
        column1='context_id',
        column2='warehouse_id',
        string='Sucursales',
        help=(
            'Sucursales (almacenes) a las que aplica este contexto. '
            'Si se deja vacío, aplica a todas las sucursales (contexto global).'
        ),
    )
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        (
            'topic_key_unique',
            'UNIQUE(topic_key)',
            'La clave del tema (topic_key) debe ser única.',
        ),
    ]

    @api.constrains('topic_key')
    def _check_topic_key_format(self):
        pattern = re.compile(r'^[a-z0-9_-]+$')
        for record in self:
            if not pattern.match(record.topic_key or ''):
                raise ValidationError(
                    f'La clave del tema "{record.topic_key}" no es válida. '
                    'Solo se permiten letras minúsculas, números, guiones (-) y guiones bajos (_).'
                )
