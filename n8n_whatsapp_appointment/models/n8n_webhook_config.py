# -*- coding: utf-8 -*-
from odoo import fields, models


class N8nWebhookConfig(models.Model):
    _name = 'n8n.webhook.config'
    _description = 'Configuración de Webhooks Salientes a n8n'
    _order = 'name asc'

    name = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre descriptivo para identificar este webhook (ej: "Confirmar Pago WhatsApp").',
    )
    webhook_url = fields.Char(
        string='URL del Webhook',
        required=True,
        help='URL del endpoint en n8n al que Odoo enviará las notificaciones.',
    )
    auth_token = fields.Char(
        string='Token de Autenticación',
        help='Token Bearer opcional para autenticar las llamadas salientes hacia n8n.',
        groups='base.group_system',
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
    )
