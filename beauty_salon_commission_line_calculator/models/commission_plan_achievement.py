# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleCommissionPlanAchievement(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    enable_line_commission = fields.Boolean(
        string='Calculate Commission per Order Line',
        default=False,
        tracking=True,
        help='If enabled, commissions are calculated per order line using sol.user_id instead of so.user_id'
    )