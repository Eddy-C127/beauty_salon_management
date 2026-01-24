# -*- coding: utf-8 -*-
import datetime
import werkzeug
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from math import ceil
from werkzeug.urls import url_encode

from odoo import Command, fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request,route
from odoo.tools import format_date, str2bool
from odoo.addons.website_sale.controllers import main as website_sale_portal

from odoo.addons.sale.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_PROGRESS_STATE, SUBSCRIPTION_CLOSED_STATE


class AppointmentPortal(payment_portal.PaymentPortal):


    # @http.route('/payment/transaction', type='json', auth='public')
    # def payment_transaction(self, amount, currency_id, partner_id, access_token, **kwargs):
    #     import ipdb; ipdb.set_trace()
    #     payment = super().payment_transaction(amount,currency_id,partner_id,access_token,**kwargs)
    #     return payment

    def _create_transaction(self, *args, **kwargs):
        # Obtención segura del sale_order_id
        sale_order_id = kwargs.get('sale_order_id')
        so = None
        
        if sale_order_id:
            so = http.request.env['sale.order'].browse(sale_order_id)
        elif hasattr(http.request, 'website') and http.request.website:
            # Fallback: obtener orden desde la sesión web (carrito activo)
            so = http.request.website.sale_get_order()
        
        # Crear transacción con el flujo estándar
        tx_sudo = super()._create_transaction(*args, **kwargs)
        
        # Si no hay orden válida, retornar transacción sin modificaciones
        if not so or not so.exists():
            return tx_sudo
        
        # Calcular el TOTAL de anticipos de TODAS las citas
        total_advance, advance_count = so._calculate_total_advance_amount()
        
        # Si hay anticipos, modificar el monto de la transacción
        if total_advance > 0:
            tx_sudo.write({'amount': total_advance})
        
        return tx_sudo


