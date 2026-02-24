# -*- coding: utf-8 -*-
import logging

from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class SalonWebsiteSale(WebsiteSale):
    """
    Override del controller de eCommerce para el flujo de citas de salón.

    PROBLEMA:
    Odoo exige validar la dirección del cliente (/shop/address) antes de
    permitir continuar al pago. Para órdenes de SERVICIO (citas), esto es
    innecesario — no hay envío y el cliente ya se identificó por teléfono.

    La validación de dirección ocurre en _check_addresses(), invocado desde:
      - shop_checkout()     → /shop/checkout
      - shop_confirm_order() → /shop/confirm_order
      - shop_payment()      → /shop/payment

    SOLUCIÓN:
    Saltamos _check_addresses() cuando la orden cumple AMBAS condiciones:
      1. only_services = True  (todos los productos son de tipo servicio)
      2. Tiene calendar_booking_ids  (es una orden de cita real, no eCommerce genérico)

    Esto garantiza que el fix NO afecta otras órdenes de eCommerce que no
    sean citas de salón.
    """

    def _check_addresses(self, order_sudo):
        """
        Override: salta validación de dirección para órdenes de citas de servicio.

        La condición doble (only_services + calendar_booking_ids) asegura que
        solo se aplica a órdenes generadas por website_appointment_sale, no a
        cualquier orden de servicio en el eCommerce.
        """
        if self._is_appointment_service_order(order_sudo):
            _logger.debug(
                'salon_customer_unifier: Saltando validación de dirección '
                'para orden de cita %s (only_services=%s)',
                order_sudo.name, order_sudo.only_services,
            )
            return None  # Sin redirección → continuar al checkout/pago
        return super()._check_addresses(order_sudo)

    def _is_appointment_service_order(self, order_sudo):
        """
        Determina si la orden es una orden de cita de servicio.

        Condiciones:
        - only_services=True (todos los productos son tipo 'service')
        - Al menos una línea tiene calendar_booking_ids (es una cita real)

        Protección: si website_appointment_sale no está instalado y el campo
        calendar_booking_ids no existe, retorna False sin romper nada.

        :param order_sudo: sale.order sudoed
        :return: bool
        """
        if not order_sudo or not order_sudo.only_services:
            return False
        try:
            return bool(
                order_sudo.order_line.filtered(lambda l: bool(l.calendar_booking_ids))
            )
        except AttributeError:
            # website_appointment_sale no instalado: calendar_booking_ids no existe
            return False
