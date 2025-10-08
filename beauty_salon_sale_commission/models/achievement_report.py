# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class SaleAchievementReport(models.Model):
    _inherit = "sale.commission.achievement.report"

    @api.model
    def _get_sale_rates(self):
        """Extender los tipos de rates para incluir los nuevos tipos"""
        rates = super()._get_sale_rates()
        # Agregar los nuevos tipos si no están ya incluidos
        new_rates = ['amount_sold_invoiced', 'qty_sold_invoiced']
        for rate in new_rates:
            if rate not in rates:
                rates.append(rate)
        return rates

    @api.model
    def _get_sale_rates_product(self):
        """Modificar el cálculo para incluir los nuevos tipos"""
        return """
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty +
            rules.amount_sold_invoiced_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_invoiced_rate * sol.product_uom_qty
        """

    def _sale_lines(self, users=None, teams=None):
        """
        Sobrescribir completamente el método para crear CTEs separados:
        - Uno para ventas normales (amount_sold, qty_sold)
        - Otro para ventas facturadas (amount_sold_invoiced, qty_sold_invoiced)
        """
        
        # CTE para reglas de ventas NORMALES (sin filtro invoice_status)
        sale_rules_normal = f"""
sale_rules_normal AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(['amount_sold', 'qty_sold'])}
        {self._select_rules()}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      {self._get_company_condition('scp')}
      AND scpa.type IN ('amount_sold', 'qty_sold')
    {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
)"""

        # CTE para reglas de ventas FACTURADAS (CON filtro invoice_status='invoiced')
        sale_rules_invoiced = f"""
sale_rules_invoiced AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(['amount_sold_invoiced', 'qty_sold_invoiced'])}
        {self._select_rules()}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      {self._get_company_condition('scp')}
      AND scpa.type IN ('amount_sold_invoiced', 'qty_sold_invoiced')
    {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
)"""

        # CTE para líneas de comisión por EQUIPO - Ventas NORMALES
        sale_lines_team_normal = f"""
sale_commission_lines_team_normal AS (
    SELECT
        MAX(rules.user_id),
        MAX(rules.team_id),
        rules.plan_id,
        SUM(
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty
        ) AS achieved,
        MAX(rules.currency_id),
        MAX(so.date_order) AS date,
        MAX(rules.company_id),
        {self._select_sales()}
    FROM sale_rules_normal rules
    {self._join_sales()}
    JOIN product_product pp ON sol.product_id = pp.id
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    WHERE rules.team_rule
      AND so.team_id = rules.team_id
    {'AND so.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
      AND sol.display_type IS NULL
      AND (so.date_order BETWEEN rules.date_from AND rules.date_to)
      AND so.state = 'sale'
      AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
      AND COALESCE(is_expense, false) = false
      AND COALESCE(is_downpayment, false) = false
      {self._get_company_condition('so')}
    GROUP BY so.id, rules.plan_id
)"""

        # CTE para líneas de comisión por USUARIO - Ventas NORMALES
        sale_lines_user_normal = f"""
sale_commission_lines_user_normal AS (
    SELECT
        MAX(rules.user_id),
        MAX(so.team_id),
        rules.plan_id,
        SUM(
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty
        ) AS achieved,
        MAX(rules.currency_id),
        MAX(so.date_order) AS date,
        MAX(rules.company_id),
        {self._select_sales()}
    FROM sale_rules_normal rules
    {self._join_sales()}
    JOIN product_product pp ON sol.product_id = pp.id
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    WHERE NOT rules.team_rule
      AND so.user_id = rules.user_id
    {'AND so.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
      AND sol.display_type IS NULL
      AND (so.date_order BETWEEN rules.date_from AND rules.date_to)
      AND so.state = 'sale'
      AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
      AND COALESCE(is_expense, false) = false
      AND COALESCE(is_downpayment, false) = false
      {self._get_company_condition('so')}
    GROUP BY so.id, rules.plan_id
)"""

        # CTE para líneas de comisión por EQUIPO - Ventas FACTURADAS
        # *** AQUÍ ESTÁ LA CLAVE: invoice_status = 'invoiced' ***
        sale_lines_team_invoiced = f"""
sale_commission_lines_team_invoiced AS (
    SELECT
        MAX(rules.user_id),
        MAX(rules.team_id),
        rules.plan_id,
        SUM(
            rules.amount_sold_invoiced_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_invoiced_rate * sol.product_uom_qty
        ) AS achieved,
        MAX(rules.currency_id),
        MAX(so.date_order) AS date,
        MAX(rules.company_id),
        {self._select_sales()}
    FROM sale_rules_invoiced rules
    {self._join_sales()}
    JOIN product_product pp ON sol.product_id = pp.id
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    WHERE rules.team_rule
      AND so.team_id = rules.team_id
    {'AND so.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
      AND sol.display_type IS NULL
      AND (so.date_order BETWEEN rules.date_from AND rules.date_to)
      AND so.state = 'sale'
      AND so.invoice_status = 'invoiced'
      AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
      AND COALESCE(is_expense, false) = false
      AND COALESCE(is_downpayment, false) = false
      {self._get_company_condition('so')}
    GROUP BY so.id, rules.plan_id
)"""

        # CTE para líneas de comisión por USUARIO - Ventas FACTURADAS
        # *** AQUÍ ESTÁ LA CLAVE: invoice_status = 'invoiced' ***
        sale_lines_user_invoiced = f"""
sale_commission_lines_user_invoiced AS (
    SELECT
        MAX(rules.user_id),
        MAX(so.team_id),
        rules.plan_id,
        SUM(
            rules.amount_sold_invoiced_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_invoiced_rate * sol.product_uom_qty
        ) AS achieved,
        MAX(rules.currency_id),
        MAX(so.date_order) AS date,
        MAX(rules.company_id),
        {self._select_sales()}
    FROM sale_rules_invoiced rules
    {self._join_sales()}
    JOIN product_product pp ON sol.product_id = pp.id
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    WHERE NOT rules.team_rule
      AND so.user_id = rules.user_id
    {'AND so.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
      AND sol.display_type IS NULL
      AND (so.date_order BETWEEN rules.date_from AND rules.date_to)
      AND so.state = 'sale'
      AND so.invoice_status = 'invoiced'
      AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
      AND COALESCE(is_expense, false) = false
      AND COALESCE(is_downpayment, false) = false
      {self._get_company_condition('so')}
    GROUP BY so.id, rules.plan_id
)"""

        # Unión de todas las líneas de comisión
        sale_commission_lines = """
sale_commission_lines AS (
    (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_team_normal)
    UNION ALL
    (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_user_normal)
    UNION ALL
    (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_team_invoiced)
    UNION ALL
    (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_user_invoiced)
)"""

        # Retornar el query completo
        return f"""
{sale_rules_normal},
{sale_rules_invoiced},
{sale_lines_team_normal},
{sale_lines_user_normal},
{sale_lines_team_invoiced},
{sale_lines_user_invoiced},
{sale_commission_lines}
""", 'sale_commission_lines'