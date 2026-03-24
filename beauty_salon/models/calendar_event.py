from odoo import models, fields, api
from odoo.exceptions import UserError
import random
import logging
from datetime import datetime, timedelta

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

    # ===== CAMPOS TÉCNICOS: BÚSQUEDA DE SLOTS =====
    slot_search_date = fields.Date(
        string='Buscar disponibilidad para el día',
        store=True,
        help='Selecciona un día para ver los slots disponibles del empleado asignado'
    )

    available_slot_ids = fields.Many2many(
        'beauty_salon.event_slot_line',
        'calendar_event_slot_rel',
        'event_id',
        'slot_id',
        string='Slots disponibles',
        compute='_compute_available_slots',
        store=False,
    )

    selected_slot_id = fields.Many2one(
        'beauty_salon.event_slot_line',
        string='Horario disponible',
        store=False,
    )

    no_slots_message = fields.Char(
        string='',
        compute='_compute_no_slots_message',
        store=False,
    )

    overlap_warning = fields.Char(
        string='',
        store=False,
        readonly=True,
    )

    # ===== COMPUTE METHODS =====

    @api.depends('slot_search_date', 'available_slot_ids')
    def _compute_no_slots_message(self):
        for event in self:
            if event.slot_search_date and not event.available_slot_ids:
                date_fmt = event.slot_search_date.strftime('%d/%m/%Y')
                apt_name = event.appointment_type_id.name if event.appointment_type_id else 'este servicio'
                event.no_slots_message = f'Sin espacios disponibles para {apt_name} el {date_fmt}.'
            else:
                event.no_slots_message = False

    @api.depends('slot_search_date', 'real_employee_id', 'appointment_type_id')
    def _compute_available_slots(self):
        """
        Calcula los slots disponibles en tiempo real.
        store=False → se recalcula cada vez que se abre el form o cambian los campos.
        No persiste en DB — siempre frescos.
        """
        for event in self:
            event.available_slot_ids = self.env['beauty_salon.event_slot_line']

            if not event.slot_search_date or not event.appointment_type_id or not event.real_employee_id:
                continue

            tz = event.appointment_type_id.appointment_tz or 'America/Monterrey'
            date_str = event.slot_search_date.strftime('%Y-%m-%d')

            try:
                slots = self.get_available_slots_for_day(
                    event.appointment_type_id.id,
                    event.real_employee_id.id,
                    date_str,
                    timezone=tz,
                )
            except Exception as e:
                _logger.warning(f"Error calculando slots para cita {event.id}: {e}")
                continue

            if slots:
                # Deduplicar por slot_start antes de crear registros
                seen = set()
                unique_slots = []
                for slot in slots:
                    if slot['start'] not in seen:
                        seen.add(slot['start'])
                        unique_slots.append(slot)

                slot_records = self.env['beauty_salon.event_slot_line'].create([{
                    'slot_start': slot['start'],
                    'slot_label': slot['label'],
                } for slot in unique_slots])
                event.available_slot_ids = slot_records

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

    @api.onchange('appointment_type_id')
    def onchange_appointment_type_id(self):
        """
        COMPONENTE B: Al seleccionar tipo de cita, auto-asigna el empleado real disponible.
        - Si hay 1 empleado → lo asigna directo
        - Si hay varios → asigna el de menor carga (menos citas en próximos 7 días)
        - La cascada a user_id y organizador la maneja onchange_real_employee_id
        """
        if not self.appointment_type_id:
            return

        apt_type = self.appointment_type_id
        staff_users = apt_type.staff_user_ids

        if not staff_users:
            return

        # Filtrar: solo empleados reales (no virtuales) asociados a los staff_users
        real_employees = self.env['hr.employee'].sudo().search([
            ('user_id', 'in', staff_users.ids),
            ('is_virtual_resource', '=', False),
            ('active', '=', True),
        ])

        if not real_employees:
            # Fallback: asignar el primer staff_user; el onchange de user_id resolverá el real
            self.user_id = staff_users[0]
            return

        if len(real_employees) == 1:
            self.real_employee_id = real_employees[0]
        else:
            # Selección por menor carga: contar citas futuras por empleado (próximos 7 días)
            now = datetime.now()
            week_later = now + timedelta(days=7)

            best_employee = None
            min_events = float('inf')

            for emp in real_employees:
                if not emp.user_id:
                    continue
                count = self.env['calendar.event'].sudo().search_count([
                    ('real_employee_id', '=', emp.id),
                    ('start', '>=', now),
                    ('start', '<=', week_later),
                    ('appointment_status', 'not in', ['cancelled']),
                ])
                if count < min_events:
                    min_events = count
                    best_employee = emp

            if best_employee:
                self.real_employee_id = best_employee
            else:
                self.real_employee_id = real_employees[0]

        # La cascada a user_id y organizador la dispara onchange_real_employee_id automáticamente

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
        ISSUE #2: Al cambiar empleado real, asigna organizador virtual aleatorio.
        COMPONENTE A: También sincroniza partner_ids para citas de website.

        NOTA: La actualización del vendedor en SO se hace en write() al guardar.
        Este onchange solo actualiza organizador/asistentes para feedback visual inmediato.
        """
        if self.real_employee_id:
            # Buscar empleados virtuales asociados al empleado real
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

            # Actualizar asistentes
            if not self.sale_order_line_ids:
                # Cita MANUAL: reconstruir lista completa
                self._update_attendees_manual()
            else:
                # Cita WEBSITE: reemplazar solo el partner del empleado anterior
                old_employee = self._origin.real_employee_id
                self._replace_employee_in_attendees(old_employee, self.real_employee_id)

            # Actualizar vendedor en SO con .sudo() para evitar regla "Personal Orders"
            if self.sale_order_line_ids:
                so = self.sale_order_line_ids.sudo()[0].order_id
                if so:
                    so.write({'user_id': self.real_employee_id.user_id.id})
                    _logger.info(
                        f'✅ Vendedor actualizado en SO #{so.name} (onchange): '
                        f'{self.real_employee_id.user_id.id}'
                    )

    @api.onchange('real_employee_id', 'start', 'stop')
    def onchange_check_overlap_warning(self):
        """Muestra advertencia visual si el empleado ya tiene una cita en ese horario."""
        self.overlap_warning = False
        if not self.real_employee_id or not self.start or not self.stop:
            return
        if hasattr(self.start, 'year') and self.start.year >= 2099:
            return
        exclude_id = self._origin.id if self._origin and self._origin.id else False
        conflict = self._check_employee_overlap(
            self.real_employee_id.id, self.start, self.stop, exclude_id=exclude_id
        )
        if conflict:
            customer = conflict.manual_customer_id or conflict.partner_id
            import pytz as _pytz
            try:
                tz = _pytz.timezone('America/Monterrey')
                start_local = _pytz.utc.localize(conflict.start).astimezone(tz)
                fecha = start_local.strftime('%d/%m/%Y %H:%M')
            except Exception:
                fecha = str(conflict.start)
            self.overlap_warning = (
                f'⚠️  Horario ocupado — "{conflict.name}" '
                f'({customer.name if customer else "sin cliente"}) · {fecha}'
            )

    @api.onchange('slot_search_date', 'real_employee_id', 'appointment_type_id')
    def onchange_slot_search_date(self):
        """
        Limpia la selección anterior cuando cambia la fecha/empleado/tipo.
        Los slots se recalculan automáticamente via _compute_available_slots.
        """
        self.selected_slot_id = False

    @api.onchange('selected_slot_id')
    def onchange_selected_slot_id(self):
        """
        Al seleccionar un slot, escribe start/stop en memoria y limpia la búsqueda.
        Limpiar slot_search_date hace que los radios desaparezcan y el compute
        ya no genere slots — señal visual de que el horario quedó seleccionado.
        """
        if not self.selected_slot_id:
            return

        apt_type = self.appointment_type_id
        duration_hours = apt_type.appointment_duration if apt_type else 1.0
        slot_start = self.selected_slot_id.slot_start
        slot_stop = slot_start + timedelta(hours=duration_hours)

        self.start = slot_start
        self.stop = slot_stop
        # Limpiar búsqueda → oculta los radios, señal de que ya se eligió el slot
        self.slot_search_date = False
        self.selected_slot_id = False

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

    # ===== HELPER METHODS =====

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

    def _replace_employee_in_attendees(self, old_employee, new_employee):
        """
        COMPONENTE A: Reemplaza el partner del empleado anterior por el nuevo en partner_ids.
        Usado en citas de WEBSITE al reasignar real_employee_id.

        Args:
            old_employee: hr.employee anterior (puede ser vacío en primera asignación)
            new_employee: hr.employee nuevo
        """
        if not new_employee or not new_employee.user_id or not new_employee.user_id.partner_id:
            return

        new_partner = new_employee.user_id.partner_id
        commands = []

        # Eliminar partner del empleado anterior si existe
        if old_employee and old_employee.user_id and old_employee.user_id.partner_id:
            old_partner = old_employee.user_id.partner_id
            if old_partner.id != new_partner.id:
                commands.append((3, old_partner.id))
                _logger.info(f"Removiendo asistente anterior: {old_partner.name}")

        # Agregar partner del nuevo empleado si no está ya
        current_partner_ids = self.partner_ids.ids if self.partner_ids else []
        if new_partner.id not in current_partner_ids:
            commands.append((4, new_partner.id))
            _logger.info(f"Agregando nuevo asistente: {new_partner.name}")

        if commands:
            self.partner_ids = commands

    def _check_employee_overlap(self, real_employee_id, start, stop, exclude_id=None):
        """
        COMPONENTE D: Verifica si el empleado real ya tiene una cita en ese rango horario.

        Returns:
            calendar.event: el evento conflictivo, o False si no hay solapamiento
        """
        domain = [
            ('real_employee_id', '=', real_employee_id),
            ('start', '<', stop),
            ('stop', '>', start),
            ('appointment_status', 'not in', ['cancelled']),
        ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))

        return self.env['calendar.event'].sudo().search(domain, limit=1)

    def _format_conflict_message(self, conflict):
        """
        Formatea el mensaje de solapamiento con la hora en TZ local (America/Monterrey).
        conflict.start está en UTC naive — se convierte a local para mostrar.
        """
        import pytz as _pytz
        customer = conflict.manual_customer_id or conflict.partner_id
        customer_name = customer.name if customer else 'sin cliente'

        # Convertir UTC naive → TZ local
        tz_name = 'America/Monterrey'
        try:
            local_tz = _pytz.timezone(tz_name)
            start_utc = _pytz.utc.localize(conflict.start)
            start_local = start_utc.astimezone(local_tz)
            fecha_hora = start_local.strftime('%d/%m/%Y %H:%M')
        except Exception:
            fecha_hora = conflict.start.strftime('%d/%m/%Y %H:%M') + ' (UTC)'

        return (
            f'Esta cita se solapa con:\n\n'
            f'"{conflict.name}"\n'
            f'Cliente: {customer_name}\n'
            f'Hora: {fecha_hora}'
        )

    # ===== SLOT AVAILABILITY (COMPONENTE C) =====

    @api.model
    def get_available_slots_for_day(self, appointment_type_id, real_employee_id, selected_date_str, timezone='America/Monterrey'):
        """
        COMPONENTE C: Retorna los slots disponibles para un día específico.
        Reutiliza _get_appointment_slots() nativo de appointment.type.

        Args:
            appointment_type_id (int): ID del appointment.type
            real_employee_id (int): ID del hr.employee real
            selected_date_str (str): Fecha en formato 'YYYY-MM-DD'
            timezone (str): Timezone del negocio

        Returns:
            list: [{'start': 'YYYY-MM-DD HH:MM:SS', 'label': 'HH:MM'}, ...]
        """
        import pytz

        apt_type = self.env['appointment.type'].browse(appointment_type_id)
        employee = self.env['hr.employee'].sudo().browse(real_employee_id)

        if not apt_type.exists() or not employee.exists() or not employee.user_id:
            return []

        try:
            tz = pytz.timezone(timezone)
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')

            # reference_date en UTC naive:
            # - Si el día buscado es HOY → usar utcnow() para que Odoo filtre slots pasados
            #   (igual que el sitio web, que no pasa reference_date y usa datetime.utcnow())
            # - Si el día es FUTURO → inicio del día en TZ local para mostrar todos sus slots
            today_local = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz).date()
            if selected_date.date() <= today_local:
                reference_date_utc = datetime.utcnow()
            else:
                day_start_local = tz.localize(selected_date.replace(hour=0, minute=0, second=0))
                reference_date_utc = day_start_local.astimezone(pytz.utc).replace(tzinfo=None)

            # Usar método nativo con filter_users del empleado real
            slots_calendar = apt_type._get_appointment_slots(
                timezone=timezone,
                filter_users=employee.user_id,
                reference_date=reference_date_utc,
            )
        except Exception as e:
            _logger.error(f"Error obteniendo slots para cita {appointment_type_id}: {e}")
            return []

        # Extraer solo los slots del día seleccionado
        # slot['datetime'] es un STRING 'YYYY-MM-DD HH:MM:SS' en la TZ del appointment type
        target_date_str = selected_date.strftime('%Y-%m-%d')
        result = []

        for month_data in slots_calendar:
            for week in month_data.get('weeks', []):
                for day_data in week:
                    if not day_data.get('slots'):
                        continue
                    for slot in day_data['slots']:
                        slot_dt_str = slot.get('datetime')
                        if not slot_dt_str:
                            continue
                        # Es un string — parsear directamente
                        if isinstance(slot_dt_str, str):
                            slot_naive = datetime.strptime(slot_dt_str, '%Y-%m-%d %H:%M:%S')
                        else:
                            # Por si acaso retorna datetime en alguna versión
                            slot_naive = slot_dt_str.replace(tzinfo=None) if slot_dt_str.tzinfo else slot_dt_str

                        if slot_naive.strftime('%Y-%m-%d') == target_date_str:
                            # start_hour es el label formateado por Odoo (ej: "1:30 p. m.")
                            label = slot.get('start_hour') or slot_naive.strftime('%H:%M')
                            # Convertir de TZ local a UTC para que Odoo lo almacene correctamente
                            slot_local_aware = tz.localize(slot_naive)
                            slot_utc = slot_local_aware.astimezone(pytz.utc).replace(tzinfo=None)
                            result.append({
                                'start': slot_utc.strftime('%Y-%m-%d %H:%M:%S'),
                                'label': label,
                            })

        _logger.info(f"Slots disponibles para empleado {employee.name} el {target_date_str}: {len(result)} slots")
        return result

# ===== OVERRIDE WRITE =====
    def write(self, vals):
        """
        Override write para:
        1. Validar que no se guarde con fecha placeholder 2099 (Componente C)
        2. Validar solapamiento de horario (Componente D) — ANTES del super()
        3. Sincronizar partner_ids al cambiar real_employee_id (Componente A)
        4. Actualizar vendedor en SO cuando cambia real_employee_id
        """
        # COMPONENTE C: Bloquear guardado con fecha placeholder 2099
        # Solo aplica cuando 'start' viene explícitamente en vals (el usuario está cambiando la fecha)
        # No aplica a ediciones de otros campos (duración, cliente, etc.)
        start_in_vals = vals.get('start')
        if start_in_vals and not self.env.context.get('skip_overlap_check'):
            check_dt = start_in_vals if isinstance(start_in_vals, datetime) else datetime.fromisoformat(str(start_in_vals))
            if check_dt.year >= 2099:
                raise UserError(
                    'Debes seleccionar un horario disponible antes de guardar.\n\n'
                    'Usa el campo "Buscar disponibilidad para el día" para elegir un slot.'
                )

        # COMPONENTE A: Capturar empleado anterior ANTES del super() para poder comparar
        old_employees = {}
        if 'real_employee_id' in vals:
            for event in self:
                old_employees[event.id] = event.real_employee_id

        res = super(CalendarEvent, self).write(vals)

        # COMPONENTE A + vendedor SO: post-write, sincronizar partner_ids y SO
        if 'real_employee_id' in vals:
            for event in self:
                if not event.real_employee_id or not event.real_employee_id.user_id:
                    continue

                old_employee = old_employees.get(event.id)

                # Sincronizar partner_ids para citas de website (las manuales ya lo hacen via onchange)
                if event.sale_order_line_ids:
                    event._replace_employee_in_attendees_db(old_employee, event.real_employee_id)

                sale_order = None

                # Caso 1: Cita MANUAL con sale_order_id directo
                if event.sale_order_id:
                    sale_order = event.sale_order_id.sudo()

                # Caso 2: Cita WEBSITE con sale_order_line_ids
                elif event.sale_order_line_ids:
                    sale_order = event.sale_order_line_ids.sudo()[0].order_id

                if sale_order:
                    sale_order.write({
                        'user_id': event.real_employee_id.user_id.id
                    })
                    _logger.info(
                        f'✅ Vendedor actualizado en SO #{sale_order.name}: '
                        f'{event.real_employee_id.user_id.name} (Cita #{event.id})'
                    )

        return res

    def _replace_employee_in_attendees_db(self, old_employee, new_employee):
        """
        COMPONENTE A (versión DB): Reemplaza partner en partner_ids usando write() real.
        Esta versión se llama desde write() donde ya tenemos el ID de la DB.

        Args:
            old_employee: hr.employee anterior
            new_employee: hr.employee nuevo
        """
        if not new_employee or not new_employee.user_id or not new_employee.user_id.partner_id:
            return

        new_partner = new_employee.user_id.partner_id
        commands = []

        # Eliminar partner del empleado anterior si existe y es diferente
        if old_employee and old_employee.user_id and old_employee.user_id.partner_id:
            old_partner = old_employee.user_id.partner_id
            if old_partner.id != new_partner.id:
                current_ids = self.partner_ids.ids
                if old_partner.id in current_ids:
                    commands.append((3, old_partner.id))
                    _logger.info(f"[write] Removiendo asistente anterior: {old_partner.name} de cita #{self.id}")

        # Agregar partner del nuevo empleado si no está ya
        current_ids = self.partner_ids.ids
        if new_partner.id not in current_ids:
            commands.append((4, new_partner.id))
            _logger.info(f"[write] Agregando nuevo asistente: {new_partner.name} a cita #{self.id}")

        if commands:
            # Usar super().write() directo para evitar recursión
            super(CalendarEvent, self).write({'partner_ids': commands})


    # ===== CRUD METHODS =====
    @api.model_create_multi
    def create(self, vals_list):
        """
        IMPORTANTE: Respetamos el flujo nativo de Odoo
        - Website: Odoo maneja todo (partner_id, asistentes, SO)
        - Manual: Solo agregamos empleado real y organizador virtual

        COMPONENTE D: Valida solapamiento al crear.
        """
        # COMPONENTE C: Default start/stop si no vienen (auto-save de Odoo antes del slot wizard)
        # Odoo requiere start/stop obligatorios; el wizard de slots los sobreescribirá después.
        # El default es far-future para evitar falsos solapamientos con citas reales.
        for vals in vals_list:
            if not vals.get('start') or not vals.get('stop'):
                from datetime import date, time
                far_future = datetime.combine(
                    date(2099, 12, 31),
                    time(0, 0)
                )
                vals.setdefault('start', far_future)
                vals.setdefault('stop', far_future + timedelta(hours=1))

        events = super().create(vals_list)

        for event in events:
            # Asignar empleado real si viene de usuario virtual
            if event.user_id and event.user_id.employee_id:
                if event.user_id.employee_id.is_virtual_resource:
                    event.real_employee_id = event.user_id.employee_id.default_real_employee_id
                else:
                    event.real_employee_id = event.user_id.employee_id

            # Asegurar que el cliente sea seguidor para que las automatizaciones funcionen
            partners_to_subscribe = []

            # 1. Intentar con cliente manual
            if event.manual_customer_id:
                partners_to_subscribe.append(event.manual_customer_id.id)

            # 2. Si no, buscar en asistentes (excluyendo personal)
            elif event.partner_ids:
                staff_partners = set()
                if event.user_id and event.user_id.partner_id:
                    staff_partners.add(event.user_id.partner_id.id)
                if event.real_employee_id and event.real_employee_id.user_id and event.real_employee_id.user_id.partner_id:
                    if event.real_employee_id.user_id.partner_id:
                         staff_partners.add(event.real_employee_id.user_id.partner_id.id)

                for partner in event.partner_ids:
                    if partner.id not in staff_partners:
                        partners_to_subscribe.append(partner.id)

            if partners_to_subscribe:
                event.with_context(mail_create_nosubscribe=False).message_subscribe(partner_ids=partners_to_subscribe)
                _logger.info(f"Partners {partners_to_subscribe} forzados como seguidores en Cita #{event.id}")

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
            'calendar_event_id': self.id,
        }

        line = self.env['sale.order.line'].create(line_vals)
        self.sale_order_id = sale_order.id

        _logger.info(
            f'✅ Vinculación dual establecida en flujo manual: '
            f'Cita #{self.id} ↔ SO #{sale_order.name} ↔ Línea #{line.id}'
        )

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
