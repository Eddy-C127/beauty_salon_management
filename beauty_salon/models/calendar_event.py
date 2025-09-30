from odoo import models, fields, api

class CalendarVent(models.Model):
    _inherit = 'calendar.event'

    real_employee_id = fields.Many2one('hr.employee', string="Real Employee", domain="[('is_virtual_resource', '=', False)]", tracking=True, )
    appointment_status = fields.Selection([
        ('request', 'Request'),
        ('booked', 'Booked'),
        ('attended', 'Checked-In'),
        ('concluded', 'Concluded'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ], string="Appointment Status", compute='_compute_appointment_status', store=True, readonly=False, tracking=True)

    @api.depends('appointment_type_id')
    def _compute_appointment_status(self):
        for event in self:
            if not event.appointment_type_id:
                event.appointment_status = False
            elif not event.appointment_status:
                event.appointment_status = 'booked'

    @api.onchange('user_id')
    def onchange_user_id_real_employee(self):
        if self.user_id and self.user_id.employee_id and self.user_id.employee_id.is_virtual_resource:
            self.real_employee_id = self.user_id.employee_id.default_real_employee_id
        else:
            self.real_employee_id = self.user_id.employee_id

    @api.onchange('real_employee_id')
    def onchange_real_employee_id(self):
        # ✅ Verificar que existan líneas de orden antes de acceder
        if self.real_employee_id and self.sale_order_line_ids:
            so = self.sale_order_line_ids[0].order_id
            if so:
                so.write({'user_id': self.real_employee_id.user_id.id})

    @api.model_create_multi
    def create(self, values):
        result = super().create(values)
        if result.user_id and result.user_id.employee_id and result.user_id.employee_id.is_virtual_resource:
            result.real_employee_id = result.user_id.employee_id.default_real_employee_id
        else:
            result.real_employee_id = result.user_id.employee_id
        return result