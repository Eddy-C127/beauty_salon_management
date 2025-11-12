# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    def unlink(self):
        """
        🛡️ PROTECCIÓN: Prevenir eliminación de líneas vinculadas a citas.
        
        Si una línea está vinculada a una cita, muestra error con instrucciones.
        """
        # Identificar líneas que tienen cita vinculada
        protected_lines = self.filtered('calendar_event_id')
        
        if protected_lines:
            # Obtener información de las citas
            appointments_info = []
            for line in protected_lines:
                event = line.calendar_event_id
                customer = event.manual_customer_id or event.partner_id
                customer_name = customer.name if customer else 'Sin cliente'
                service_name = event.appointment_type_id.name if event.appointment_type_id else 'Sin servicio'
                
                appointments_info.append(
                    f"• {customer_name} - {service_name} (Cita #{event.id})"
                )
            
            appointments_list = '\n'.join(appointments_info)
            
            raise UserError(_(
                '🚫 NO PUEDES ELIMINAR LÍNEAS VINCULADAS A CITAS\n\n'
                'Las siguientes líneas están vinculadas a citas activas:\n\n'
                '%s\n\n'
                '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                '✅ PROCESO CORRECTO PARA CAMBIAR SERVICIO:\n'
                '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
                '1️⃣ Ve a la CITA en el calendario\n'
                '2️⃣ Cambia el campo "Cita" (appointment_type_id) al servicio correcto\n'
                '3️⃣ GUARDA la cita\n'
                '4️⃣ Regresa a esta orden de venta\n'
                '5️⃣ Haz clic en el botón "🔄 ACTUALIZAR SERVICIO"\n\n'
                '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
                '⚠️ Este proceso mantiene el anticipo intacto y evita cancelar la cita.\n\n'
                '💡 Si realmente necesitas eliminar esta línea, primero desvincula '
                'la cita contactando al administrador del sistema.'
            ) % appointments_list)
        
        # Si no hay líneas protegidas, permitir eliminación normal
        return super(SaleOrderLine, self).unlink()