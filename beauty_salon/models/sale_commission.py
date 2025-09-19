from odoo import models, api, fields, tools


class SaleCommissionPlanUser(models.Model):
    _inherit = 'sale.commission.plan.user'

    real_employee_id  = fields.Many2one('hr.employee', string="Real Employee", readonly=True)

    @api.onchange('user_id')
    def onchange_user_id_real_employee(self):
        if self.user_id and self.user_id.employee_id and self.user_id.employee_id.is_virtual_resource:
            self.real_employee_id = self.user_id.employee_id.default_real_employee_id
        else:
            self.real_employee_id = self.user_id.employee_id



class SaleCommissionReport(models.Model):
    _inherit = 'sale.commission.report'

    real_employee_id = fields.Many2one(
        'hr.employee',
        readonly=True,
    )

    def _query(self):
        users = self.env.context.get('commission_user_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()

        return f"""
WITH {self.env['sale.commission.achievement.report']._commission_lines_query(users=users, teams=teams)},
achievement AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY MAX(era.date_to) DESC, u.user_id) AS id,
        era.id AS target_id,
        era.plan_id AS plan_id,
        u.user_id AS user_id,
        MIN(cl.team_id) AS team_id,
        cl.company_id AS company_id,
        SUM(achieved) AS achieved,
        CASE
            WHEN MAX(era.amount) > 0 THEN GREATEST(SUM(achieved), 0) / MAX(era.amount)
            ELSE 0
        END AS achieved_rate,
        cl.currency_id AS currency_id,
        MAX(era.amount) AS amount,
        MAX(era.date_to) AS payment_date,
        MAX(scpf.id) AS forecast_id,
        MAX(scpf.amount) AS forecast,
        -- NUEVO: derivamos el empleado real a partir del usuario
        MIN(he.id) AS real_employee_id
    FROM sale_commission_plan_target era
    LEFT JOIN sale_commission_plan_user u
        ON u.plan_id=era.plan_id
        AND COALESCE(u.date_from, era.date_from)<era.date_to
        AND COALESCE(u.date_to, era.date_to)>era.date_from
    LEFT JOIN commission_lines cl
        ON cl.plan_id = era.plan_id
        AND cl.date >= era.date_from
        AND cl.date <= era.date_to
        AND cl.user_id = u.user_id
    LEFT JOIN sale_commission_plan_target_forecast scpf
        ON (scpf.target_id = era.id AND u.user_id = scpf.user_id)
    -- NUEVO: relación usuario -> empleado
    LEFT JOIN hr_employee he ON he.user_id = u.user_id
    GROUP BY
        era.id,
        era.plan_id,
        u.user_id,
        cl.company_id,
        cl.currency_id
), target_com AS (
    SELECT
        amount AS before,
        target_rate AS rate_low,
        LEAD(amount) OVER (PARTITION BY plan_id ORDER BY target_rate) AS amount,
        LEAD(target_rate) OVER (PARTITION BY plan_id ORDER BY target_rate) AS rate_high,
        plan_id
    FROM sale_commission_plan_target_commission scpta
    JOIN sale_commission_plan scp ON scp.id = scpta.plan_id
    WHERE scp.type = 'target'
), achievement_target AS (
    SELECT
        min(a.id) as id,
        min(a.target_id) as target_id,
        a.plan_id,
        a.user_id,
        a.team_id,
        a.company_id,
        a.currency_id,
        min(a.forecast_id) as forecast_id,
        {self._get_date_range()} as payment_date,
        sum(a.achieved) as achieved,
        case WHEN sum(a.amount) > 0 THEN sum(a.achieved) / sum(a.amount) ELSE NULL END as achieved_rate,
        sum(a.amount) AS target_amount,
        sum(a.forecast) as forecast,
        count(1) as ct,
        -- NUEVO: propagamos el employee
        a.real_employee_id as real_employee_id
    FROM achievement a
    GROUP BY
        a.plan_id, a.user_id, a.team_id, a.company_id, a.currency_id, {self._get_date_range()}, a.real_employee_id
)
SELECT
    a.*,
    CASE
        WHEN tc.before IS NULL THEN a.achieved
        WHEN tc.rate_high IS NULL THEN tc.before * a.ct
        ELSE (tc.before + (tc.amount - tc.before) * (a.achieved_rate - tc.rate_low) / (tc.rate_high - tc.rate_low)) * a.ct
    END AS commission
FROM achievement_target a
LEFT JOIN target_com tc ON (
    tc.plan_id = a.plan_id AND
    tc.rate_low <= a.achieved_rate AND
    (tc.rate_high IS NULL OR tc.rate_high > a.achieved_rate)
)
"""
