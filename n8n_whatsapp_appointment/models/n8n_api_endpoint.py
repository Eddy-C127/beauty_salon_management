# -*- coding: utf-8 -*-
from odoo import fields, models


class N8nApiEndpoint(models.Model):
    """
    Catálogo de endpoints REST que Odoo expone para n8n.
    Los registros se crean via data XML (no por el usuario).
    Sirve como documentación viva dentro de Odoo.
    """
    _name = 'n8n.api.endpoint'
    _description = 'Endpoints API para n8n'
    _order = 'sequence asc, name asc'
    _rec_name = 'name'

    sequence = fields.Integer(default=10)

    name = fields.Char(
        string='Nombre',
        required=True,
    )
    http_method = fields.Selection(
        selection=[('POST', 'POST'), ('GET', 'GET')],
        string='Método',
        required=True,
        default='POST',
    )
    path = fields.Char(
        string='Ruta',
        required=True,
        help='Ruta relativa del endpoint, ej: /api/n8n/appointment/slots',
    )
    description = fields.Text(
        string='¿Qué hace?',
    )
    direction = fields.Selection(
        selection=[
            ('inbound', 'Entrante → n8n llama a Odoo'),
            ('outbound', 'Saliente → Odoo llama a n8n'),
        ],
        string='Dirección',
        required=True,
        default='inbound',
    )
    n8n_node_type = fields.Char(
        string='Nodo n8n',
        help='Tipo de nodo a usar en n8n para este endpoint',
    )
    request_params = fields.Text(
        string='Parámetros de entrada (JSON-RPC params)',
        help='Campos que se envían dentro de "params" del envelope JSON-RPC',
    )
    response_fields = fields.Text(
        string='Campos de respuesta',
        help='Campos devueltos en result cuando el status es ok',
    )
    n8n_config_guide = fields.Text(
        string='Cómo configurar en n8n',
        help='Instrucciones paso a paso para configurar el nodo en n8n',
    )
    body_example = fields.Text(
        string='Ejemplo de body',
    )
    active = fields.Boolean(default=True)
