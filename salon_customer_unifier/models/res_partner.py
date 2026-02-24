# -*- coding: utf-8 -*-
import re
import logging

from odoo import models, api
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _normalize_phone_e164(self, phone_number):
        """
        Normaliza un número de teléfono al formato E.164.
        Elimina espacios, guiones, paréntesis y otros caracteres no numéricos.
        Mantiene el signo + al inicio.

        Reglas para México (caso de uso principal):
        - 10 dígitos sin código → +52XXXXXXXXXX
        - 12 dígitos empezando con 52 → +52XXXXXXXXXX

        :param phone_number: str — Número en cualquier formato
        :return: str — Número normalizado tipo +528711234567, o '' si no se puede
        """
        if not phone_number:
            return ''
        # Conservar solo dígitos y el signo +
        cleaned = re.sub(r'[^\d+]', '', str(phone_number).strip())
        if not cleaned:
            return ''
        # Si ya tiene +, respetar el formato
        if cleaned.startswith('+'):
            return cleaned
        # 10 dígitos → número mexicano local
        if len(cleaned) == 10:
            return '+52' + cleaned
        # 12 dígitos comenzando con 52 → agregar +
        if len(cleaned) == 12 and cleaned.startswith('52'):
            return '+' + cleaned
        # 13 dígitos comenzando con 521 → normalizar (algunos sistemas agregan 1)
        if len(cleaned) == 13 and cleaned.startswith('521'):
            return '+52' + cleaned[3:]
        # Otro formato: agregar + y retornar tal cual
        return '+' + cleaned

    @api.model
    def find_or_create_by_phone(self, phone, name, email):
        """
        Busca un partner existente por teléfono (mobile o phone) o crea uno nuevo.
        El teléfono es el identificador primario (Phone-First Match).

        Estrategia:
        1. Match exacto en campo `mobile` o `phone` con número normalizado E.164
        2. Match parcial por últimos 10 dígitos (tolerancia de formato)
        3. Creación si no se encuentra ningún match

        :param phone: str — Número de teléfono del cliente
        :param name: str — Nombre del cliente
        :param email: str — Email del cliente
        :return: res.partner recordset — Partner encontrado o creado
                 Recordset vacío si el teléfono no se puede normalizar
        """
        clean_phone = self._normalize_phone_e164(phone)

        if not clean_phone:
            _logger.warning(
                'salon_customer_unifier: No se pudo normalizar el teléfono: %r — '
                'se usará el flujo nativo de Odoo.',
                phone,
            )
            return self.env['res.partner']

        # ── 1. Búsqueda por match exacto en mobile o phone ──────────────────
        partner = self.sudo().search([
            '|',
            ('mobile', '=', clean_phone),
            ('phone', '=', clean_phone),
            ('active', 'in', [True, False]),  # incluir archivados por seguridad
        ], limit=1)

        if partner:
            _logger.info(
                'salon_customer_unifier: [MATCH EXACTO] Teléfono %s → Partner "%s" (ID %s)',
                clean_phone, partner.name, partner.id,
            )
            self._update_partner_if_incomplete(partner, name, email)
            return partner

        # ── 2. Búsqueda por últimos 10 dígitos ──────────────────────────────
        phone_digits = re.sub(r'\D', '', clean_phone)
        if len(phone_digits) >= 10:
            last_10 = phone_digits[-10:]
            partner = self.sudo().search([
                '|',
                ('mobile', 'like', last_10),
                ('phone', 'like', last_10),
                ('active', 'in', [True, False]),
            ], limit=1)
            if partner:
                _logger.info(
                    'salon_customer_unifier: [MATCH PARCIAL] Últimos 10 dígitos %s → Partner "%s" (ID %s)',
                    last_10, partner.name, partner.id,
                )
                partner.sudo().write({'mobile': clean_phone})
                self._update_partner_if_incomplete(partner, name, email)
                return partner

        # ── 3. Creación de nuevo partner ─────────────────────────────────────
        _logger.info(
            'salon_customer_unifier: [NUEVO] Creando partner con teléfono %s, nombre: %s',
            clean_phone, name,
        )
        return self.sudo().create({
            'name': name or phone,
            'email': email or False,
            'mobile': clean_phone,
            'phone': clean_phone,
            'customer_rank': 1,
            'lang': self.env.lang or 'es_MX',
        })

    @api.model
    def search_by_phone(self, phone):
        """
        Busca un partner por teléfono SIN crear uno nuevo.
        Usado por el autocomplete del formulario de citas (frontend).

        Mismo algoritmo de búsqueda que find_or_create_by_phone,
        pero se detiene antes de la creación.

        :param phone: str — Número en cualquier formato
        :return: res.partner recordset (vacío si no se encuentra)
        """
        clean_phone = self._normalize_phone_e164(phone)
        if not clean_phone:
            return self.env['res.partner']

        # 1. Match exacto en mobile o phone
        partner = self.sudo().search([
            '|',
            ('mobile', '=', clean_phone),
            ('phone', '=', clean_phone),
            ('active', 'in', [True, False]),
        ], limit=1)
        if partner:
            return partner

        # 2. Match parcial por últimos 10 dígitos
        phone_digits = re.sub(r'\D', '', clean_phone)
        if len(phone_digits) >= 10:
            last_10 = phone_digits[-10:]
            partner = self.sudo().search([
                '|',
                ('mobile', 'like', last_10),
                ('phone', 'like', last_10),
                ('active', 'in', [True, False]),
            ], limit=1)
            if partner:
                return partner

        return self.env['res.partner']

    @api.model
    def _search_display_name(self, operator, value):
        """
        Extiende la búsqueda predictiva de partners para incluir phone y mobile.
        Afecta todos los campos Many2one a res.partner (sale_order.partner_id,
        calendar.event.manual_customer_id, etc.).

        En Odoo 18 el autocomplete de Many2one llama a name_search →
        search_fetch([('display_name', op, value)]) → _search_display_name.
        """
        domain = super()._search_display_name(operator, value)
        if value:
            phone_domains = [
                [('phone', operator, value)],
                [('mobile', operator, value)],
            ]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = expression.AND([domain] + phone_domains)
            else:
                domain = expression.OR([domain] + phone_domains)
        return domain

    @api.model
    def _update_partner_if_incomplete(self, partner, name, email):
        """
        Actualiza campos vacíos del partner existente sin sobreescribir datos.
        Solo rellena email y nombre si el partner no los tenía.

        :param partner: res.partner recordset
        :param name: str — nombre propuesto
        :param email: str — email propuesto
        """
        vals = {}
        if not partner.email and email:
            vals['email'] = email
        if not partner.name and name:
            vals['name'] = name
        if vals:
            partner.sudo().write(vals)
            _logger.info(
                'salon_customer_unifier: Partner ID %s actualizado con datos faltantes: %s',
                partner.id, list(vals.keys()),
            )
