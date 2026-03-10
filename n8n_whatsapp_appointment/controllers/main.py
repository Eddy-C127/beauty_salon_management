# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

import pytz

from odoo import Command, fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Response


def _json_response(data, status=200):
    """Devuelve una Response JSON para rutas type='http'."""
    return Response(
        json.dumps(data, default=str),
        status=status,
        mimetype='application/json',
    )


_logger = logging.getLogger(__name__)


def _get_params():
    """
    Extrae parámetros del body JSON de la request HTTP.
    Compatible con:
      - JSON directo:          {"appointment_type_id": 6}
      - Envelope JSON-RPC:     {"jsonrpc":"2.0","method":"call","params":{"appointment_type_id":6}}
    """
    try:
        body = request.httprequest.get_data(as_text=True)
        _logger.info('N8N API | body raw [%s]: %s', request.httprequest.path, body[:500] if body else '<empty>')
        if not body:
            return {}
        data = json.loads(body)
        if isinstance(data, dict) and 'params' in data:
            return data['params']
        return data
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(code, message, **extra):
    """Construye una respuesta de error estandarizada."""
    return {'status': 'error', 'code': code, 'message': message, **extra}


def _flatten_slots(months_data, appointment_type):
    """
    Convierte la estructura mensual/semanal devuelta por _get_appointment_slots()
    en una lista plana de slots listos para serializar como JSON.

    Cada entrada contiene:
        datetime            – 'YYYY-MM-DD HH:MM:SS' en la TZ del appointment_type
        duration_h          – duración en horas (float)
        staff_user_id       – int o None  (schedule_based_on='users')
        staff_user_name     – str o None
        available_staff     – lista [{id, name}] si assign_method='time_resource'
        available_resources – lista [{id, name, capacity}] si resources
    """
    flat = []
    for month in months_data:
        for week in month.get('weeks', []):
            for day in week:
                if not isinstance(day, dict):
                    continue
                for slot in day.get('slots', []):
                    duration_raw = slot.get('slot_duration', appointment_type.appointment_duration)
                    try:
                        duration_h = float(duration_raw)
                    except (TypeError, ValueError):
                        duration_h = float(appointment_type.appointment_duration)

                    entry = {
                        'datetime': slot['datetime'],
                        'duration_h': duration_h,
                    }

                    # schedule_based_on = 'users', assign_method = 'time_auto_assign' o 'resource_time'
                    if slot.get('staff_user_id'):
                        uid = slot['staff_user_id']
                        user = request.env['res.users'].sudo().browse(uid)
                        entry['staff_user_id'] = uid
                        entry['staff_user_name'] = user.name if user.exists() else None

                    # schedule_based_on = 'users', assign_method = 'time_resource'
                    elif slot.get('available_staff_users'):
                        entry['available_staff'] = slot['available_staff_users']

                    # schedule_based_on = 'resources'
                    elif slot.get('available_resources'):
                        entry['available_resources'] = slot['available_resources']

                    flat.append(entry)

    # Deduplicar: Odoo puede incluir el mismo slot más de una vez
    seen = set()
    unique = []
    for e in flat:
        key = (e['datetime'], e.get('staff_user_id'))
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


