from odoo import models, fields, api


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        confirmed_orders = super()._check_amount_and_confirm_order()
        #confirmed_orders._compute_cart_info()
        # Auto Facturar si tiene el booleano Verdadero
        if not confirmed_orders.invoice_ids:
            appointment_type_id = self._get_appointment_type(confirmed_orders)
            if appointment_type_id and appointment_type_id.advance_type:
                advance_type = appointment_type_id.advance_type
                ctx = {
                    'active_model': 'sale.order',
                    'active_ids': confirmed_orders.ids,
                    'active_id': confirmed_orders.id,
                }
                if advance_type == 'advance_percentage':

                    downpayment = self.env['sale.advance.payment.inv'].with_context(ctx).create({
                        'advance_payment_method': 'percentage',
                        'amount': appointment_type_id.advance_percentage,
                        'fixed_amount':1,
                    })
                    downpayment.create_invoices()
                if advance_type == 'fixed_import':
                    downpayment = self.env['sale.advance.payment.inv'].with_context(ctx).create({
                        'advance_payment_method': 'fixed',
                        'amount': appointment_type_id.fixed_import,
                        'fixed_amount':appointment_type_id.fixed_import,
                    })
                    downpayment.create_invoices()
        return confirmed_orders

    # def _stripe_prepare_payment_intent_payload(self):
    #     res = super()._stripe_prepare_payment_intent_payload()
    #     import ipdb; ipdb.set_trace()
    #     return res

    def _get_appointment_type(self,confirmed_orders):
        calendar_booking_ids = confirmed_orders.order_line[0].calendar_booking_ids
        if calendar_booking_ids and calendar_booking_ids.appointment_type_id:
            appointment_type_id = calendar_booking_ids.appointment_type_id
            if appointment_type_id:
                return appointment_type_id
        return False    
