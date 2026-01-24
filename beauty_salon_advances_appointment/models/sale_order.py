# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Verifica el monto de la transaccion con el total de la orden
    def _is_confirmation_amount_reached(self):
        if self.has_advance_appointment():
            return True
        else:
            res = super()._is_confirmation_amount_reached()
            return res

    def _compute_cart_info(self):
        super()._compute_cart_info()
        for order in self:
            if order.has_advance_appointment():
                order.only_services = True

    def _get_advance_appointment_line(self):
        """
        Busca y retorna la primera línea de orden que tenga una cita con anticipo configurado.
        Itera sobre TODAS las líneas para no depender de la posición [0].
        Retorna: sale.order.line recordset (puede estar vacío si no encuentra)
        """
        for line in self.order_line:
            if line.calendar_booking_ids:
                for booking in line.calendar_booking_ids:
                    if booking.appointment_type_id and booking.appointment_type_id.advance_type:
                        return line
        return self.env['sale.order.line']  # Retorna recordset vacío

    def _get_advance_appointment_type(self):
        """
        Retorna el appointment.type con anticipo configurado, o False si no existe.
        Método helper centralizado para evitar duplicación de código.
        NOTA: Este método retorna solo el PRIMER tipo de cita con anticipo.
        Para múltiples citas, usar _calculate_total_advance_amount()
        """
        line = self._get_advance_appointment_line()
        if line and line.calendar_booking_ids:
            for booking in line.calendar_booking_ids:
                if booking.appointment_type_id and booking.appointment_type_id.advance_type:
                    return booking.appointment_type_id
        return False

    def _calculate_total_advance_amount(self):
        """
        Calcula la SUMA de todos los anticipos de todas las citas en la orden.
        Soporta citas con anticipo por porcentaje y por importe fijo.
        
        Retorna: tuple (total_advance_amount, count_of_advances)
            - total_advance_amount: Suma total de todos los anticipos
            - count_of_advances: Número de citas con anticipo
        """
        total_advance = 0.0
        advance_count = 0
        
        for line in self.order_line:
            if not line.calendar_booking_ids:
                continue
                
            for booking in line.calendar_booking_ids:
                apt = booking.appointment_type_id
                if not apt or not apt.advance_type:
                    continue
                
                advance_amount = 0.0
                if apt.advance_type == 'advance_percentage':
                    # Calcular porcentaje sobre el subtotal de la línea (no del total de orden)
                    advance_amount = line.price_subtotal * (apt.advance_percentage / 100)
                elif apt.advance_type == 'fixed_import':
                    advance_amount = apt.fixed_import
                
                if advance_amount > 0:
                    total_advance += advance_amount
                    advance_count += 1
        
        return total_advance, advance_count

    def has_advance_appointment(self):
        """
        Verifica si la orden tiene al menos una cita con anticipo configurado.
        Usa el método centralizado para buscar en cualquier posición del carrito.
        """
        return bool(self._get_advance_appointment_type())