from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    aux_branch_id = fields.Many2one('stock.warehouse', string="Branch")
    
    # ===== NUEVO CAMPO =====
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Related Appointment',
        readonly=True,
        help='Appointment that generated this order',
        copy=False
    )

    @api.onchange('aux_branch_id')
    def onchange_aux_branch_id(self):
        if self.aux_branch_id:
            self.warehouse_id = self.aux_branch_id

    # ===== NUEVO MÉTODO =====
    def action_view_calendar_event(self):
        """
        Abre la cita vinculada a esta orden de venta
        
        Returns:
            dict: Acción para abrir el Calendar Event
        """
        self.ensure_one()
        
        if not self.calendar_event_id:
            raise UserError('Esta orden de venta no tiene una cita vinculada.')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointment',
            'res_model': 'calendar.event',
            'res_id': self.calendar_event_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        
        # Procesar solo líneas que vienen de calendar bookings (website)
        for line in lines:
            if line.calendar_booking_ids:
                booking = line.calendar_booking_ids[0]
                
                # Asignar empleado real si existe
                if booking.staff_user_id.employee_id.is_virtual_resource:
                    new_user = booking.staff_user_id.employee_id.default_real_employee_id.user_id
                else:
                    new_user = booking.staff_user_id
                
                # Asignar sucursal si existe
                branch = booking.appointment_type_id.branch_id
                
                # Actualizar la orden
                vals_to_write = {}
                if branch:
                    vals_to_write['aux_branch_id'] = branch.id
                if new_user:
                    vals_to_write['user_id'] = new_user.id
                
                if vals_to_write:
                    line.order_id.write(vals_to_write)
                    
                # 🎯 Vincular SO al calendar.event (citas website)
                # Usar relación directa line.calendar_event_id
                if line.calendar_event_id and not line.calendar_event_id.sale_order_id:
                    line.calendar_event_id.write({'sale_order_id': line.order_id.id})

        return lines