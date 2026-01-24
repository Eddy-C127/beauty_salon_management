from odoo import models, fields, api


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        confirmed_orders = super()._check_amount_and_confirm_order()
        
        # Si no hay órdenes confirmadas, retornar
        if not confirmed_orders:
            return confirmed_orders
        
        # Auto Facturar si tiene anticipo configurado y no tiene facturas
        if not confirmed_orders.invoice_ids:
            # Calcular el TOTAL de anticipos de TODAS las citas
            total_advance, advance_count = confirmed_orders._calculate_total_advance_amount()
            
            if total_advance > 0:
                ctx = {
                    'active_model': 'sale.order',
                    'active_ids': confirmed_orders.ids,
                    'active_id': confirmed_orders.id,
                }
                
                # Crear UNA factura de anticipo con el monto TOTAL
                downpayment = self.env['sale.advance.payment.inv'].with_context(ctx).create({
                    'advance_payment_method': 'fixed',
                    'amount': total_advance,
                    'fixed_amount': total_advance,
                })
                downpayment.create_invoices()
        
        return confirmed_orders    
