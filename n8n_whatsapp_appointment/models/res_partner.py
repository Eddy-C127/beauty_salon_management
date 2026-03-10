# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    manychat_subscriber_id = fields.Char(
        string='ManyChat Subscriber ID',
        copy=False,
        index=True,
        help='ID del suscriptor en ManyChat (Instagram). Se asigna automáticamente al vincularse via n8n.',
    )
    instagram_name = fields.Char(
        string='Nombre Instagram',
        copy=False,
        help='Nombre de pantalla en Instagram (username o nombre completo de ManyChat).',
    )
    ig_session_state = fields.Char(
        string='Estado sesión Instagram',
        copy=False,
        help='Estado temporal de la sesión de Instagram. "pending_phone" = esperando que el cliente proporcione su teléfono.',
    )

    _sql_constraints = [
        (
            'manychat_subscriber_id_unique',
            'UNIQUE(manychat_subscriber_id)',
            'Este ManyChat Subscriber ID ya está vinculado a otro contacto.',
        ),
    ]
