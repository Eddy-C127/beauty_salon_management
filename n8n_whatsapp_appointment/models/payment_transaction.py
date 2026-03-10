# -*- coding: utf-8 -*-
import logging

from odoo import models, Command

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """
        Override: cuando una transacción pasa a 'done' (pago online confirmado):
        1. Si la tx cubre una factura cuyo invoice_origin apunta a un SO de nuestra
           integración, vinculamos el SO a tx.sale_order_ids.
        2. Para bookings is_from_n8n cuya factura queda pagada, promovemos la cita
           a booked/paid y disparamos el webhook saliente a n8n.
        """
        # Recopilar bookings n8n afectados ANTES del super() para tener el estado previo
        n8n_bookings_to_confirm = self.env['calendar.booking']
        for tx in self.filtered(lambda t: t.state == 'done' and t.invoice_ids):
            for invoice in tx.invoice_ids:
                # Enlazar SO si aplica (flujo factura directa)
                if invoice.invoice_origin and not tx.sale_order_ids:
                    so = self.env['sale.order'].sudo().search(
                        [('name', '=', invoice.invoice_origin)], limit=1
                    )
                    if so and so.state in ('draft', 'sent'):
                        tx.sudo().write({'sale_order_ids': [Command.link(so.id)]})
                        _logger.info(
                            'N8N TX#%s | Vinculando SO %s (id=%s) vía invoice_origin',
                            tx.id, so.name, so.id,
                        )
                # Recopilar bookings n8n con event asociado
                for booking in invoice.calendar_booking_ids:
                    if booking.is_from_n8n and booking.calendar_event_id:
                        n8n_bookings_to_confirm |= booking

        super()._post_process()

        # Ahora la factura debería estar en payment_state=paid/in_payment
        # Promover citas y disparar webhooks
        for booking in n8n_bookings_to_confirm:
            invoice = booking.account_move_id
            if invoice.payment_state not in ('paid', 'in_payment'):
                _logger.info(
                    'N8N TX | booking #%s: factura #%s aún no pagada (payment_state=%s) — sin cambios',
                    booking.id, invoice.id, invoice.payment_state,
                )
                continue
            event = booking.calendar_event_id
            _logger.info(
                'N8N TX | booking #%s: pago confirmado — promoviendo event #%s a booked/paid',
                booking.id, event.id,
            )
            event.sudo().write({
                'appointment_status': 'booked',
                'n8n_status': 'paid',
            })
            booking._notify_n8n_payment_confirmed(event)