class N8nAppointmentController(http.Controller):
    """
    API REST inbound para la integración n8n <-> Odoo.

    Todas las rutas son type='json' (JSON-RPC 2.0 envelope).
    Autenticación: header X-N8N-Token validado contra n8n.webhook.config.auth_token.
    Si no hay registros con auth_token configurado → modo libre (dev/test).
    """

    # ------------------------------------------------------------------
    # Auth helper
    # ------------------------------------------------------------------

    def _check_token(self):
        """
        Valida el header X-N8N-Token contra n8n.webhook.config.
        Retorna True si OK, dict de error si no autorizado.
        """
        token_header = request.httprequest.headers.get('X-N8N-Token', '')
        configs_with_token = request.env['n8n.webhook.config'].sudo().search([
            ('active', '=', True),
            ('auth_token', '!=', False),
            ('auth_token', '!=', ''),
        ])
        if not configs_with_token:
            return True  # sin tokens configurados → acceso libre (dev)
        if any(cfg.auth_token == token_header for cfg in configs_with_token):
            return True
        return _error(401, 'Token inválido o ausente. Incluye el header X-N8N-Token.')

    # ------------------------------------------------------------------
    # POST /api/n8n/appointment/slots
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/slots',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def get_appointment_slots(self, **kwargs):
        kwargs = _get_params() or kwargs
        """
        Devuelve slots disponibles calculados on-the-fly via _get_appointment_slots().

        Payload (JSON-RPC params):
            appointment_type_id (int, required)
            timezone            (str, optional)  – default: TZ del type
            staff_user_id       (int, optional)  – filtrar por empleado
            reference_date      (str, optional)  – 'YYYY-MM-DD', default hoy
        """
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        appointment_type_id = kwargs.get('appointment_type_id')
        if not appointment_type_id:
            return _json_response(_error(400, 'El campo appointment_type_id es requerido.'), status=400)

        apt_type = request.env['appointment.type'].sudo().browse(int(appointment_type_id))
        if not apt_type.exists() or not apt_type.active:
            return _json_response(_error(404, f'appointment.type #{appointment_type_id} no encontrado o inactivo.'), status=404)

        tz_str = kwargs.get('timezone') or apt_type.appointment_tz or 'America/Mexico_City'

        ref_date_str = kwargs.get('reference_date')
        if ref_date_str:
            try:
                reference_date = datetime.strptime(ref_date_str, '%Y-%m-%d')
            except ValueError:
                return _json_response(_error(400, f'reference_date inválida: {ref_date_str!r}. Usa YYYY-MM-DD.'), status=400)
        else:
            reference_date = datetime.utcnow()

        filter_users = None
        staff_user_id = kwargs.get('staff_user_id')
        if staff_user_id:
            user = request.env['res.users'].sudo().browse(int(staff_user_id))
            if user.exists():
                filter_users = user

        try:
            months_data = apt_type._get_appointment_slots(
                timezone=tz_str,
                filter_users=filter_users,
                reference_date=reference_date,
            )
        except Exception as exc:
            _logger.exception('N8N API | /slots | Error en _get_appointment_slots')
            return _json_response(_error(500, f'Error interno al calcular slots: {exc}'), status=500)

        slots = _flatten_slots(months_data, apt_type)

        return _json_response({
            'status': 'ok',
            'appointment_type_id': apt_type.id,
            'appointment_type_name': apt_type.name,
            'appointment_duration_h': apt_type.appointment_duration,
            'timezone': tz_str,
            'total_slots': len(slots),
            'slots': slots,
        })

    # ------------------------------------------------------------------
    # POST /api/n8n/appointment/book_draft
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/book_draft',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def book_draft_appointment(self, **kwargs):
        kwargs = _get_params() or kwargs
        """
        Crea un calendar.booking (reserva temporal pendiente de pago),
        una sale.order vinculada y una factura de anticipo.
        Devuelve la checkout_url para que n8n la envíe al cliente.

        Payload (JSON-RPC params):
            appointment_type_id (int, required)
            slot_datetime       (str, required)  – 'YYYY-MM-DD HH:MM:SS' en TZ del type
            partner_name        (str, required)
            partner_phone       (str, required)  – E.164 preferido
            partner_email       (str, optional)
            staff_user_id       (int, optional)
            timezone            (str, optional)  – TZ del slot_datetime
        """
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        required = ['appointment_type_id', 'slot_datetime', 'partner_name', 'partner_phone']
        missing = [f for f in required if not kwargs.get(f)]
        if missing:
            return _json_response(_error(400, f'Campos requeridos faltantes: {", ".join(missing)}'), status=400)

        appointment_type_id = int(kwargs['appointment_type_id'])
        raw_slot = kwargs['slot_datetime']
        if isinstance(raw_slot, dict):
            slot_datetime_str = raw_slot.get('datetime', '')
        else:
            slot_datetime_str = str(raw_slot)
        partner_name = kwargs['partner_name'].strip()
        partner_phone = kwargs['partner_phone'].strip()
        partner_email = (kwargs.get('partner_email') or '').strip() or False

        # --- appointment.type ---
        apt_type = request.env['appointment.type'].sudo().browse(appointment_type_id)
        if not apt_type.exists() or not apt_type.active:
            return _json_response(_error(404, f'appointment.type #{appointment_type_id} no encontrado o inactivo.'), status=404)

        if not apt_type.has_payment_step or not apt_type.product_id:
            return _json_response(_error(422, (
                f'El tipo de cita "{apt_type.name}" no tiene paso de pago configurado. '
                'Activa "Up-front Payment" y asigna un producto.'
            )), status=422)

        # --- Parsear slot_datetime (local → UTC) ---
        tz_str = kwargs.get('timezone') or apt_type.appointment_tz or 'America/Mexico_City'
        try:
            local_tz = pytz.timezone(tz_str)
            slot_dt_naive = datetime.strptime(slot_datetime_str, '%Y-%m-%d %H:%M:%S')
            slot_start_utc = local_tz.localize(slot_dt_naive).astimezone(pytz.utc).replace(tzinfo=None)
        except (ValueError, pytz.UnknownTimeZoneError) as exc:
            return _json_response(_error(400, f'slot_datetime inválido: {slot_datetime_str!r}. Error: {exc}'), status=400)

        slot_end_utc = slot_start_utc + timedelta(hours=apt_type.appointment_duration)

        # --- Partner (Phone-First via salon_customer_unifier) ---
        partner = request.env['res.partner'].find_or_create_by_phone(
            phone=partner_phone,
            name=partner_name,
            email=partner_email,
        )
        if not partner:
            return _json_response(_error(422, f'No se pudo normalizar el teléfono: {partner_phone!r}'), status=422)

        # --- Staff user ---
        staff_user = request.env['res.users']
        staff_user_id = kwargs.get('staff_user_id')
        if staff_user_id:
            user_candidate = request.env['res.users'].sudo().browse(int(staff_user_id))
            if not user_candidate.exists() or user_candidate not in apt_type.staff_user_ids:
                return _json_response(_error(422, f'staff_user_id {staff_user_id} no es válido para este tipo de cita.'), status=422)
            staff_user = user_candidate
        elif apt_type.schedule_based_on == 'users' and apt_type.staff_user_ids:
            staff_user = apt_type.staff_user_ids[0]

        # --- appointment.invite (requerido por el modelo calendar.booking) ---
        invite = request.env['appointment.invite'].sudo().search([
            ('appointment_type_ids', 'in', apt_type.id),
        ], limit=1)
        if not invite:
            invite = request.env['appointment.invite'].sudo().create({
                'appointment_type_ids': [Command.link(apt_type.id)],
            })

        # --- Crear calendar.booking ---
        booking_vals = {
            'appointment_type_id': apt_type.id,
            'appointment_invite_id': invite.id,
            'name': partner_name,
            'partner_id': partner.id,
            'product_id': apt_type.product_id.id,
            'start': fields.Datetime.to_string(slot_start_utc),
            'stop': fields.Datetime.to_string(slot_end_utc),
            'asked_capacity': 1,
            'is_from_n8n': True,
        }
        if staff_user:
            booking_vals['staff_user_id'] = staff_user.id

        try:
            booking = request.env['calendar.booking'].sudo().create(booking_vals)
        except (UserError, ValidationError) as exc:
            return _json_response(_error(422, str(exc)), status=422)
        except Exception as exc:
            _logger.exception('N8N API | /book_draft | Error al crear calendar.booking')
            return _json_response(_error(500, f'Error interno al crear la reserva: {exc}'), status=500)

        # --- Crear calendar.event en status 'request' ---
        try:
            event_vals = apt_type._prepare_calendar_event_values(
                1, [], apt_type.appointment_duration, invite,
                request.env['res.partner'], partner_name, partner,
                staff_user or request.env['res.users'], slot_start_utc, slot_end_utc,
            )
            event_vals.update({
                'is_from_n8n': True,
                'n8n_status': 'draft',
                'n8n_partner_phone': partner_phone,
            })
            event_vals.pop('appointment_status', None)
            event = request.env['calendar.event'].sudo().with_context(
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
            ).create(event_vals)
            event.sudo().write({'appointment_status': 'request'})
            booking.sudo().write({'calendar_event_id': event.id})
        except Exception as exc:
            _logger.exception('N8N API | /book_draft | Error al crear calendar.event')
            booking.sudo().unlink()
            return _json_response(_error(500, f'Error al crear el evento de calendario: {exc}'), status=500)

        # --- Sale.order + línea vinculada al booking ---
        website = request.env['website'].sudo().search([], limit=1)
        try:
            order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'date_order': fields.Datetime.now(),
                'website_id': website.id if website else False,
            })
            request.env['sale.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': apt_type.product_id.id,
                'product_uom_qty': 1,
                'calendar_booking_ids': [Command.link(booking.id)],
            })
        except Exception as exc:
            _logger.exception('N8N API | /book_draft | Error al crear sale.order')
            booking.sudo().unlink()
            return _json_response(_error(500, f'Error interno al crear la orden de venta: {exc}'), status=500)

        # --- Calcular anticipo ---
        total_advance, _ = order._calculate_total_advance_amount()
        if not total_advance:
            total_advance = apt_type.product_id.lst_price

        # --- Crear factura de anticipo desde la SO ---
        try:
            ctx = {
                'active_model': 'sale.order',
                'active_ids': order.ids,
                'active_id': order.id,
            }
            downpayment = request.env['sale.advance.payment.inv'].sudo().with_context(ctx).create({
                'advance_payment_method': 'fixed',
                'amount': total_advance,
                'fixed_amount': total_advance,
            })
            downpayment.create_invoices()
            invoice = order.invoice_ids[:1]
            if not invoice:
                raise Exception('No se generó factura tras create_invoices()')
            booking.sudo().write({'account_move_id': invoice.id})
        except Exception as exc:
            _logger.exception('N8N API | /book_draft | Error al crear factura de anticipo')
            booking.sudo().unlink()
            order.sudo().unlink()
            return _json_response(_error(500, f'Error al crear la factura de anticipo: {exc}'), status=500)

        invoice.sudo().action_post()

        # --- Checkout URL ---
        from odoo.addons.payment import utils as payment_utils
        base_url = request.httprequest.host_url.rstrip('/')
        access_token = payment_utils.generate_access_token(
            invoice.partner_id.id,
            invoice.amount_total,
            invoice.currency_id.id,
        )
        checkout_url = (
            f"{base_url}/payment/pay"
            f"?invoice_id={invoice.id}"
            f"&partner_id={partner.id}"
            f"&amount={invoice.amount_total}"
            f"&currency_id={invoice.currency_id.id}"
            f"&access_token={access_token}"
        )

        _logger.info(
            'N8N API | /book_draft | booking=#%s partner="%s"(%s) SO=#%s factura=#%s',
            booking.id, partner.name, partner_phone, order.id, invoice.id,
        )

        return _json_response({
            'status': 'ok',
            'booking_id': booking.id,
            'booking_token': booking.booking_token,
            'sale_order_id': order.id,
            'invoice_id': invoice.id,
            'partner_id': partner.id,
            'partner_name': partner.name,
            'slot_start_utc': fields.Datetime.to_string(slot_start_utc),
            'slot_end_utc': fields.Datetime.to_string(slot_end_utc),
            'advance_amount': total_advance,
            'currency': order.currency_id.name,
            'checkout_url': checkout_url,
            'short_pay_url': f"{base_url}/pay/{booking.booking_token}",
        })

    # ------------------------------------------------------------------
    # POST /api/n8n/appointment/expired_drafts
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/expired_drafts',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def get_expired_drafts(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        minutes = int(kwargs.get('minutes', 30))
        limit = int(kwargs.get('limit', 50))
        cutoff_dt = fields.Datetime.now() - timedelta(minutes=minutes)

        bookings = request.env['calendar.booking'].sudo().search([
            ('is_from_n8n', '=', True),
            ('create_date', '<', cutoff_dt),
        ], limit=limit, order='create_date asc')

        expired = bookings.filtered(
            lambda b: b.calendar_event_id and b.calendar_event_id.n8n_status == 'draft'
        )

        now = fields.Datetime.now()
        result = []
        for booking in expired:
            ev = booking.calendar_event_id
            partner = booking.partner_id
            elapsed = int((now - booking.create_date).total_seconds() / 60)
            sol = request.env['sale.order.line'].sudo().search([
                ('calendar_booking_ids', 'in', booking.id),
            ], limit=1)
            result.append({
                'booking_id': booking.id,
                'booking_token': booking.booking_token,
                'partner_id': partner.id if partner else False,
                'partner_name': partner.name if partner else booking.name,
                'partner_phone': partner.mobile or partner.phone or False,
                'event_id': ev.id,
                'event_name': ev.name,
                'start': fields.Datetime.to_string(ev.start),
                'created_at': fields.Datetime.to_string(booking.create_date),
                'minutes_elapsed': elapsed,
                'invoice_id': booking.account_move_id.id if booking.account_move_id else False,
                'sale_order_id': sol.order_id.id if sol else False,
            })

        return _json_response({
            'status': 'ok',
            'expired_count': len(result),
            'expired': result,
        })

    # ------------------------------------------------------------------
    # POST /api/n8n/appointment/cancel_draft
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/cancel_draft',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def cancel_draft_appointment(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        booking_id = kwargs.get('booking_id')
        booking_token = kwargs.get('booking_token')

        if not booking_id and not booking_token:
            return _json_response(_error(400, 'Se requiere booking_id o booking_token.'), status=400)

        if booking_id:
            booking = request.env['calendar.booking'].sudo().browse(int(booking_id))
            if not booking.exists():
                return _json_response(_error(404, f'calendar.booking #{booking_id} no encontrado.'), status=404)
        else:
            booking = request.env['calendar.booking'].sudo().search([
                ('booking_token', '=', booking_token),
            ], limit=1)
            if not booking:
                return _json_response(_error(404, f'calendar.booking con token "{booking_token}" no encontrado.'), status=404)

        if booking.calendar_event_id and booking.calendar_event_id.appointment_status == 'booked':
            return _json_response(_error(409, (
                f'La reserva #{booking.id} ya fue confirmada y pagada '
                f'(calendar.event #{booking.calendar_event_id.id}). No se puede cancelar.'
            )), status=409)

        if booking.calendar_event_id:
            try:
                booking.calendar_event_id.sudo().write({
                    'appointment_status': 'cancelled',
                    'active': False,
                    'n8n_status': 'cancelled',
                })
            except Exception:
                _logger.warning(
                    'N8N API | /cancel_draft | No se pudo cancelar calendar.event #%s',
                    booking.calendar_event_id.id,
                )

        if booking.account_move_id and booking.account_move_id.state in ('draft', 'posted'):
            try:
                booking.account_move_id.sudo().button_cancel()
            except Exception:
                _logger.warning(
                    'N8N API | /cancel_draft | No se pudo cancelar factura #%s',
                    booking.account_move_id.id,
                )

        sol_lines = request.env['sale.order.line'].sudo().search([
            ('calendar_booking_ids', 'in', booking.id),
        ])
        for line in sol_lines:
            if line.order_id.state not in ('cancel',) and not line.order_id.locked:
                line.order_id.sudo()._action_cancel()

        booking_id_log = booking.id
        booking_token_log = booking.booking_token

        try:
            booking.unlink()
        except Exception as exc:
            _logger.exception('N8N API | /cancel_draft | Error al eliminar booking #%s', booking_id_log)
            return _json_response(_error(500, f'Error al eliminar la reserva: {exc}'), status=500)

        return _json_response({
            'status': 'ok',
            'booking_id': booking_id_log,
            'booking_token': booking_token_log,
            'cancelled': True,
        })

    # ------------------------------------------------------------------
    # POST /api/n8n/appointment/catalog
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/catalog',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def get_catalog(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        mode = kwargs.get('mode', 'services')

        if mode == 'branches':
            branches = request.env['stock.warehouse'].sudo().search([])
            return _json_response({
                'status': 'ok',
                'branches': [{'id': b.id, 'name': b.name, 'code': b.code} for b in branches],
            })

        if mode == 'categories':
            cats = request.env['appointment.category'].sudo().search([])
            return _json_response({
                'status': 'ok',
                'categories': [{'id': c.id, 'name': c.name} for c in cats],
            })

        domain = [('active', '=', True), ('is_published', '=', True)]
        branch_id = kwargs.get('branch_id')
        category_id = kwargs.get('category_id')
        if branch_id:
            domain.append(('branch_id', '=', int(branch_id)))
        if category_id:
            domain.append(('appointment_category_ids', 'in', int(category_id)))

        apts = request.env['appointment.type'].sudo().search(domain, order='name asc')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        seen_names = set()
        services = []
        for a in apts:
            if a.name in seen_names:
                continue
            seen_names.add(a.name)
            services.append({
                'id': a.id,
                'name': a.name,
                'branch_id': a.branch_id.id if a.branch_id else False,
                'branch_name': a.branch_id.name if a.branch_id else False,
                'categories': [{'id': c.id, 'name': c.name} for c in a.appointment_category_ids],
                'duration_h': a.appointment_duration,
                'price': a.product_id.lst_price if a.product_id else 0,
                'currency': a.product_id.currency_id.name if a.product_id and a.product_id.currency_id else 'MXN',
                'is_published': a.is_published,
                'website_url': f"{base_url}{a.website_url}" if a.website_url else False,
            })

        return _json_response({
            'status': 'ok',
            'count': len(services),
            'services': services,
        })

    # ------------------------------------------------------------------
    # POST /api/n8n/appointment/my_appointments
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/my_appointments',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def get_my_appointments(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        phone_raw = kwargs.get('phone', '').strip()
        if not phone_raw:
            return _json_response(_error(400, 'El campo phone es requerido.'), status=400)

        limit = int(kwargs.get('limit', 5))
        include_past = bool(kwargs.get('include_past', False))

        def _normalize_variants(phone):
            digits = ''.join(c for c in phone if c.isdigit())
            variants = set()
            variants.add(phone)
            variants.add(digits)
            if digits:
                variants.add('+' + digits)
                if digits.startswith('52') and len(digits) == 12:
                    variants.add(digits[2:])
                    variants.add('+' + digits[2:])
                if len(digits) == 10:
                    variants.add('52' + digits)
                    variants.add('+52' + digits)
            return list(variants)

        partner = request.env['res.partner']
        phone_variants = _normalize_variants(phone_raw)

        for field in ('mobile', 'phone'):
            for variant in phone_variants:
                found = request.env['res.partner'].sudo().search(
                    [(field, '=', variant)], limit=1
                )
                if found:
                    partner = found
                    break
            if partner:
                break

        if not partner:
            return _json_response({
                'status': 'ok',
                'partner_found': False,
                'partner_id': False,
                'partner_name': False,
                'total': 0,
                'appointments': [],
                'message': 'No encontramos ningún cliente con ese número de teléfono.',
            })

        now = fields.Datetime.now()
        domain = [
            ('partner_ids', 'in', partner.id),
            ('appointment_type_id', '!=', False),
        ]
        if not include_past:
            domain.append(('start', '>=', now))

        events = request.env['calendar.event'].sudo().search(
            domain, order='start asc', limit=limit,
        )

        def _format_dt(dt):
            if not dt:
                return False
            try:
                mx = pytz.timezone('America/Mexico_City')
                local = fields.Datetime.from_string(str(dt))
                local = pytz.utc.localize(local).astimezone(mx)
                return local.strftime('%d/%m/%Y %H:%M')
            except Exception:
                return str(dt)

        appointments = []
        for ev in events:
            appointments.append({
                'event_id': ev.id,
                'name': ev.name or '',
                'service': ev.appointment_type_id.name if ev.appointment_type_id else '',
                'start': _format_dt(ev.start),
                'stop': _format_dt(ev.stop),
                'start_raw': fields.Datetime.to_string(ev.start) if ev.start else False,
                'status': ev.appointment_status or '',
                'n8n_status': ev.n8n_status if hasattr(ev, 'n8n_status') else '',
                'staff': ev.user_id.name if ev.user_id else '',
                'location': ev.location or '',
            })

        return _json_response({
            'status': 'ok',
            'partner_found': True,
            'partner_id': partner.id,
            'partner_name': partner.name,
            'total': len(appointments),
            'appointments': appointments,
        })

    # ------------------------------------------------------------------
    # GET/POST /api/n8n/appointment/context
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/appointment/context',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def get_context(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        topic = (kwargs.get('topic') or '').strip()
        if not topic:
            return _json_response(_error(400, 'El parámetro "topic" es requerido.'), status=400)

        branch_id = kwargs.get('branch_id')
        CompanyContext = request.env['n8n.company.context'].sudo()
        ctx_record = None

        if branch_id:
            ctx_record = CompanyContext.search([
                ('topic_key', '=', topic),
                ('branch_ids', 'in', int(branch_id)),
            ], limit=1, order='sequence asc')
            if not ctx_record:
                ctx_record = CompanyContext.search([
                    ('topic_key', '=', topic),
                    ('branch_ids', '=', False),
                ], limit=1, order='sequence asc')
        else:
            ctx_record = CompanyContext.search([
                ('topic_key', '=', topic),
            ], limit=1, order='sequence asc')

        if not ctx_record:
            return _json_response(
                _error(404, f"No se encontró contexto para el tema '{topic}'"),
                status=404,
            )

        return _json_response({
            'status': 'ok',
            'topic': ctx_record.topic_key,
            'name': ctx_record.name,
            'content': ctx_record.content,
        })

    # ------------------------------------------------------------------
    # GET /pay/<token>  — Redirect corto a la URL de pago
    # ------------------------------------------------------------------

    @http.route(
        '/pay/<string:token>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def pay_redirect(self, token, **kwargs):
        if not token or len(token) != 32:
            return Response('Enlace inválido.', status=400, mimetype='text/plain')

        booking = request.env['calendar.booking'].sudo().search(
            [('booking_token', '=', token)], limit=1
        )
        if not booking:
            return Response(
                'Este enlace de pago ya no está disponible.',
                status=410, mimetype='text/plain',
            )

        invoice = booking.account_move_id
        if not invoice:
            return Response(
                'Este enlace de pago ya no está disponible.',
                status=410, mimetype='text/plain',
            )

        from odoo.addons.payment import utils as payment_utils
        base_url = request.httprequest.host_url.rstrip('/')
        access_token = payment_utils.generate_access_token(
            invoice.partner_id.id,
            invoice.amount_total,
            invoice.currency_id.id,
        )
        checkout_url = (
            f"{base_url}/payment/pay"
            f"?invoice_id={invoice.id}"
            f"&partner_id={invoice.partner_id.id}"
            f"&amount={invoice.amount_total}"
            f"&currency_id={invoice.currency_id.id}"
            f"&access_token={access_token}"
        )
        return request.redirect(checkout_url, code=302, local=False)

    # ------------------------------------------------------------------
    # POST /api/n8n/partner/lookup_or_link
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/partner/lookup_or_link',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def partner_lookup_or_link(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        manychat_id = (kwargs.get('manychat_id') or '').strip()
        if not manychat_id:
            return _json_response(_error(400, 'El campo manychat_id es requerido.'), status=400)

        phone_raw = (kwargs.get('phone') or '').strip() or False
        ig_name = (kwargs.get('instagram_name') or '').strip() or False
        Partner = request.env['res.partner'].sudo()

        def _phone_variants(phone):
            digits = ''.join(c for c in phone if c.isdigit())
            variants = {phone, digits}
            if digits:
                variants.add('+' + digits)
                if digits.startswith('52') and len(digits) == 12:
                    variants.add(digits[2:])
                    variants.add('+' + digits[2:])
                if len(digits) == 10:
                    variants.add('52' + digits)
                    variants.add('+52' + digits)
            return list(variants)

        partner = Partner.search([('manychat_subscriber_id', '=', manychat_id)], limit=1)

        if partner:
            phone_in_odoo = partner.mobile or partner.phone or False
            if phone_in_odoo:
                case = 'A'
                linked = True
                if ig_name:
                    vals_a = {}
                    if not partner.instagram_name:
                        vals_a['instagram_name'] = ig_name
                    if partner.name and partner.name.replace('+', '').replace(' ', '').isdigit():
                        vals_a['name'] = ig_name
                    if vals_a:
                        partner.write(vals_a)
            else:
                case = 'B'
                linked = True
                if phone_raw:
                    vals_b = {'mobile': phone_raw}
                    if ig_name and not partner.instagram_name:
                        vals_b['instagram_name'] = ig_name
                    if ig_name and partner.name and partner.name.replace('+', '').replace(' ', '').isdigit():
                        vals_b['name'] = ig_name
                    partner.write(vals_b)
                    phone_in_odoo = partner.mobile or partner.phone or False

            return _json_response({
                'status': 'ok',
                'case': case,
                'partner_found': True,
                'has_phone': bool(phone_in_odoo),
                'linked': linked,
                'partner_id': partner.id,
                'partner_name': partner.name,
                'phone': phone_in_odoo,
                'manychat_id': manychat_id,
            })

        if not phone_raw:
            return _json_response(_error(400, (
                'No se encontró ningún partner con ese manychat_id. '
                'Proporciona phone para buscar o crear el contacto.'
            )), status=400)

        partner = Partner
        for field in ('mobile', 'phone'):
            for variant in _phone_variants(phone_raw):
                found = Partner.search([(field, '=', variant)], limit=1)
                if found:
                    partner = found
                    break
            if partner:
                break

        if partner:
            case = 'C'
            existing = Partner.search([
                ('manychat_subscriber_id', '=', manychat_id),
                ('id', '!=', partner.id),
            ], limit=1)
            if existing:
                existing.write({'manychat_subscriber_id': False})
            vals_c = {'manychat_subscriber_id': manychat_id}
            if ig_name and not partner.instagram_name:
                vals_c['instagram_name'] = ig_name
            if ig_name and partner.name and partner.name.replace('+', '').replace(' ', '').isdigit():
                vals_c['name'] = ig_name
            partner.write(vals_c)
            return _json_response({
                'status': 'ok',
                'case': case,
                'partner_found': True,
                'has_phone': True,
                'linked': True,
                'partner_id': partner.id,
                'partner_name': partner.name,
                'phone': partner.mobile or partner.phone,
                'manychat_id': manychat_id,
            })

        case = 'D'

        def _is_real_name(name):
            if not name:
                return False
            digits_only = name.replace('+', '').replace(' ', '').replace('-', '')
            return not digits_only.isdigit()

        if not _is_real_name(ig_name):
            return _json_response({
                'status': 'ok',
                'case': case,
                'partner_found': False,
                'has_phone': True,
                'linked': False,
                'partner_id': False,
                'partner_name': False,
                'phone': phone_raw,
                'manychat_id': manychat_id,
                'needs_name': True,
            })

        partner = Partner.create({
            'name': ig_name,
            'mobile': phone_raw,
            'manychat_subscriber_id': manychat_id,
            'customer_rank': 1,
            'lang': 'es_MX',
            'instagram_name': ig_name,
        })

        return _json_response({
            'status': 'ok',
            'case': case,
            'partner_found': False,
            'has_phone': True,
            'linked': True,
            'partner_id': partner.id,
            'partner_name': partner.name,
            'phone': partner.mobile or partner.phone or False,
            'manychat_id': manychat_id,
            'needs_name': False,
        })

    # ------------------------------------------------------------------
    # POST /api/n8n/partner/identify
    # ------------------------------------------------------------------

    @http.route(
        '/api/n8n/partner/identify',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
        website=False,
    )
    def partner_identify(self, **kwargs):
        kwargs = _get_params() or kwargs
        auth = self._check_token()
        if auth is not True:
            return _json_response(auth, status=auth.get('code', 401))

        manychat_id = (kwargs.get('manychat_id') or '').strip()
        if not manychat_id:
            return _json_response(_error(400, 'El campo manychat_id es requerido.'), status=400)

        ig_name = (kwargs.get('instagram_name') or '').strip() or False
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('manychat_subscriber_id', '=', manychat_id)], limit=1)

        if not partner:
            return _json_response({
                'status': 'ok',
                'partner_found': False,
                'has_phone': False,
                'partner_id': False,
                'partner_name': False,
                'phone': False,
                'manychat_id': manychat_id,
            })

        phone = partner.mobile or partner.phone or False
        if ig_name and not partner.instagram_name:
            partner.write({'instagram_name': ig_name})

        return _json_response({
            'status': 'ok',
            'partner_found': True,
            'has_phone': bool(phone),
            'partner_id': partner.id,
            'partner_name': partner.name,
            'phone': phone,
            'manychat_id': manychat_id,
        })
