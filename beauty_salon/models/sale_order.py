from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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
    def action_sync_service_from_appointment(self):
        """
        🔄 Sincroniza servicios desde citas cuando el appointment_type_id cambió.
        
        PROCESO:
        1. Identifica líneas vinculadas a citas
        2. Verifica si el servicio de la cita cambió vs el producto de la línea
        3. Elimina la línea vieja
        4. Crea una nueva línea con el servicio correcto
        5. Mantiene el anticipo intacto (no se toca)
        6. Registra todo en el chatter
        
        VENTAJA: Al eliminar-recrear evitamos que Odoo cancele la cita automáticamente
        (que es lo que pasa si usamos write() en product_id)
        """
        self.ensure_one()
        
        # 🆕 VALIDACIÓN: Solo permitir en órdenes en borrador o cotización
        if self.state not in ['draft', 'sent']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '⚠️ Orden Confirmada',
                    'message': (
                        'No se puede actualizar servicios en órdenes confirmadas.\n\n'
                        '✅ PROCESO:\n'
                        '1. Cancela la orden\n'
                        '2. Restablece a borrador\n'
                        '3. Actualiza el servicio\n'
                        '4. Vuelve a confirmar\n\n'
                        '💡 El anticipo se mantendrá intacto.'
                    ),
                    'type': 'warning',
                    'sticky': True,
                }
            }
            
        synced_lines = []
        errors = []
        no_changes = []
        
        # Buscar líneas vinculadas a citas
        lines_with_appointments = self.order_line.filtered('calendar_event_id')
        
        if not lines_with_appointments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin Citas Vinculadas',
                    'message': 'Esta orden no tiene líneas vinculadas a citas.',
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        for line in lines_with_appointments:
            event = line.calendar_event_id
            
            # Validación 1: Cita tiene appointment_type_id
            if not event.appointment_type_id:
                errors.append({
                    'event_id': event.id,
                    'customer': (event.manual_customer_id or event.partner_id).name if (event.manual_customer_id or event.partner_id) else 'Sin cliente',
                    'error': 'No tiene tipo de cita asignado'
                })
                continue
            
            # Validación 2: Appointment type tiene producto
            correct_product = event.appointment_type_id.product_id
            if not correct_product:
                errors.append({
                    'event_id': event.id,
                    'customer': (event.manual_customer_id or event.partner_id).name if (event.manual_customer_id or event.partner_id) else 'Sin cliente',
                    'error': f'El tipo de cita "{event.appointment_type_id.name}" no tiene producto configurado'
                })
                continue
            
            # Verificar si hay cambio
            if line.product_id == correct_product:
                no_changes.append({
                    'event_id': event.id,
                    'customer': (event.manual_customer_id or event.partner_id).name if (event.manual_customer_id or event.partner_id) else 'Sin cliente',
                    'service': correct_product.name,
                })
                continue
            
            # ✅ HAY CAMBIO: Procesar
            old_product_name = line.product_id.name
            old_price = line.price_unit
            old_line_id = line.id
            
            # Preparar valores para nueva línea
            new_line_vals = {
                'order_id': self.id,
                'product_id': correct_product.id,
                'product_uom_qty': line.product_uom_qty,
                'name': correct_product.name or event.appointment_type_id.name,
                'calendar_event_id': event.id,
                'sequence': line.sequence,
            }
            
            # CRÍTICO: Remover calendar_event_id de la línea vieja ANTES de eliminar
            # para evitar que la protección la bloquee
            line.calendar_event_id = False
            
            # Eliminar línea vieja
            line.unlink()
            
           # Crear línea nueva (Odoo 18 calcula precio automáticamente)
            new_line = self.env['sale.order.line'].create(new_line_vals)
            
            # Forzar recalculo de precio y descripción
            new_line._compute_price_unit()
            if hasattr(new_line, '_compute_name'):
                new_line._compute_name()
            
            synced_lines.append({
                'event_id': event.id,
                'customer': (event.manual_customer_id or event.partner_id).name if (event.manual_customer_id or event.partner_id) else 'Sin cliente',
                'old_product': old_product_name,
                'new_product': correct_product.name,
                'old_price': old_price,
                'new_price': new_line.price_unit,
                'old_line_id': old_line_id,
                'new_line_id': new_line.id,
            })
            
            _logger.info(
                f'✅ Servicio actualizado en SO #{self.name}: '
                f'{old_product_name} (${old_price:.2f}) → {correct_product.name} (${new_line.price_unit:.2f}) '
                f'[Línea #{old_line_id} eliminada, #{new_line.id} creada]'
            )
        
        # ═══════════════════════════════════════════
        # REGISTRAR EN CHATTER
        # ═══════════════════════════════════════════
        
        if synced_lines or errors or no_changes:
            message = '<div style="font-family: Arial, sans-serif;">'
            message += '<h3 style="color: #0066cc; margin-bottom: 10px;">🔄 Sincronización de Servicios desde Citas</h3>'
            
            # Servicios actualizados
            if synced_lines:
                message += '<div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 10px; margin-bottom: 10px;">'
                message += f'<p style="margin: 0 0 10px 0;"><strong>✅ {len(synced_lines)} Servicio(s) Actualizado(s)</strong></p>'
                message += '<ul style="margin: 0; padding-left: 20px;">'
                for item in synced_lines:
                    price_diff = item['new_price'] - item['old_price']
                    price_indicator = f'<span style="color: {"green" if price_diff > 0 else "red"};">({price_diff:+.2f})</span>' if price_diff != 0 else ''
                    
                    message += (
                        f'<li style="margin-bottom: 5px;">'
                        f'<strong>Cita #{item["event_id"]}</strong> - {item["customer"]}<br/>'
                        f'<span style="text-decoration: line-through; color: #666;">{item["old_product"]} (${item["old_price"]:.2f})</span> → '
                        f'<span style="color: #28a745; font-weight: bold;">{item["new_product"]} (${item["new_price"]:.2f})</span> {price_indicator}'
                        f'</li>'
                    )
                message += '</ul></div>'
            
            # Sin cambios
            if no_changes:
                message += '<div style="background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 10px; margin-bottom: 10px;">'
                message += f'<p style="margin: 0 0 10px 0;"><strong>ℹ️ {len(no_changes)} Servicio(s) Ya Sincronizado(s)</strong></p>'
                message += '<ul style="margin: 0; padding-left: 20px;">'
                for item in no_changes:
                    message += (
                        f'<li>Cita #{item["event_id"]} - {item["customer"]}: '
                        f'{item["service"]} (sin cambios)</li>'
                    )
                message += '</ul></div>'
            
            # Errores
            if errors:
                message += '<div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin-bottom: 10px;">'
                message += f'<p style="margin: 0 0 10px 0;"><strong>⚠️ {len(errors)} Error(es)</strong></p>'
                message += '<ul style="margin: 0; padding-left: 20px;">'
                for error in errors:
                    message += (
                        f'<li>Cita #{error["event_id"]} - {error["customer"]}: '
                        f'{error["error"]}</li>'
                    )
                message += '</ul></div>'
            
            message += '</div>'
            
            self.message_post(
                body=message,
                subject='🔄 Servicios Sincronizados desde Citas',
                message_type='notification',
            )
        
        # ═══════════════════════════════════════════
        # NOTIFICACIÓN AL USUARIO
        # ═══════════════════════════════════════════
        
        if synced_lines and not errors:
            message_text = f'✅ {len(synced_lines)} servicio(s) actualizado(s) correctamente'
            notification_type = 'success'
        elif synced_lines and errors:
            message_text = f'⚠️ {len(synced_lines)} actualizado(s), {len(errors)} error(es)'
            notification_type = 'warning'
        elif errors:
            message_text = f'❌ No se pudo actualizar ningún servicio. {len(errors)} error(es)'
            notification_type = 'danger'
        else:
            message_text = '✓ Todos los servicios ya están sincronizados'
            notification_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sincronización de Servicios',
                'message': message_text,
                'type': notification_type,
                'sticky': False,
            }
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