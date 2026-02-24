# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SaleAchievementReport(models.Model):
    _inherit = "sale.commission.achievement.report"

    @api.model
    def _get_sale_rates(self):
        rates = super()._get_sale_rates()
        new_rates = ['amount_sold_invoiced', 'qty_sold_invoiced']
        for rate in new_rates:
            if rate not in rates:
                rates.append(rate)
        return rates

    def _sale_lines(self, users=None, teams=None):
        """
        Override para soportar comisiones por línea cuando enable_line_commission=True
        """
        parent_query, cte_name = super()._sale_lines(users=users, teams=teams)
        
        # Detectar si algún achievement tiene enable_line_commission = True
        line_commission_enabled = False
        try:
            achievements = self.env['sale.commission.plan.achievement'].search([
                ('enable_line_commission', '=', True)
            ], limit=1)
            line_commission_enabled = bool(achievements)
        except:
            pass
        
        if not line_commission_enabled:
            return parent_query, cte_name
        
        # Modificar el query para usar sol.user_id en lugar de so.user_id
        # Cambiar GROUP BY so.id → GROUP BY sol.id, so.id
        modified_query = parent_query.replace(
            'GROUP BY so.id, rules.plan_id',
            'GROUP BY sol.id, so.id, rules.plan_id, sol.user_id'
        )
        
        # Cambiar la condición del usuario: so.user_id → sol.user_id
        modified_query = modified_query.replace(
            'WHERE rules.team_rule\n      AND so.team_id = rules.team_id',
            'WHERE rules.team_rule\n      AND so.team_id = rules.team_id'
        )
        
        # Cambiar para usuarios no team
        modified_query = modified_query.replace(
            'WHERE NOT rules.team_rule\n      AND so.user_id = rules.user_id',
            'WHERE NOT rules.team_rule\n      AND sol.user_id = rules.user_id'
        )
        
        _logger.info(f'✅ Commission per line ENABLED - Using sol.user_id')
        
        return modified_query, cte_name