from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_virtual_resource = fields.Boolean()
    default_real_employee_id = fields.Many2one('hr.employee', string="Default Real Employee", domain="[('is_virtual_resource', '=', False)]", store=True)
