from odoo import models, fields, api


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _stripe_get_inline_form_values(
        self, amount, currency, partner_id, is_validation, payment_method_sudo=None, **kwargs
    ):
        #Apple Pay generico verificar metodos adicionales en el futuro.
        confirmed_orders = self.env['sale.order'].browse(kwargs['sale_order_id'])
        if not confirmed_orders.invoice_ids:
            appointment_type_id = self._get_appointment_type(confirmed_orders)
            if appointment_type_id and appointment_type_id.advance_type:
                advance_type = appointment_type_id.advance_type
                if advance_type == 'advance_percentage':
                    amount= amount * (appointment_type_id.advance_percentage/100)
                if advance_type == 'fixed_import':
                    amount=appointment_type_id.fixed_import
        print('MONTO ACTUALIZADO--------------------------------------------------------->'+str(amount))
        stripe = super()._stripe_get_inline_form_values(amount,currency,partner_id,is_validation,payment_method_sudo,**kwargs)
        return stripe


    def _get_appointment_type(self,confirmed_orders):
        calendar_booking_ids = confirmed_orders.order_line[0].calendar_booking_ids
        if calendar_booking_ids and calendar_booking_ids.appointment_type_id:
            appointment_type_id = calendar_booking_ids.appointment_type_id
            if appointment_type_id:
                return appointment_type_id
        return False