# -*- coding: utf-8 -*-

from odoo import models, fields

import logging
_logger = logging.getLogger(__name__)


class AppointmentType(models.Model):
    """
    Extensión de appointment.type para controlar política de autenticación.
    """
    _inherit = 'appointment.type'
    
    require_login = fields.Boolean(
        string='Require Login to Book',
        default=False,
        help='If enabled, users must login or create an account before booking.\n'
             'This prevents duplicate contact creation and ensures better traceability.\n\n'
             '• Disabled: Users can book without login (may create duplicates)\n'
             '• Enabled: Users must authenticate first (recommended for paid services)'
    )