from odoo import api, fields, models
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, values):
        result = super().create(values)
        if result.calendar_booking_ids:
            new_user = result.calendar_booking_ids[0].staff_user_id.employee_id.default_real_employee_id.user_id
            if new_user:
                result.order_id.user_id = new_user
            else:
                result.order_id.user_id = result.calendar_booking_ids[0].staff_user_id
        return result