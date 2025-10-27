# -*- coding: utf-8 -*-

from urllib.parse import quote
from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers.main import AppointmentController

import logging
_logger = logging.getLogger(__name__)


class AppointmentControllerAuth(AppointmentController):
    """
    Override del controlador de appointment para forzar autenticación
    cuando el appointment type tiene require_login=True.
    """
    
    @http.route(['/appointment/<int:appointment_type_id>/info'],
                type='http', auth="public", website=True, sitemap=False)
    def appointment_type_id_form(self, appointment_type_id, date_time, duration, 
                                  staff_user_id=None, resource_selected_id=None, 
                                  available_resource_ids=None, asked_capacity=1, **kwargs):
        """
        Override: Verifica si el appointment type requiere login.
        Si es así y el usuario es público, redirige a login/signup.
        """
        
        # ========================================
        # PASO 1: Obtener appointment type
        # ========================================
        domain = self._appointments_base_domain(
            filter_appointment_type_ids=kwargs.get('filter_appointment_type_ids'),
            search=kwargs.get('search'),
            invite_token=kwargs.get('invite_token')
        )
        
        available_appointments = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('filter_resource_ids'),
            kwargs.get('invite_token'),
            domain=domain,
        )
        
        appointment_type = available_appointments.filtered(
            lambda appt: appt.id == int(appointment_type_id)
        )
        
        if not appointment_type:
            from werkzeug.exceptions import NotFound
            raise NotFound()
        
        # ========================================
        # PASO 2: ⭐ NUEVA LÓGICA - Verificar autenticación
        # ========================================
        if appointment_type.require_login and request.env.user._is_public():
            # Usuario público intentando acceder a appointment que requiere login
            
            # Construir URL de retorno con TODOS los parámetros
            # Odoo se encargará de redirigir aquí después del login
            redirect_url = quote(request.httprequest.full_path)
            
            _logger.info(
                f'🔒 Appointment type "{appointment_type.name}" requires login. '
                f'Redirecting public user to signup/login. '
                f'Return URL: {redirect_url}'
            )
            
            # Redirigir a página de signup
            # Nota: Usamos /web/signup en lugar de /web/login para dar
            # prioridad a crear cuenta nueva (mejora UX para clientes nuevos)
            return request.redirect(f'/web/signup?redirect={redirect_url}')
        
        # ========================================
        # PASO 3: Continuar flujo normal (usuario autenticado o no requiere login)
        # ========================================
        return super().appointment_type_id_form(
            appointment_type_id, date_time, duration,
            staff_user_id=staff_user_id,
            resource_selected_id=resource_selected_id,
            available_resource_ids=available_resource_ids,
            asked_capacity=asked_capacity,
            **kwargs
        )