# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
import urllib.error

from odoo import fields, models

_logger = logging.getLogger(__name__)

_N8N_TIMEOUT = 10


class CalendarBooking(models.Model):
    _inherit = 'calendar.booking'

    is_from_n8n = fields.Boolean(
        string='Origen: n8n/WhatsApp',
        default=False,
        copy=False,
    )

    def _make_event_from_paid_booking(self):
        """
        Override: si el booking ya tiene calendar_event_id (creado en request por book_draft),
        lo promovemos a 'booked' en vez de crear uno nuevo. El super() lo omite porque
        filtra bookings sin calendar_event_id. Luego stampa n8n_status='paid'.

        IMPORTANTE: appointment_account_payment llama este método al hacer _post() en la
        factura (aunque no esté pagada). Para bookings de n8n, solo promovemos a booked
        si la factura asociada ya fue efectivamente pagada (payment_state='paid' o 'in_payment').

        También dispara el webhook saliente a n8n desde aquí, ya que es el único punto
        donde se puede garantizar con certeza que el pago fue confirmado para citas WhatsApp.
        """
        # Para bookings que NO son de n8n, comportamiento normal del super()
        super()._make_event_from_paid_booking()

        for booking in self.filtered(lambda b: b.is_from_n8n and b.calendar_event_id):
            invoice = booking.account_move_id
            # Solo confirmar si la factura realmente está pagada
            if invoice and invoice.payment_state not in ('paid', 'in_payment'):
                _logger.info(
                    'N8N | booking #%s: factura #%s aún no pagada (payment_state=%s) — se mantiene en request/draft',
                    booking.id, invoice.id, invoice.payment_state,
                )
                continue

            _logger.info(
                'N8N | booking #%s: pago confirmado — promoviendo a booked/paid',
                booking.id,
            )
            booking.calendar_event_id.sudo().write({
                'appointment_status': 'booked',
                'is_from_n8n': True,
                'n8n_status': 'paid',
            })

            # Disparar webhook saliente a n8n
            self._notify_n8n_payment_confirmed(booking.calendar_event_id)

    def _notify_n8n_payment_confirmed(self, event):
        """Envía el webhook de pago confirmado a todos los n8n.webhook.config activos."""
        webhooks = self.env['n8n.webhook.config'].sudo().search([('active', '=', True)])
        if not webhooks:
            return

        # Teléfono: preferir el guardado en la reserva (rawPhone de WhatsApp),
        # con fallback al partner por si se usa fuera del flujo de WhatsApp
        partner_phone = (
            event.n8n_partner_phone
            or (event.partner_id.mobile if event.partner_id else False)
            or (event.partner_id.phone if event.partner_id else False)
            or False
        )
        payload = {
            'event': 'appointment.payment.confirmed',
            'event_id': event.id,
            'n8n_reservation_id': event.n8n_reservation_id or False,
            'n8n_status': event.n8n_status,
            'partner_id': event.partner_id.id if event.partner_id else False,
            'partner_name': event.partner_id.name if event.partner_id else False,
            'partner_phone': partner_phone,
            'manychat_id': event.partner_id.manychat_subscriber_id if event.partner_id else False,
            'appointment_type_id': event.appointment_type_id.id if event.appointment_type_id else False,
            'appointment_type_name': event.appointment_type_id.name if event.appointment_type_id else False,
            'start': event.start.isoformat() if event.start else False,
            'stop': event.stop.isoformat() if event.stop else False,
        }
        body = json.dumps(payload).encode('utf-8')

        for webhook in webhooks:
            req = urllib.request.Request(
                url=webhook.webhook_url,
                data=body,
                method='POST',
                headers={'Content-Type': 'application/json'},
            )
            if webhook.auth_token:
                req.add_header('Authorization', f'Bearer {webhook.auth_token}')
            try:
                with urllib.request.urlopen(req, timeout=_N8N_TIMEOUT) as resp:
                    _logger.info(
                        'N8N Webhook | "%s" → %s | HTTP %s',
                        webhook.name, webhook.webhook_url, resp.status,
                    )
            except urllib.error.HTTPError as exc:
                _logger.warning(
                    'N8N Webhook | "%s" → %s | HTTP error %s: %s',
                    webhook.name, webhook.webhook_url, exc.code, exc.reason,
                )
            except urllib.error.URLError as exc:
                _logger.warning(
                    'N8N Webhook | "%s" → %s | URL error: %s',
                    webhook.name, webhook.webhook_url, exc.reason,
                )
            except Exception:
                _logger.exception(
                    'N8N Webhook | "%s" → %s | Error inesperado',
                    webhook.name, webhook.webhook_url,
                )
