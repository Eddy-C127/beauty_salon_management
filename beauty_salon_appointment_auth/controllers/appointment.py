# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.appointment.controllers.appointment import AppointmentController

class AppointmentControllerAuth(AppointmentController):

    @http.route()
    def appointment_type_id_form(self, *args, **kwargs):
        response = super().appointment_type_id_form(*args, **kwargs)
        # Disable caching for this page to prevent session leakage
        # when using user-dependent logic in the view (require_login check)
        if hasattr(response, 'headers'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        return response
