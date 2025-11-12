# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_fully_invoiced = fields.Datetime(
        string='Fully Invoiced Date',
        copy=False,
        readonly=True,
        tracking=True,
        help='Date and time when this order status changed to "Fully Invoiced"'
    )

    @api.depends('invoice_ids.state')
    def _compute_invoice_status(self):
        """
        Sobrescribir para capturar el momento exacto del cambio a 'invoiced'
        """
        # Guardar estados anteriores ANTES de calcular
        old_statuses = {order.id: order.invoice_status for order in self}
        
        # Ejecutar el cálculo nativo
        super(SaleOrder, self)._compute_invoice_status()
        
        # DESPUÉS del cálculo, detectar cambios
        for order in self:
            old_status = old_statuses.get(order.id)
            new_status = order.invoice_status
            
            # Si cambió a 'invoiced' y NO tiene fecha aún
            if new_status == 'invoiced' and old_status != 'invoiced':
                if not order.date_fully_invoiced:
                    # Capturar el momento exacto
                    order.date_fully_invoiced = fields.Datetime.now()
                    _logger.info(f"✅ {order.name} cambió a INVOICED - Fecha capturada: {order.date_fully_invoiced}")
            
            # Si cambió DE 'invoiced' a otro estado
            elif old_status == 'invoiced' and new_status != 'invoiced':
                if order.date_fully_invoiced:
                    order.date_fully_invoiced = False
                    _logger.info(f"🗑️ {order.name} ya NO está invoiced - Fecha limpiada")