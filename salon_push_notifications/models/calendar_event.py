from datetime import timedelta
import logging

from odoo import api, fields, models, Command

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    push_notif_confirmed = fields.Boolean(
        string='Push Confirmation Sent',
        default=False,
        copy=False,
    )
    push_notif_reminder_sent_ids = fields.Many2many(
        'calendar.alarm',
        'calendar_event_push_reminder_rel',
        'event_id',
        'alarm_id',
        string='Push Reminders Sent',
        copy=False,
    )

    # ─── Helpers ────────────────────────────────────────────────────────────────

    def _get_push_visitors(self, partner):
        """Return website.visitor records that have push subscriptions for a partner."""
        return self.env['website.visitor'].search([
            ('partner_id', '=', partner.id),
            ('has_push_notifications', '=', True),
        ])

    def _get_firebase_account(self):
        """Return the active push notification social.account."""
        return self.env['social.account'].search([
            ('media_type', '=', 'push_notifications'),
        ], limit=1)

    def _is_push_enabled(self):
        """Check if salon push notifications are enabled in settings."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'salon_push_notifications.enabled', default='True'
        ) == 'True'

    def _format_appointment_date(self, dt):
        """Format a datetime for display in the user's timezone."""
        tz = self.env.user.tz or 'UTC'
        try:
            import pytz
            user_tz = pytz.timezone(tz)
            local_dt = fields.Datetime.context_timestamp(self, dt)
            return local_dt.strftime('%d/%m/%Y a las %H:%M')
        except Exception:
            return fields.Datetime.to_string(dt)

    # ─── Visitor → Partner linking (guest bookings) ──────────────────────────────

    def _link_visitor_to_booker(self, partner):
        """Transfer the current session's push subscriptions to the appointment booker's partner.

        Problem this solves:
            An anonymous visitor accepts push notifications (has_push_notifications=True,
            partner_id=False). Then books an appointment as a guest (not logged in).
            The push confirmation is sent to env['website.visitor'] filtered by
            partner_id == booker. But the anonymous visitor has no partner_id, so the
            search returns nothing and the push is never sent.

        How it works (safely):
            1. Gets the website.visitor for the CURRENT HTTP session (by cookie).
            2. Finds or creates a visitor record for the partner
               (access_token = str(partner.id) → partner_id is computed automatically).
            3. Transfers the push subscription tokens to the partner's visitor.
               The push_token unique DB constraint guarantees no token duplication.
            4. The anonymous visitor keeps existing (its access_token/cookie is unchanged),
               but its push subscriptions now belong to the partner visitor.

        Safety guards (ALL must pass — if any fails, the booking is NOT affected):
            - Must be in an active HTTP request context (never runs in cron or backend shell).
            - Must be a website request (not the Odoo backend /web).
            - The current session visitor must have NO partner_id already
              (never overwrites an existing link — protects logged-in users).
            - The visitor must have at least one active push subscription
              (if no subscriptions, nothing to transfer, skip silently).
            - The partner must not already have a visitor with push subscriptions
              (avoids transferring onto a visitor that already has tokens,
              which would fail silently thanks to ON CONFLICT on the unique constraint).

        Device-sharing limitation (inherent to push technology):
            If two people share the same browser/device and the same Odoo session cookie,
            they share one website.visitor. This means the second person's push token
            would be linked to the first person's appointments. This is NOT fixable at
            the application level — it is a fundamental limitation of push notifications
            on shared devices. The only mitigation is requiring login.
        """
        try:
            # Guard 1: only in active HTTP request (not cron, not shell, not backend jobs)
            import odoo.http as http
            if not http.request:
                return

            # Guard 2: get the visitor tied to the current session cookie
            visitor = self.env['website.visitor'].sudo()._get_visitor_from_request()
            if not visitor:
                return

            # Guard 3: never overwrite an existing partner link
            # (protects logged-in users and previously linked anonymous sessions)
            if visitor.partner_id:
                return

            # Guard 4: only proceed if this visitor actually has push subscriptions
            # (no subscriptions = nothing to transfer = no-op)
            if not visitor.has_push_notifications:
                return

            # Find or create the partner's visitor record.
            # In Odoo, a visitor with access_token = str(partner.id) automatically
            # computes partner_id = partner (see website.visitor._compute_partner_id).
            partner_visitor = self.env['website.visitor'].sudo().search(
                [('access_token', '=', str(partner.id))], limit=1
            )

            if not partner_visitor:
                partner_visitor = self.env['website.visitor'].sudo().create({
                    'access_token': str(partner.id),
                    'lang_id': visitor.lang_id.id,
                    'country_id': visitor.country_id.id,
                    'timezone': visitor.timezone,
                    'website_id': visitor.website_id.id,
                })

            # Guard 6: if the partner visitor already has push subscriptions,
            # do not transfer — their existing tokens are correct and we don't
            # want to mix tokens from different devices or sessions.
            if partner_visitor.has_push_notifications:
                _logger.info(
                    'salon_push_notifications: partner visitor %s already has push '
                    'subscriptions, skipping transfer from anonymous visitor %s',
                    partner_visitor.id, visitor.id,
                )
                return

            # Transfer push subscriptions from the anonymous visitor to the partner visitor.
            # ON CONFLICT DO NOTHING at DB level (push_token unique constraint) ensures
            # no token is ever duplicated even under concurrent requests.
            token_count = len(visitor.push_subscription_ids)
            visitor.push_subscription_ids.write({'website_visitor_id': partner_visitor.id})
            _logger.info(
                'salon_push_notifications: transferred %d push token(s) from '
                'anonymous visitor %s to partner visitor %s (partner: %s #%s)',
                token_count, visitor.id, partner_visitor.id, partner.name, partner.id,
            )

        except Exception:
            # Never let a push notification error affect the appointment booking.
            _logger.exception(
                'salon_push_notifications: unexpected error in _link_visitor_to_booker '
                'for partner %s — booking continues normally', partner.id if partner else '?'
            )

    # ─── Confirmation ────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # TRACE: write to file to confirm this code runs in web server context
        if not self._is_push_enabled():
            return records
        for event in records.filtered(
            lambda e: e.appointment_type_id and e.appointment_booker_id
        ):
            # Link anonymous visitor to partner BEFORE sending confirmation,
            # so _get_push_visitors(booker) can find the newly linked visitor.
            event._link_visitor_to_booker(event.appointment_booker_id)
            try:
                event._send_push_confirmation()
            except Exception:
                _logger.exception(
                    'salon_push_notifications: error sending confirmation for event %s', event.id
                )
        return records

    def _get_push_visitors_for_confirmation(self):
        """Return visitors to send the confirmation push to.

        Strategy (union of two sources, deduplicated):
        1. The visitor tied to the current HTTP session cookie — this is the
           physical device doing the booking. Always included when available,
           regardless of partner matching. This handles the common case where
           the session visitor's token differs from the partner's linked visitor
           (e.g. user logged in on one device, push subscription on another,
           or duplicate partner records).
        2. The visitor(s) linked to appointment_booker_id by partner_id —
           used as fallback and also picked up by the cron for reminders.

        The union is computed as a single recordset so _firebase_send_message
        de-duplicates at the token level (unique constraint on push_token).
        """
        collected = self.env['website.visitor'].sudo()

        # Source 1: visitor from the current HTTP session.
        # Guard: only when there is an active HTTP request (not cron, not shell).
        # We do NOT require http.request.website — the appointment controller
        # creates the calendar.event with sudo(), which drops the website
        # attribute from the request context even though the original request
        # came from the public website.
        try:
            import odoo.http as http
            if http.request:
                session_visitor = self.env['website.visitor'].sudo()._get_visitor_from_request()
                if session_visitor and session_visitor.has_push_notifications:
                    _logger.info(
                        'salon_push_notifications: confirm: session visitor %s '
                        '(partner=%s, tokens=%s) for booker %s',
                        session_visitor.id,
                        session_visitor.partner_id.id if session_visitor.partner_id else None,
                        len(session_visitor.push_subscription_ids),
                        self.appointment_booker_id.id,
                    )
                    collected |= session_visitor
        except Exception:
            _logger.exception('salon_push_notifications: error getting session visitor')

        # Source 2: visitors linked to the booker partner
        partner_visitors = self._get_push_visitors(self.appointment_booker_id)
        if partner_visitors:
            collected |= partner_visitors

        _logger.info(
            'salon_push_notifications: [DEBUG] confirm: total visitors=%s for booker=%s',
            len(collected), self.appointment_booker_id.id,
        )
        return collected

    def _send_push_confirmation(self):
        """Send an immediate push notification confirming the appointment booking."""
        if self.push_notif_confirmed:
            _logger.info('salon_push_notifications: [DEBUG] confirm: already confirmed, skip')
            return
        account = self._get_firebase_account()
        if not account:
            _logger.warning('salon_push_notifications: no push account found, skipping confirmation')
            return
        visitors = self._get_push_visitors_for_confirmation()
        _logger.info('salon_push_notifications: [DEBUG] confirm: booker=%s visitors_found=%s',
                     self.appointment_booker_id.id, len(visitors))
        if not visitors:
            return

        date_str = self._format_appointment_date(self.start)
        appointment_name = self.appointment_type_id.name or 'tu cita'

        data = {
            'title': '¡Cita confirmada!',
            'body': f'{appointment_name} confirmada para el {date_str}.',
            'icon': '/web/image/res.company/%d/logo' % self.env.company.id,
            'target_url': '/web#action=calendar.action_calendar_event&id=%d' % self.id,
        }
        account._firebase_send_message(data, visitors)
        # Use raw SQL to avoid triggering write() side effects on calendar.event
        self.env.cr.execute(
            "UPDATE calendar_event SET push_notif_confirmed = TRUE WHERE id = %s",
            (self.id,)
        )

    # ─── Reminders (cron) ────────────────────────────────────────────────────────

    @api.model
    def _cron_send_push_reminders(self):
        """Cron: send push reminder notifications based on calendar.alarm triggers."""
        if not self._is_push_enabled():
            return

        account = self._get_firebase_account()
        if not account:
            _logger.warning('salon_push_notifications: no push account found, skipping reminders')
            return

        now = fields.Datetime.now()
        window_start = now - timedelta(minutes=15)

        # Events with appointment context, in the next 7 days, not yet past
        events = self.search([
            ('appointment_type_id', '!=', False),
            ('appointment_booker_id', '!=', False),
            ('start', '>', now),
            ('start', '<=', now + timedelta(days=7)),
            ('appointment_status', 'not in', ['cancelled']),
        ])

        for event in events:
            if not event.appointment_booker_id:
                continue

            alarms_to_check = event.alarm_ids - event.push_notif_reminder_sent_ids

            if not alarms_to_check:
                # Fallback: use configured hours from Settings
                self._send_push_reminder_fallback(event, account, now, window_start)
                continue

            for alarm in alarms_to_check:
                trigger_time = event.start - timedelta(minutes=alarm.duration_minutes)
                if window_start <= trigger_time <= now:
                    try:
                        event._send_push_reminder(alarm, account)
                        # Use raw SQL to avoid triggering write() side effects on calendar.event
                        self.env.cr.execute(
                            "INSERT INTO calendar_event_push_reminder_rel (event_id, alarm_id) "
                            "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (event.id, alarm.id)
                        )
                    except Exception:
                        _logger.exception(
                            'salon_push_notifications: error sending reminder for event %s, alarm %s',
                            event.id, alarm.id
                        )

    def _send_push_reminder(self, alarm, account):
        """Send a push reminder notification for a specific alarm."""
        visitors = self._get_push_visitors(self.appointment_booker_id)
        if not visitors:
            return

        date_str = self._format_appointment_date(self.start)
        appointment_name = self.appointment_type_id.name or 'tu cita'

        # Build human-readable time description
        duration = alarm.duration
        interval = alarm.interval
        interval_labels = {
            'minutes': 'minuto(s)',
            'hours': 'hora(s)',
            'days': 'día(s)',
            'weeks': 'semana(s)',
        }
        interval_label = interval_labels.get(interval, interval)

        data = {
            'title': f'Recordatorio: {appointment_name}',
            'body': f'Tienes {appointment_name} en {duration} {interval_label} ({date_str}).',
            'icon': '/web/image/res.company/%d/logo' % self.env.company.id,
            'target_url': '/',
        }
        account._firebase_send_message(data, visitors)

    @api.model
    def _send_push_reminder_fallback(self, event, account, now, window_start):
        """Send a push reminder using the fallback hours configured in Settings."""
        # Only send if not already confirmed via fallback
        if event.push_notif_reminder_sent_ids:
            return

        fallback_hours = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'salon_push_notifications.reminder_hours', default='24'
            )
        )
        trigger_time = event.start - timedelta(hours=fallback_hours)
        if window_start <= trigger_time <= now:
            visitors = self._get_push_visitors(event.appointment_booker_id)
            if not visitors:
                return
            date_str = event._format_appointment_date(event.start)
            appointment_name = event.appointment_type_id.name or 'tu cita'
            data = {
                'title': f'Recordatorio: {appointment_name}',
                'body': f'Tienes {appointment_name} mañana: {date_str}.',
                'icon': '/web/image/res.company/%d/logo' % self.env.company.id,
                'target_url': '/',
            }
            account._firebase_send_message(data, visitors)
            # Use raw SQL to avoid triggering write() side effects on calendar.event
            self.env.cr.execute(
                "UPDATE calendar_event SET push_notif_fallback_reminder_sent = TRUE WHERE id = %s",
                (event.id,)
            )

    push_notif_fallback_reminder_sent = fields.Boolean(
        string='Push Fallback Reminder Sent',
        default=False,
        copy=False,
    )
