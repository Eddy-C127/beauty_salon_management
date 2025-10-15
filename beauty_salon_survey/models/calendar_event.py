# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    # ============================================
    # CAMPOS DE ENCUESTA
    # ============================================
    
    survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta Asignada',
        help='Encuesta que se enviará al cliente al concluir el servicio'
    )
    
    survey_response_id = fields.Many2one(
        'survey.user_input',
        string='Respuesta de Encuesta',
        help='Respuesta del cliente a la encuesta',
        readonly=True,
        copy=False
    )
    
    survey_score = fields.Float(
        string='Calificación Numérica',
        digits=(3, 2),
        readonly=True,
        help='Score promedio obtenido en la encuesta (1-5)',
        copy=False
    )
    
    survey_score_display = fields.Char(
        string='Calificación',
        compute='_compute_survey_score_display',
        help='Muestra la calificación como estrellas'
    )
    
    survey_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('sent', 'Enviada'),
        ('completed', 'Completada'),
        ('positive', 'Positiva'),
        ('negative', 'Negativa'),
    ], string='Estado de Encuesta', 
       default='pending', 
       tracking=True,
       copy=False,
       help='Estado del proceso de encuesta')
    
    survey_sent_date = fields.Datetime(
        string='Fecha de Envío',
        readonly=True,
        copy=False,
        help='Cuándo se envió la encuesta al cliente'
    )
    
    survey_token = fields.Char(
        string='Token de Encuesta',
        readonly=True,
        copy=False,
        index=True,
        help='Token único para acceder a la encuesta sin autenticación'
    )
    
    survey_comments = fields.Text(
        string='Comentarios del Cliente',
        compute='_compute_survey_comments',
        store=True,
        help='Comentarios extraídos de la encuesta'
    )
    
    survey_url = fields.Char(
        string='URL de Encuesta',
        compute='_compute_survey_url',
        store=False,
        help='Link completo para enviar al cliente por WhatsApp'
    )
    
    # ============================================
    # CAMPOS DE GARANTÍA
    # ============================================
    
    is_warranty = fields.Boolean(
        string='Es Garantía',
        default=False,
        copy=False,
        help='Indica si esta cita es una garantía de un servicio previo'
    )
    
    original_appointment_id = fields.Many2one(
        'calendar.event',
        string='Cita Original',
        help='Si es garantía, referencia a la cita original',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )
    
    warranty_appointment_id = fields.Many2one(
        'calendar.event',
        string='Cita de Garantía Generada',
        help='Si generó una garantía, referencia a la nueva cita',
        readonly=True,
        copy=False,
        ondelete='set null'
    )
    
    warranty_status = fields.Selection([
        ('not_required', 'No Requerida'),
        ('pending_approval', 'Pendiente Aprobación'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('completed', 'Completada'),
    ], string='Estado de Garantía', 
       default='not_required', 
       tracking=True,
       copy=False,
       help='Estado del proceso de garantía')
    
    warranty_approved_by = fields.Many2one(
        'res.users',
        string='Aprobada Por',
        readonly=True,
        copy=False,
        help='Usuario que aprobó la garantía'
    )
    
    warranty_deadline = fields.Date(
        string='Fecha Límite para Garantía',
        copy=False,
        help='Fecha límite para agendar la garantía (7 días)'
    )
    
    warranty_notes = fields.Text(
        string='Notas de Garantía',
        help='Notas internas sobre la garantía (razones, detalles, etc.)'
    )
    
    # ============================================
    # EXTENDER ESTADO EXISTENTE
    # ============================================
    
    appointment_status = fields.Selection(
        selection_add=[
            ('warranty_completed', 'Warranty Completed'),
        ],
        ondelete={
            'warranty_completed': 'cascade',
        }
    )
    
    # ============================================
    # CAMPOS COMPUTADOS
    # ============================================
    
    @api.depends('survey_response_id', 'survey_response_id.user_input_line_ids')
    def _compute_survey_comments(self):
        """
        Extrae comentarios de texto libre de la respuesta de encuesta.
        """
        for record in self:
            if not record.survey_response_id:
                record.survey_comments = ''
                continue

            comment_lines = record.survey_response_id.user_input_line_ids.filtered(
                lambda l: l.question_id.question_type in ['text_box', 'char_box']
            )
            
            if not comment_lines:
                record.survey_comments = ''
                continue

            comments = []
            for line in comment_lines:
                comment = line.value_text_box or line.value_char_box or ''
                if comment.strip():
                    comments.append(comment.strip())
            
            record.survey_comments = '\n\n'.join(comments)
    
    @api.depends('survey_score')
    def _compute_survey_score_display(self):
        """
        Convierte el score numérico a representación con estrellas.
        Ejemplo: 2.3 → ⭐⭐⯨☆☆ (2.3/5.0) 😟
        """
        for record in self:
            if not record.survey_score:
                record.survey_score_display = ''
                continue
            
            score = record.survey_score
            
            # Calcular estrellas llenas y vacías
            full_stars = int(score)
            half_star = (score - full_stars) >= 0.5
            empty_stars = 5 - full_stars - (1 if half_star else 0)
            
            # Construir string de estrellas
            stars = '⭐' * full_stars
            if half_star:
                stars += '⯨'  # Media estrella
            stars += '☆' * empty_stars
            
            # Agregar emoji según clasificación
            config = self.env['pop.survey.config'].get_config()
            if config.is_negative_survey(score):
                emoji = '😟'  # Triste
            elif config.is_positive_survey(score):
                emoji = '😊'  # Feliz
            else:
                emoji = '😐'  # Neutral
            
            record.survey_score_display = f"{stars} ({score:.1f}/5.0) {emoji}"
    
    @api.depends('survey_id', 'survey_id.access_token', 'survey_token')
    def _compute_survey_url(self):
        """
        Construye la URL completa de la encuesta.
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        for record in self:
            if record.survey_id and record.survey_token:
                survey_access_token = record.survey_id.access_token
                answer_token = record.survey_token
                record.survey_url = f"{base_url}/survey/start/{survey_access_token}?answer_token={answer_token}"
            else:
                record.survey_url = False

    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def _get_survey_url(self):
        """Genera URL pública de la encuesta."""
        self.ensure_one()
        if not self.survey_response_id or not self.survey_response_id.access_token:
            return ''
        return self.survey_response_id.get_start_url()
    
    def _get_customer_name(self):
        """Obtiene el nombre del cliente."""
        self.ensure_one()
        customer = self.manual_customer_id or self.partner_id
        return customer.name if customer else 'Cliente'
    
    def _get_customer_phone(self):
        """Obtiene el teléfono del cliente."""
        self.ensure_one()
        customer = self.manual_customer_id or self.partner_id
        
        if not customer:
            return ''
        
        phone = customer.mobile or customer.phone or ''
        return ''.join(filter(str.isdigit, phone))

    # ============================================
    # MÉTODOS DE LÓGICA DE NEGOCIO
    # ============================================
    
    def write(self, vals):
        """
        Override write para detectar cambios de estado.
        """
        res = super(CalendarEvent, self).write(vals)
        
        if 'appointment_status' in vals:
            status = vals['appointment_status']
            if status == 'concluded':
                for record in self.filtered(lambda r: not r.is_warranty):
                    record._trigger_survey_flow()
            elif status == 'warranty_completed':
                for record in self.filtered('is_warranty'):
                    record._trigger_warranty_survey_flow()
            elif status == 'booked' and self.is_warranty and self.original_appointment_id:
                # Cuando se guarda una garantía que estaba en borrador
                self.original_appointment_id.warranty_status = 'completed'
        
        return res
    
    def _trigger_survey_flow(self):
        """
        Dispara el flujo de encuesta para una cita normal.
        """
        self.ensure_one()
        
        customer = self.manual_customer_id or self.partner_id
        if not customer:
            _logger.warning(f'Cita {self.id} no tiene cliente, no se puede enviar encuesta.')
            return
        
        if not self.survey_id:
            config = self.env['pop.survey.config'].get_config()
            self.survey_id = config.default_service_survey_id
            if not self.survey_id:
                _logger.warning('No hay encuesta de servicio por defecto configurada.')
                return
        
        # Verificar si ya existe una respuesta (prevenir duplicados)
        existing_input = self.env['survey.user_input'].search([
            ('calendar_event_id', '=', self.id),
        ], limit=1)
        
        if existing_input:
            _logger.warning(f'Ya existe una encuesta para la cita {self.id}. No se crea otra.')
            return
        
        user_input_vals = {
            'survey_id': self.survey_id.id,
            'partner_id': customer.id,
            'email': customer.email or '',
            'state': 'new',
            'test_entry': False,
            'calendar_event_id': self.id,
        }
        
        user_input = self.env['survey.user_input'].create(user_input_vals)
        
        self.write({
            'survey_response_id': user_input.id,
            'survey_token': user_input.access_token,
            'survey_status': 'sent',
            'survey_sent_date': fields.Datetime.now(),
        })
        
        survey_url = user_input.get_start_url()
        _logger.info(f'Encuesta enviada para cita {self.id} - Cliente: {customer.name} - URL: {survey_url}')

    def _trigger_warranty_survey_flow(self):
        """
        Dispara el flujo de encuesta para una garantía.
        """
        self.ensure_one()
        
        customer = self.manual_customer_id or self.partner_id
        if not customer:
            _logger.warning(f'Garantía {self.id} no tiene cliente, no se puede enviar encuesta.')
            return
        
        if not self.survey_id:
            config = self.env['pop.survey.config'].get_config()
            self.survey_id = config.default_warranty_survey_id
            if not self.survey_id:
                _logger.warning('No hay encuesta de garantía por defecto configurada.')
                return
        
        # Verificar duplicados
        existing_input = self.env['survey.user_input'].search([
            ('calendar_event_id', '=', self.id),
        ], limit=1)
        
        if existing_input:
            _logger.warning(f'Ya existe una encuesta para la garantía {self.id}.')
            return

        user_input_vals = {
            'survey_id': self.survey_id.id,
            'partner_id': customer.id,
            'email': customer.email or '',
            'state': 'new',
            'test_entry': False,
            'calendar_event_id': self.id,
        }
        
        user_input = self.env['survey.user_input'].create(user_input_vals)
        
        self.write({
            'survey_response_id': user_input.id,
            'survey_token': user_input.access_token,
            'survey_status': 'sent',
            'survey_sent_date': fields.Datetime.now(),
        })
        
        survey_url = user_input.get_start_url()
        _logger.info(f'Encuesta de garantía enviada para cita {self.id} - URL: {survey_url}')
    
    def _process_survey_response(self):
        """
        Procesa la respuesta de encuesta y la clasifica.
        """
        self.ensure_one()
        
        if not self.survey_response_id:
            return
        
        score = self._calculate_survey_score()
        
        if score is None:
            _logger.warning(f'No se pudo calcular la calificación para la cita {self.id}.')
            return
        
        config = self.env['pop.survey.config'].get_config()
        
        if config.is_negative_survey(score):
            new_status = 'negative'
        elif config.is_positive_survey(score):
            new_status = 'positive'
        else:
            new_status = 'completed'
        
        _logger.info(f'Encuesta procesada para cita {self.id}: Calificación={score}, Estado={new_status}')

        self.write({
            'survey_score': score,
            'survey_status': new_status,
        })
        
        if new_status == 'negative':
            self._handle_negative_survey()

    def _handle_negative_survey(self):
        """
        Lógica cuando una encuesta sale negativa.
        """
        self.ensure_one()
        
        if self.is_warranty:
            self._handle_negative_warranty_survey()
            return
        
        config = self.env['pop.survey.config'].get_config()
        
        self.warranty_status = 'pending_approval'
        
        _logger.info(f'Encuesta NEGATIVA para cita {self.id}. Creando actividad de aprobación.')
        
        if config.warranty_approval_user_id:
            self._create_warranty_approval_activity()
        else:
            _logger.info(f'No hay usuario configurado para aprobación de garantías.')
    
    def _calculate_survey_score(self):
        """
        Calcula la calificación promedio de la encuesta.
        """
        self.ensure_one()
        
        if not self.survey_response_id:
            return None
        
        # Prioridad 1: Respuestas numéricas directas
        numeric_lines = self.survey_response_id.user_input_line_ids.filtered(
            lambda l: l.answer_type == 'numerical_box' and l.value_numerical_box > 0
        )
        if numeric_lines:
            scores = numeric_lines.mapped('value_numerical_box')
            return sum(scores) / len(scores) if scores else None

        # Prioridad 2: Respuestas de tipo "sugerencia"
        suggestion_lines = self.survey_response_id.user_input_line_ids.filtered(
            lambda l: l.answer_type == 'suggestion' and l.suggested_answer_id
        )
        if suggestion_lines:
            scores = []
            for line in suggestion_lines:
                try:
                    score_value = float(line.suggested_answer_id.value.split()[0])
                    scores.append(score_value)
                except (ValueError, IndexError):
                    _logger.debug(f"No se pudo convertir '{line.suggested_answer_id.value}' a un score.")
                    continue
            
            return sum(scores) / len(scores) if scores else None
        
        _logger.warning(f"No se encontraron respuestas calificables para la encuesta de la cita {self.id}")
        return None

    # ============================================
    # MÉTODOS DE GARANTÍAS (ITERACIÓN 4)
    # ============================================
    
    def _create_warranty_approval_activity(self):
        """
        Crea una actividad de tipo 'Aprobar Garantía' para el gerente.
        """
        self.ensure_one()
        
        config = self.env['pop.survey.config'].get_config()
        
        if not config.warranty_approval_user_id:
            _logger.warning('No hay usuario configurado para aprobación de garantías.')
            return
        
        activity_type = self.env.ref(
            'beauty_salon_survey.mail_activity_type_warranty_approval',
            raise_if_not_found=False
        )
        
        if not activity_type:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        
        customer_name = self._get_customer_name()
        service_name = self.appointment_type_id.name if self.appointment_type_id else 'Servicio'
        
        summary = f'Aprobar Garantía: {customer_name} - {service_name}'
        note = f'''
        <p><strong>Encuesta Negativa Recibida</strong></p>
        <ul>
            <li><strong>Cliente:</strong> {customer_name}</li>
            <li><strong>Servicio:</strong> {service_name}</li>
            <li><strong>Calificación:</strong> {self.survey_score:.1f}/5.0</li>
            <li><strong>Fecha del servicio:</strong> {self.start.strftime('%d/%m/%Y') if self.start else 'N/A'}</li>
        </ul>
        <p><strong>Comentarios del cliente:</strong></p>
        <p>{self.survey_comments or 'Sin comentarios'}</p>
        <hr/>
        <p>Por favor, revisa la encuesta y decide si se aprueba la garantía.</p>
        '''
        
        activity = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id if activity_type else False,
            'summary': summary,
            'note': note,
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get_id('calendar.event'),
            'user_id': config.warranty_approval_user_id.id,
            'date_deadline': fields.Date.today(),
        })
        
        # Enviar mensaje al chatter INMEDIATAMENTE
        self.message_post(
            body=note,
            subject=summary,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        _logger.info(
            f'Actividad de aprobación creada (ID: {activity.id}) para usuario {config.warranty_approval_user_id.name}'
        )
    
    def action_approve_warranty(self):
        """Aprueba la garantía."""
        for record in self:
            if record.warranty_status != 'pending_approval':
                continue
            
            config = self.env['pop.survey.config'].get_config()
            deadline = fields.Date.today() + relativedelta(days=config.warranty_deadline_days)
            
            record.write({
                'warranty_status': 'approved',
                'warranty_approved_by': self.env.user.id,
                'warranty_deadline': deadline,
            })
            
            record._complete_warranty_activities('Garantía aprobada')
            
            _logger.info(
                f'Garantía aprobada para cita {record.id} por {self.env.user.name}. '
                f'Deadline: {deadline.strftime("%d/%m/%Y")}'
            )
        
        return True
    
    def action_reject_warranty(self):
        """Rechaza la garantía."""
        for record in self:
            if record.warranty_status != 'pending_approval':
                continue
            
            record.warranty_status = 'rejected'
            record._complete_warranty_activities('Garantía rechazada')
            
            _logger.info(f'Garantía rechazada para cita {record.id} por {self.env.user.name}')
        
        return True
    
    def _complete_warranty_activities(self, feedback_message):
        """Completa actividades pendientes."""
        self.ensure_one()
        
        activities = self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', 'calendar.event'),
            ('user_id', '=', self.env.user.id),
        ])
        
        for activity in activities:
            activity.action_feedback(feedback=feedback_message)
        
        _logger.info(f'Completadas {len(activities)} actividades para cita {self.id}')
    
    def action_create_warranty_appointment(self):
        """
        Crea una nueva cita marcada como garantía EN MODO BORRADOR.
        """
        self.ensure_one()
        
        if self.warranty_status != 'approved':
            raise UserError(_('Solo se pueden crear citas de garantía para garantías aprobadas.'))
        
        if self.warranty_appointment_id:
            raise UserError(_('Esta cita ya tiene una garantía creada.'))
        
        config = self.env['pop.survey.config'].get_config()
        
        warranty_vals = {
            'name': f'Garantía - {self.appointment_type_id.name if self.appointment_type_id else "Servicio"}',
            'manual_customer_id': self.manual_customer_id.id if self.manual_customer_id else False,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'appointment_type_id': self.appointment_type_id.id if self.appointment_type_id else False,
            'real_employee_id': self.real_employee_id.id if self.real_employee_id else False,
            'is_warranty': True,
            'original_appointment_id': self.id,
            'survey_id': config.default_warranty_survey_id.id if config.default_warranty_survey_id else False,
            'warranty_status': 'not_required',
        }
        
        new_appointment = self.env['calendar.event'].create(warranty_vals)
        
        self.warranty_appointment_id = new_appointment.id
        
        _logger.info(
            f'Cita de garantía creada (ID: {new_appointment.id}) en modo borrador para cita original {self.id}'
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cita de Garantía - Completar Detalles',
            'res_model': 'calendar.event',
            'res_id': new_appointment.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'form_view_initial_mode': 'edit',
            }
        }
    
    def _handle_negative_warranty_survey(self):
        """
        Escala cuando una GARANTÍA también sale negativa.
        """
        self.ensure_one()
        
        config = self.env['pop.survey.config'].get_config()
        
        if not config.supervisor_user_id:
            _logger.warning('No hay supervisor configurado para escalaciones.')
            return
        
        original = self.original_appointment_id
        
        customer_name = self._get_customer_name()
        service_name = self.appointment_type_id.name if self.appointment_type_id else 'Servicio'
        
        summary = f'🚨 ESCALACIÓN: Garantía Negativa - {customer_name}'
        
        note = f'''
        <p><strong style="color: red;">⚠️ GARANTÍA CON ENCUESTA NEGATIVA</strong></p>
        <p>El cliente tuvo un servicio inicial negativo y la garantía TAMBIÉN fue negativa.</p>
        <hr/>
        <p><strong>Información del cliente:</strong></p>
        <ul>
            <li><strong>Cliente:</strong> {customer_name}</li>
            <li><strong>Servicio:</strong> {service_name}</li>
            <li><strong>Calificación garantía:</strong> {self.survey_score:.1f}/5.0</li>
            <li><strong>Calificación original:</strong> {original.survey_score:.1f}/5.0 (Cita #{original.id})</li>
        </ul>
        <p><strong>Comentarios de la garantía:</strong></p>
        <p>{self.survey_comments or 'Sin comentarios'}</p>
        <hr/>
        <p><strong>Acción requerida:</strong> Contacto directo con el cliente para resolver la situación.</p>
        '''
        
        activity_type = self.env.ref(
            'beauty_salon_survey.mail_activity_type_warranty_escalation',
            raise_if_not_found=False
        )
        
        if not activity_type:
            activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False)
        
        self.env['mail.activity'].create({
            'activity_type_id': activity_type.id if activity_type else False,
            'summary': summary,
            'note': note,
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get_id('calendar.event'),
            'user_id': config.supervisor_user_id.id,
            'date_deadline': fields.Date.today(),
        })
        
        _logger.warning(
            f'🚨 ESCALACIÓN: Garantía {self.id} también negativa. '
            f'Actividad creada para supervisor {config.supervisor_user_id.name}'
        )
    
    @api.model
    def _check_warranty_deadlines(self):
        """
        Cron job que revisa garantías aprobadas con deadline vencido.
        """
        today = fields.Date.today()
        
        expired_warranties = self.search([
            ('warranty_status', '=', 'approved'),
            ('warranty_deadline', '<', today),
            ('warranty_appointment_id', '=', False),
        ])
        
        if not expired_warranties:
            _logger.info('No hay garantías vencidas.')
            return
        
        _logger.warning(f'Se encontraron {len(expired_warranties)} garantías vencidas.')
        
        config = self.env['pop.survey.config'].get_config()
        
        for appointment in expired_warranties:
            if config.warranty_approval_user_id:
                customer_name = appointment._get_customer_name()
                
                note = f'''
                <p><strong>⏰ Garantía Vencida</strong></p>
                <p>El plazo para agendar la garantía ha expirado.</p>
                <ul>
                    <li><strong>Cliente:</strong> {customer_name}</li>
                    <li><strong>Cita original:</strong> #{appointment.id}</li>
                    <li><strong>Fecha límite:</strong> {appointment.warranty_deadline.strftime('%d/%m/%Y')}</li>
                    <li><strong>Calificación:</strong> {appointment.survey_score:.1f}/5.0</li>
                </ul>
                <p>Por favor, contacta al cliente para reagendar o cerrar el caso.</p>
                '''
                
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                    'summary': f'⏰ Garantía Vencida: {customer_name}',
                    'note': note,
                    'res_id': appointment.id,
                    'res_model_id': self.env['ir.model']._get_id('calendar.event'),
                    'user_id': config.warranty_approval_user_id.id,
                    'date_deadline': today,
                })
        
        _logger.info(f'Notificaciones enviadas para {len(expired_warranties)} garantías vencidas.')            