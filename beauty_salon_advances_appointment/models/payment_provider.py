from odoo import models, fields, api
from odoo import http


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _stripe_get_inline_form_values(
        self, amount, currency, partner_id, is_validation, payment_method_sudo=None, **kwargs
    ):
        # Obtención segura del sale_order_id
        sale_order_id = kwargs.get('sale_order_id')
        confirmed_orders = None
        
        if sale_order_id:
            confirmed_orders = self.env['sale.order'].browse(sale_order_id)
        elif hasattr(http, 'request') and http.request and hasattr(http.request, 'website') and http.request.website:
            # Fallback: obtener orden desde la sesión web
            confirmed_orders = http.request.website.sale_get_order()
        
        # Si hay orden válida y no tiene facturas, calcular el TOTAL de anticipos
        if confirmed_orders and confirmed_orders.exists() and not confirmed_orders.invoice_ids:
            total_advance, advance_count = confirmed_orders._calculate_total_advance_amount()
            if total_advance > 0:
                amount = total_advance
        
        return super()._stripe_get_inline_form_values(
            amount, currency, partner_id, is_validation, payment_method_sudo, **kwargs
        )