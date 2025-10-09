# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Verifica el monto de la transaccion con el total de la orden
    def _is_confirmation_amount_reached(self):
        if self.has_advance_appointment():
            return True
        else:
            res = super()._is_confirmation_amount_reached()
            return res

    def _compute_cart_info(self):
        super()._compute_cart_info()
        for order in self:
            if order.has_advance_appointment():
                order.only_services = True

    def has_advance_appointment(self):
        has_advance_appointment = False
        if self.order_line:
            calendar_booking_ids = self.order_line[0].calendar_booking_ids
            if calendar_booking_ids and calendar_booking_ids.appointment_type_id:
                appointment_type_id = calendar_booking_ids.appointment_type_id
                if appointment_type_id and appointment_type_id.payment_way:
                    has_advance_appointment = True
        return has_advance_appointment