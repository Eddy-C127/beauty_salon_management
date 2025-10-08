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
        so = http.request.env['sale.order'].browse(kwargs['sale_order_id'])
        tx_sudo = super()._create_transaction(
            *args, **kwargs
        )
        calendar_booking_ids = so.order_line[0].calendar_booking_ids
        if calendar_booking_ids and calendar_booking_ids.appointment_type_id:
            appointment_type_id = calendar_booking_ids.appointment_type_id
            if appointment_type_id and appointment_type_id.advance_percentage:
                amount = tx_sudo.amount*(appointment_type_id.advance_percentage/100)
                tx_sudo.write({
                    'amount': amount 
                })
        return tx_sudo


