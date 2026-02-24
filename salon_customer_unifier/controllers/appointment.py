# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers.appointment import AppointmentController

_logger = logging.getLogger(__name__)


class AppointmentPhoneMatch(AppointmentController):
    """
    Override del controller de citas para implementar Phone-First Match
    y la asignación del partner correcto al carrito de eCommerce.

    PROBLEMA NATIVO:
    1. Odoo usa EMAIL como criterio primario para identificar partners.
       Para usuarios públicos, siempre crea un partner nuevo (duplicados).
    2. website_appointment_sale._redirect_to_payment() crea el carrito
       con el partner del usuario público (anónimo), no con el cliente real.

    SOLUCIÓN (tres pasos en el mismo request):
    - ANTES de super(): resolver partner por teléfono, inyectar en _get_customer_partner()
    - DESPUÉS de super(): el carrito ya fue creado → asignar el partner resuelto
    - DESPUÉS de super(): si el cliente solicitó corrección de datos → crear actividad
    """

    @http.route(['/appointment/<int:appointment_type_id>/submit'],
                type='http', auth="public", website=True, methods=["POST"])
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str,
                                name, phone, email, staff_user_id=None,
                                available_resource_ids=None, asked_capacity=1,
                                guest_emails_str=None, **kwargs):
        # ── Extraer campos propios ANTES de llamar a super() ──────────────────
        # El controller nativo tiene **kwargs pero pasa parámetros desconocidos
        # al modelo; mejor limpiarlos aquí para evitar warnings.
        found_partner_id_str = kwargs.pop('found_partner_id', '').strip()
        correction_name = kwargs.pop('correction_name', '').strip()
        correction_email = kwargs.pop('correction_email', '').strip()

        # ── PASO 1: PHONE-FIRST MATCH ─────────────────────────────────────────
        Partner = request.env['res.partner']
        customer = Partner.find_or_create_by_phone(phone, name, email)

        if customer:
            _logger.info(
                'salon_customer_unifier: Partner resuelto para cita: "%s" (ID %s)',
                customer.name, customer.id,
            )
            request._phone_matched_partner = customer
        else:
            _logger.warning(
                'salon_customer_unifier: No se pudo resolver partner por teléfono "%s". '
                'Usando flujo nativo de Odoo.',
                phone,
            )

        # ── PASO 2: FLUJO NATIVO (crea calendar.booking + carrito eCommerce) ──
        response = super().appointment_form_submit(
            appointment_type_id, datetime_str, duration_str,
            name, phone, email,
            staff_user_id=staff_user_id,
            available_resource_ids=available_resource_ids,
            asked_capacity=asked_capacity,
            guest_emails_str=guest_emails_str,
            **kwargs,
        )

        # ── PASO 3: ASIGNAR PARTNER AL CARRITO ───────────────────────────────
        if customer:
            self._assign_partner_to_cart(customer)

        # ── PASO 4: CREAR ACTIVIDAD DE CORRECCIÓN SI EL CLIENTE LO SOLICITÓ ──
        if found_partner_id_str and (correction_name or correction_email):
            try:
                self._create_data_correction_activity(
                    int(found_partner_id_str),
                    correction_name,
                    correction_email,
                    phone,
                    appointment_type_id,
                )
            except Exception as e:
                # No interrumpir el flujo de citas si la actividad falla
                _logger.warning(
                    'salon_customer_unifier: Error creando actividad de corrección: %s', e,
                )

        return response

    def _get_customer_partner(self):
        """
        Override: retorna el partner ya resuelto por teléfono.
        Evita que la lógica email-first cree un partner duplicado.
        """
        phone_matched = getattr(request, '_phone_matched_partner', None)
        if phone_matched:
            return phone_matched
        return super()._get_customer_partner()

    @http.route('/appointment/partner_lookup', type='json', auth='public', website=True)
    def appointment_partner_lookup(self, phone='', **kwargs):
        """
        Busca un partner por teléfono SIN crear uno nuevo.
        Retorna también el ID del partner para que el JS pueda
        incluirlo en la solicitud de corrección de datos.
        """
        if not phone or len(str(phone).strip()) < 6:
            return {'found': False}
        try:
            partner = request.env['res.partner'].search_by_phone(phone)
            if not partner:
                return {'found': False}
            return {
                'found': True,
                'partner_id': partner.id,
                'name': partner.name or '',
                'email': partner.email or '',
                'has_email': bool(partner.email),
            }
        except Exception as e:
            _logger.warning('salon_customer_unifier partner_lookup error: %s', e)
            return {'found': False, 'error': True}

    @http.route('/appointment/send_correction', type='json', auth='public', website=True)
    def appointment_send_correction(self, found_partner_id=0, correction_name='',
                                     correction_email='', phone='',
                                     appointment_type_id=None, **kwargs):
        """
        Endpoint AJAX para enviar la solicitud de corrección de datos
        de forma independiente (sin necesidad de agendar la cita).

        El cliente puede pulsar "Enviar solicitud" desde el formulario de
        corrección y la actividad se crea inmediatamente en el partner.
        """
        correction_name = (correction_name or '').strip()
        correction_email = (correction_email or '').strip()

        if not found_partner_id or not (correction_name or correction_email):
            return {'success': False, 'error': 'missing_data'}

        try:
            self._create_data_correction_activity(
                int(found_partner_id),
                correction_name,
                correction_email,
                phone or '',
                appointment_type_id,
            )
            return {'success': True}
        except Exception as e:
            _logger.warning('salon_customer_unifier send_correction error: %s', e)
            return {'success': False, 'error': str(e)}

    def _create_data_correction_activity(self, found_partner_id, correction_name,
                                          correction_email, phone, appointment_type_id=None):
        """
        Crea una actividad "Hacer" en el partner encontrado por teléfono.

        La actividad se asigna a los usuarios configurados en el campo
        `salon_correction_user_ids` del tipo de cita. Si no hay ninguno
        configurado, se asigna al administrador del sistema.
        Se crea una actividad independiente por cada responsable configurado.

        :param found_partner_id: int — ID del partner encontrado por teléfono
        :param correction_name: str — Nombre correcto indicado por el cliente
        :param correction_email: str — Correo correcto indicado por el cliente
        :param phone: str — Teléfono del cliente (para contexto en la nota)
        :param appointment_type_id: int — ID del tipo de cita (para obtener responsables)
        """
        partner = request.env['res.partner'].sudo().browse(found_partner_id)
        if not partner.exists():
            _logger.warning(
                'salon_customer_unifier: Partner ID %s no existe, '
                'no se crea actividad de corrección.',
                found_partner_id,
            )
            return

        # ── Obtener responsables configurados en el tipo de cita ─────────────
        correction_users = request.env['res.users'].sudo().browse([])
        if appointment_type_id:
            apt_type = request.env['appointment.type'].sudo().browse(appointment_type_id)
            if apt_type.exists():
                correction_users = apt_type.salon_correction_user_ids.filtered('active')

        # Fallback: administrador del sistema
        if not correction_users:
            admin_user = request.env.ref('base.user_admin', raise_if_not_found=False)
            if admin_user and admin_user.active:
                correction_users = admin_user
            else:
                correction_users = request.env['res.users'].sudo().browse(
                    request.env.user.id
                )

        # ── Construir nota HTML ───────────────────────────────────────────────
        note_parts = [
            f'El cliente con teléfono <strong>{phone}</strong> indicó que sus '
            f'datos registrados son incorrectos.<br/><br/>'
            f'<strong>Datos proporcionados por el cliente:</strong><br/>'
        ]
        if correction_name:
            note_parts.append(f'• Nombre correcto: <strong>{correction_name}</strong><br/>')
        if correction_email:
            note_parts.append(f'• Correo correcto: <strong>{correction_email}</strong><br/>')
        note_parts.append(
            '<br/>Por favor actualiza el contacto con la información indicada '
            'y confirma con el cliente.'
        )
        note = ''.join(note_parts)

        # ── Crear una actividad por cada responsable ──────────────────────────
        for user in correction_users:
            partner.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary='Corrección de datos solicitada por el cliente',
                note=note,
                user_id=user.id,
                date_deadline=date.today(),
            )
            _logger.info(
                'salon_customer_unifier: Actividad de corrección creada en '
                'Partner "%s" (ID %s) → asignada a "%s" — nombre: %r, email: %r',
                partner.name, partner.id, user.name, correction_name, correction_email,
            )

    def _assign_partner_to_cart(self, customer):
        """
        Asigna el partner resuelto por teléfono al carrito de eCommerce.
        Se llama DESPUÉS de super() porque website_appointment_sale crea
        el carrito dentro de _redirect_to_payment().
        """
        try:
            if not (hasattr(request, 'website') and request.website):
                return
            sale_order = request.website.sale_get_order()
            if not sale_order or not sale_order.exists():
                return
            if sale_order.partner_id.id == customer.id:
                _logger.debug(
                    'salon_customer_unifier: Carrito %s ya tiene el partner correcto (ID %s)',
                    sale_order.name, customer.id,
                )
                return
            sale_order.sudo().write({
                'partner_id': customer.id,
                'partner_invoice_id': customer.id,
                'partner_shipping_id': customer.id,
            })
            _logger.info(
                'salon_customer_unifier: Carrito %s → partner asignado: "%s" (ID %s)',
                sale_order.name, customer.name, customer.id,
            )
        except Exception as e:
            _logger.warning(
                'salon_customer_unifier: Error al asignar partner al carrito: %s', e,
            )
