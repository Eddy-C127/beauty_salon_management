from odoo import models, fields

class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    branch_id = fields.Many2one('stock.warehouse', string='Branch', help='Warehouse used to manage the stock of products consumed during the appointment.')
