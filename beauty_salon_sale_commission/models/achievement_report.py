# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class SaleAchievementReport(models.Model):
    _inherit = "sale.commission.achievement.report"

    date_fully_invoiced = fields.Datetime(
        string='Fully Invoiced Date',
        readonly=True,
        help='Date when the related order was fully invoiced'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        readonly=True,
        help='Customer from the related sale order or invoice'
    )

    @property
    def _table_query(self):
        """
        Sobrescribir el query principal (CONSUMIDOR)
        Aplica la corrección de TIMEZONE aquí.
        """
        users = self.env.context.get('commission_user_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()
        
        # 1. Obtener timezone
        tz = self.env.user.tz or self.env.company.partner_id.tz or 'America/Mexico_City'
        
        # 2. Definir la corrección
        corrected_date_check = f"(cl.date AT TIME ZONE 'UTC' AT TIME ZONE '{tz}')::date"
        
        return f"""
WITH {self._commission_lines_query(users=users, teams=teams)}
SELECT
    ROW_NUMBER() OVER (ORDER BY era.date_from DESC, era.id) AS id,
    era.id AS target_id,
    cl.user_id AS user_id,
    cl.team_id AS team_id,
    cl.achieved AS achieved,
    cl.currency_id AS currency_id,
    cl.company_id AS company_id,
    cl.plan_id,
    cl.related_res_model,
    cl.related_res_id,
    
    -- APLICAR CORRECCIÓN DE TZ AQUÍ --
    {corrected_date_check} AS date,

    cl.date_fully_invoiced AS date_fully_invoiced,
    cl.partner_id AS partner_id
FROM commission_lines cl
JOIN sale_commission_plan_target era
    ON cl.plan_id = era.plan_id
    -- Y APLICAR CORRECCIÓN DE TZ EN EL JOIN --
    AND {corrected_date_check} >= era.date_from
    AND {corrected_date_check} <= era.date_to
"""

    # ... (Los métodos _get_sale_rates, _select_sales, _select_invoices, _achievement_lines no cambian)...
    
    @api.model
    def _get_sale_rates(self):
        rates = super()._get_sale_rates()
        new_rates = ['amount_sold_invoiced', 'qty_sold_invoiced']
        for rate in new_rates:
            if rate not in rates:
                rates.append(rate)
        return rates

    @api.model
    def _get_sale_rates_product(self):
        # ESTE MÉTODO YA NO SE USARÁ, PERO LO DEJAMOS POR SI ACASO
        # LA LÓGICA SE MOVIÓ DIRECTAMENTE A _sale_lines
        return """
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty +
            rules.amount_sold_invoiced_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_invoiced_rate * sol.product_uom_qty
        """

    @api.model
    def _select_sales(self):
        base_select = super()._select_sales()
        return f"""
          {base_select},
          MAX(so.date_fully_invoiced) AS date_fully_invoiced,
          MAX(so.partner_id) AS partner_id
        """

    @api.model
    def _select_invoices(self):
        base_select = super()._select_invoices()
        return f"""
          {base_select},
          NULL::timestamp AS date_fully_invoiced,
          MAX(am.partner_id) AS partner_id
        """

    def _achievement_lines(self, users=None, teams=None):
        return f"""
achievement_commission_lines AS (
    SELECT
        sca.user_id,
        sca.team_id,
        scp.id AS plan_id,
        sca.currency_rate * sca.amount * scpa.rate AS achieved,
        scp.currency_id,
        
        -- DEJAR COMO sca.date (UTC NATIVO) --
        sca.date,
        
        scp.company_id,
        sca.id AS related_res_id,
        NULL::timestamp AS date_fully_invoiced,
        NULL::integer AS partner_id,
        'sale.commission.achievement' AS related_res_model
    FROM sale_commission_achievement sca
    JOIN sale_commission_plan scp ON scp.company_id = sca.company_id
    JOIN sale_commission_plan_achievement scpa ON scpa.plan_id = scp.id
    JOIN sale_commission_plan_user scpu ON scpu.plan_id = scp.id
    WHERE scp.active
      AND scp.state = 'approved'
      AND sca.type = scpa.type
      AND CASE
            WHEN scp.user_type = 'person' THEN sca.user_id = scpu.user_id
            ELSE sca.team_id = scp.team_id
      END
    {'AND sca.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    {'AND sca.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
)""", 'achievement_commission_lines'


    def _sale_lines(self, users=None, teams=None):
        """
        Sobrescribir el método (PROVEEDOR)
        ¡¡CORREGIDO: QUITAR LA CORRECCIÓN DE TIMEZONE DE AQUÍ!!
        Las fechas se devuelven en UTC.
        """
        
        # --- QUITAR 'tz' DE AQUÍ ---
        
        # CTE para reglas de ventas NORMALES
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

        # CTE para reglas de ventas FACTURADAS
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
        
        -- INICIO DE CORRECCIÓN: Usar solo rates normales
        SUM(
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty
        ) AS achieved,
        -- FIN DE CORRECCIÓN
        
        MAX(rules.currency_id),
        
        -- DEJAR FECHA EN UTC --
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
      
      -- CORRECCIÓN: COMPARAR FECHA EN UTC (usar ::date) --
      AND (so.date_order::date BETWEEN rules.date_from AND rules.date_to)
      
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

        -- INICIO DE CORRECCIÓN: Usar solo rates normales
        SUM(
            rules.amount_sold_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_rate * sol.product_uom_qty
        ) AS achieved,
        -- FIN DE CORRECCIÓN

        MAX(rules.currency_id),
        
        -- DEJAR FECHA EN UTC --
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
      
      -- CORRECCIÓN: COMPARAR FECHA EN UTC (usar ::date) --
      AND (so.date_order::date BETWEEN rules.date_from AND rules.date_to)

      AND so.state = 'sale'
      AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
      AND COALESCE(is_expense, false) = false
      AND COALESCE(is_downpayment, false) = false
      {self._get_company_condition('so')}
    GROUP BY so.id, rules.plan_id
)"""

        # CTE para líneas de comisión por EQUIPO - Ventas FACTURADAS
        sale_lines_team_invoiced = f"""
sale_commission_lines_team_invoiced AS (
    SELECT
        MAX(rules.user_id),
        MAX(rules.team_id),
        rules.plan_id,

        -- INICIO DE CORRECCIÓN: Usar solo rates facturados
        SUM(
            rules.amount_sold_invoiced_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_invoiced_rate * sol.product_uom_qty
        ) AS achieved,
        -- FIN DE CORRECCIÓN

        MAX(rules.currency_id),
        
        -- DEJAR FECHA EN UTC --
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
      
      -- CORRECCIÓN: COMPARAR FECHA EN UTC (usar ::date) --
      AND (so.date_order::date BETWEEN rules.date_from AND rules.date_to)
      
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
        sale_lines_user_invoiced = f"""
sale_commission_lines_user_invoiced AS (
    SELECT
        MAX(rules.user_id),
        MAX(so.team_id),
        rules.plan_id,

        -- INICIO DE CORRECCIÓN: Usar solo rates facturados
        SUM(
            rules.amount_sold_invoiced_rate * sol.price_subtotal / so.currency_rate +
            rules.qty_sold_invoiced_rate * sol.product_uom_qty
        ) AS achieved,
        -- FIN DE CORRECCIÓN

        MAX(rules.currency_id),

        -- DEJAR FECHA EN UTC --
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
      
      -- CORRECCIÓN: COMPARAR FECHA EN UTC (usar ::date) --
      AND (so.date_order::date BETWEEN rules.date_from AND rules.date_to)
      
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