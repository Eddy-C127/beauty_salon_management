from odoo import models, fields, api
from odoo.exceptions import UserError
import random
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    # ===== CAMPOS EXISTENTES =====
    real_employee_id = fields.Many2one(
        'hr.employee', 
        string="Real Employee", 
        domain="[('is_virtual_resource', '=', False)]", 
        tracking=True
    )
    
    appointment_status = fields.Selection([
        ('request', 'Request'),
        ('booked', 'Booked'),
        ('attended', 'Checked-In'),
        ('concluded', 'Concluded'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ], string="Appointment Status", compute='_compute_appointment_status', store=True, readonly=False, tracking=True)

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        readonly=True,
        help='Sale Order generated from this appointment',
        copy=False
    )

    has_sale_order = fields.Boolean(
        compute='_compute_has_sale_order',
        store=False,
        help='Technical field to control button visibility'
    )

    # ===== CAMPO NUEVO: CLIENTE MANUAL =====
    manual_customer_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        tracking=True,
        help='Cliente para citas manuales. Este campo alimenta el primer asistente.'
    )

    # ===== CAMPO NAME CON COMPUTE (ISSUE #1) =====
    name = fields.Char(
        string='Nombre de la reservación',
        compute='_compute_name',
        store=True,
        readonly=False,
        required=True
    )

    # ===== COMPUTE METHODS =====
    @api.depends('manual_customer_id', 'partner_id', 'appointment_type_id')
    def _compute_name(self):
        """
        ISSUE #1: Genera el nombre automáticamente
        Formato: {Cliente} - {Tipo de Cita}
        """
        for event in self:
            # Priorizar manual_customer_id para citas manuales, partner_id para website
            customer = event.manual_customer_id or event.partner_id
            
            if customer and event.appointment_type_id:
                event.name = f"{customer.name} - {event.appointment_type_id.name}"
            elif customer:
                event.name = customer.name
            elif event.appointment_type_id:
                event.name = event.appointment_type_id.name
            elif not event.name:
                event.name = 'Nueva Cita'

    @api.depends('appointment_type_id')
    def _compute_appointment_status(self):
        for event in self:
            if not event.appointment_type_id:
                event.appointment_status = False
            elif not event.appointment_status:
                event.appointment_status = 'booked'

    @api.depends('sale_order_id', 'sale_order_line_ids')
    def _compute_has_sale_order(self):
        """
        ISSUE #4: Detecta si ya existe una SO vinculada
        - Si tiene sale_order_id directo = SO creada manualmente
        - Si tiene sale_order_line_ids = SO del website
        """
        for event in self:
            event.has_sale_order = bool(event.sale_order_id) or bool(event.sale_order_line_ids)

    # ===== ONCHANGE METHODS =====
    @api.onchange('user_id')
    def onchange_user_id_real_employee(self):
        """Asigna el empleado real cuando se selecciona un usuario virtual"""
        if self.user_id and self.user_id.employee_id:
            if self.user_id.employee_id.is_virtual_resource:
                self.real_employee_id = self.user_id.employee_id.default_real_employee_id
            else:
                self.real_employee_id = self.user_id.employee_id

    @api.onchange('real_employee_id')
    def onchange_real_employee_id(self):
        """
        ISSUE #2: Al cambiar empleado real, asigna organizador virtual aleatorio
        
        NOTA: La actualización del vendedor en SO se hace en write() al guardar.
        Este onchange solo actualiza organizador/asistentes para feedback visual inmediato.
        """
        if self.real_employee_id:
            # Buscar empleados virtuales asociados al empleado real
            # ✅ FIX: Usar .sudo() para evitar redirección a hr.employee.public
            virtual_employees = self.env['hr.employee'].sudo().search([
                ('is_virtual_resource', '=', True),
                ('default_real_employee_id', '=', self.real_employee_id.id)
            ])
            
            # Seleccionar un empleado virtual aleatorio
            if virtual_employees:
                selected_virtual = random.choice(virtual_employees)
                self.user_id = selected_virtual.user_id
                _logger.info(f"Asignado organizador virtual aleatorio: {selected_virtual.name}")
            else:
                # Si no hay virtuales, usar el empleado real
                self.user_id = self.real_employee_id.user_id
                _logger.warning(f"No se encontraron empleados virtuales para {self.real_employee_id.name}, usando empleado real")
            
            # Actualizar asistentes solo en citas MANUALES
            if not self.sale_order_line_ids:
                self._update_attendees_manual()
            
            # ✅ FIX: Actualizar vendedor en SO con .sudo() para evitar regla "Personal Orders"
            if self.sale_order_line_ids:
                # Usar sudo() ANTES de acceder a order_id para evitar regla de lectura
                so = self.sale_order_line_ids.sudo()[0].order_id
                if so:
                    so.write({'user_id': self.real_employee_id.user_id.id})
                    _logger.info(
                        f'✅ Vendedor actualizado en SO #{so.name} (onchange): '
                        f'{self.real_employee_id.user_id.id}'
                    )

    @api.onchange('manual_customer_id')
    def onchange_manual_customer_id(self):
        """
        Al cambiar cliente manual, actualiza asistentes
        Solo para citas MANUALES
        """
        if self.manual_customer_id and not self.sale_order_line_ids:
            self._update_attendees_manual()
            # Sincronizar con partner_id para compatibilidad
            self.partner_id = self.manual_customer_id

    def _update_attendees_manual(self):
        """
        Actualiza la lista de asistentes SOLO para citas MANUALES
        Orden: 1. Cliente (manual_customer_id), 2. Organizador
        
        IMPORTANTE: Este método NO se ejecuta para citas del website
        """
        attendees = []
        
        # Primero el cliente manual
        if self.manual_customer_id:
            attendees.append(self.manual_customer_id.id)
        
        # Segundo el organizador (si es diferente al cliente)
        if self.user_id and self.user_id.partner_id:
            if self.user_id.partner_id.id not in attendees:
                attendees.append(self.user_id.partner_id.id)
        
        # Asignar lista de asistentes
        if attendees:
            self.partner_ids = [(6, 0, attendees)]
            _logger.info(f"Asistentes manuales actualizados: {attendees}")

