from odoo import api, fields, models
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    aux_branch_id = fields.Many2one('stock.warehouse', string="Branch")

    @api.onchange('aux_branch_id')
    def onchange_aux_branch_id(self):
        if self.aux_branch_id:
            self.warehouse_id = self.aux_branch_id

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, values):
        result = super().create(values)
        if result.calendar_booking_ids:
            new_user = result.calendar_booking_ids[0].staff_user_id.employee_id.default_real_employee_id.user_id
            branch = result.calendar_booking_ids[0].appointment_type_id.branch_id
            if branch:
                result.order_id.aux_branch_id = branch
            if new_user:
                result.order_id.user_id = new_user
            else:
                result.order_id.user_id = result.calendar_booking_ids[0].staff_user_id
        return result
