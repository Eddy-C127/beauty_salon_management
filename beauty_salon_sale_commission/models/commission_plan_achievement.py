# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class CommissionPlanAchievement(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    type = fields.Selection(
        selection_add=[
            ('amount_sold_invoiced', 'Amount Sold - Fully Invoiced'),
            ('qty_sold_invoiced', 'Quantity Sold - Fully Invoiced'),
        ],
        ondelete={
            'amount_sold_invoiced': 'cascade',
            'qty_sold_invoiced': 'cascade',
        }
    )