# ===== OVERRIDE WRITE =====
    def write(self, vals):
        """
        Override write para:
        1. Actualizar vendedor en SO cuando cambia real_employee_id
        2. Mantener compatibilidad con flujos existentes
        """
        res = super(CalendarEvent, self).write(vals)
        
        # 🎯 NUEVO: Si cambió el empleado real, actualizar vendedor en SO
        if 'real_employee_id' in vals:
            for event in self:
                if not event.real_employee_id or not event.real_employee_id.user_id:
                    continue
                
                sale_order = None
                
                # Caso 1: Cita MANUAL con sale_order_id directo
                if event.sale_order_id:
                    sale_order = event.sale_order_id.sudo()
                
                # Caso 2: Cita WEBSITE con sale_order_line_ids
                elif event.sale_order_line_ids:
                    # Usar sudo() ANTES de acceder a order_id
                    sale_order = event.sale_order_line_ids.sudo()[0].order_id
                
                # ✅ FIX: Actualizar vendedor con .sudo() para evitar regla "Personal Orders"
                if sale_order:
                    sale_order.write({
                        'user_id': event.real_employee_id.user_id.id
                    })
                    _logger.info(
                        f'✅ Vendedor actualizado en SO #{sale_order.name}: '
                        f'{event.real_employee_id.user_id.name} (Cita #{event.id})'
                    )
        
        return res


    # ===== CRUD METHODS =====
    @api.model_create_multi
    def create(self, vals_list):
        """
        IMPORTANTE: Respetamos el flujo nativo de Odoo
        - Website: Odoo maneja todo (partner_id, asistentes, SO)
        - Manual: Solo agregamos empleado real y organizador virtual
        """
        events = super().create(vals_list)
        
        for event in events:
            # Asignar empleado real si viene de usuario virtual
            if event.user_id and event.user_id.employee_id:
                if event.user_id.employee_id.is_virtual_resource:
                    event.real_employee_id = event.user_id.employee_id.default_real_employee_id
                else:
                    event.real_employee_id = event.user_id.employee_id
            
            # NO tocar asistentes ni partner_id del website
            # Dejamos que Odoo maneje esto nativamente
            _logger.info(f"Cita creada: {event.name} - Partner: {event.partner_id.name if event.partner_id else 'Sin partner'} - Cliente Manual: {event.manual_customer_id.name if event.manual_customer_id else 'Sin cliente manual'}")
        
        return events

    # ===== ACTION METHODS =====
    def action_create_sale_order(self):
        """
        Crea una Sale Order desde el Calendar Event
        Usa manual_customer_id para citas manuales, partner_id para website
        
        Returns:
            dict: Acción para abrir la SO creada
        """
        self.ensure_one()

        # ===== VALIDACIONES =====
        if self.sale_order_id:
            return self.action_view_sale_order()

        # Determinar el cliente: manual_customer_id o partner_id
        customer = self.manual_customer_id or self.partner_id
        
        if not customer:
            raise UserError('Debe seleccionar un cliente para crear la orden de venta.')

        if not self.appointment_type_id:
            raise UserError('Debe seleccionar un tipo de cita para crear la orden de venta.')

        # ===== PREPARAR DATOS DE SALE ORDER =====
        salesperson = False
        if self.real_employee_id and self.real_employee_id.user_id:
            salesperson = self.real_employee_id.user_id.id
        elif self.user_id:
            salesperson = self.user_id.id

        warehouse = False
        if self.appointment_type_id.branch_id:
            warehouse = self.appointment_type_id.branch_id.id

        so_vals = {
            'partner_id': customer.id,
            'date_order': self.start or fields.Datetime.now(),
            'calendar_event_id': self.id,
            'user_id': salesperson,
        }

        if warehouse:
            so_vals['warehouse_id'] = warehouse
            so_vals['aux_branch_id'] = warehouse

        # ===== CREAR SALE ORDER =====
        sale_order = self.env['sale.order'].create(so_vals)

        # ===== CREAR SALE ORDER LINE =====
        product = self.appointment_type_id.product_id
        
        if not product:
            sale_order.unlink()
            raise UserError(
                f'El tipo de cita "{self.appointment_type_id.name}" no tiene un producto/servicio configurado.'
            )

        line_vals = {
            'order_id': sale_order.id,
            'product_id': product.id,
            'product_uom_qty': 1,
            'name': product.name or self.appointment_type_id.name,
        }

        self.env['sale.order.line'].create(line_vals)
        self.sale_order_id = sale_order.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_view_sale_order(self):
        """Abre la Sale Order vinculada"""
        self.ensure_one()
        
        if self.sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        if self.sale_order_line_ids:
            so = self.sale_order_line_ids[0].order_id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'res_id': so.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        raise UserError('Esta cita no tiene una orden de venta vinculada.')