/** @odoo-module **/
/**
 * salon_customer_unifier — Phone Widget v3
 *
 * Funcionalidades:
 * 1. intl-tel-input: selector de bandera + validación + formato E.164
 * 2. Lookup al salir del campo teléfono: busca el partner sin crear uno nuevo
 * 3. Autocomplete de Nombre y Email al encontrar un partner
 * 4. Campos bloqueados (readonly) cuando se encuentra partner
 * 5. Mensaje inteligente: found / found_no_email / new
 * 6. "¿No eres tú?" → formulario de solicitud de corrección de datos
 *    El admin recibe una actividad en el CRM con los datos indicados por el cliente
 */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SalonPhoneIntlInput = publicWidget.Widget.extend({
    selector: '.appointment_submit_form',
    events: {},

    start: function () {
        this._super.apply(this, arguments);
        this._lastLookedPhone = null;
        this._initIntlTelInput();
        this._bindCorrectionForm();
        return Promise.resolve();
    },

    // ── INICIALIZACIÓN ──────────────────────────────────────────────────────

    _initIntlTelInput: function () {
        const phoneInput = this.el.querySelector('#phone_field');
        if (!phoneInput) return;

        if (typeof window.intlTelInput === 'undefined') {
            console.warn('[salon_customer_unifier] intl-tel-input no disponible.');
            this._bindNativeFallback(phoneInput);
            return;
        }

        this.iti = window.intlTelInput(phoneInput, {
            initialCountry: 'mx',
            preferredCountries: ['mx', 'us', 'co', 'ar'],
            separateDialCode: true,
            utilsScript: '/salon_customer_unifier/static/src/lib/intl-tel-input/js/utils.js',
            nationalMode: false,
            formatOnDisplay: true,
            autoPlaceholder: 'aggressive',
        });

        const confirmBtn = this.el.querySelector('.o_appointment_form_confirm_btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', this._onConfirmClick.bind(this));
        }

        phoneInput.addEventListener('input', this._onPhoneInput.bind(this));
        phoneInput.addEventListener('countrychange', this._onCountryChange.bind(this));
        phoneInput.addEventListener('blur', this._onPhoneBlur.bind(this));
    },

    /**
     * Enlaza los botones del formulario de corrección.
     * "¿No eres tú?" se crea dinámicamente en _showPartnerMessage.
     * "Cancelar" y "Enviar solicitud" están en el DOM desde el inicio.
     */
    _bindCorrectionForm: function () {
        const cancelBtn = this.el.querySelector('#o_salon_cancel_correction');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', this._onCancelCorrection.bind(this));
        }
        const sendBtn = this.el.querySelector('#o_salon_send_correction');
        if (sendBtn) {
            sendBtn.addEventListener('click', this._onSendCorrection.bind(this));
        }
    },

    /** Extrae el appointment_type_id de la acción del formulario. */
    _getAppointmentTypeId: function () {
        const action = this.el.getAttribute('action') || '';
        const match = action.match(/\/appointment\/(\d+)\/submit/);
        return match ? parseInt(match[1]) : null;
    },

    // ── EVENTOS DEL CAMPO TELÉFONO ───────────────────────────────────────────

    /**
     * Retorna la cantidad de dígitos del número nacional (sin código de país).
     * Con separateDialCode: true, phoneInput.value ya es el número nacional.
     */
    _getNationalDigits: function () {
        const phoneInput = this.el.querySelector('#phone_field');
        if (!phoneInput) return 0;
        return (phoneInput.value || '').replace(/\D/g, '').length;
    },

    _setPhoneError: function (show) {
        const phoneInput = this.el.querySelector('#phone_field');
        const errorEl = this.el.querySelector('#phone_error');
        if (show) {
            if (errorEl) errorEl.classList.remove('d-none');
            if (phoneInput) phoneInput.classList.add('is-invalid');
        } else {
            if (errorEl) errorEl.classList.add('d-none');
            if (phoneInput) phoneInput.classList.remove('is-invalid');
        }
    },

    /**
     * Click en "Confirmar Cita":
     * 1. Valida que el número nacional tenga exactamente 10 dígitos
     * 2. Copia los datos de corrección (si los hay) a los hidden fields
     * 3. Escribe E.164 en el campo visible y en el campo oculto
     */
    _onConfirmClick: function (ev) {
        if (!this.iti) return;

        const phoneInput = this.el.querySelector('#phone_field');

        if (this._getNationalDigits() !== 10) {
            ev.preventDefault();
            ev.stopPropagation();
            this._setPhoneError(true);
            phoneInput && phoneInput.focus();
            return false;
        }

        this._setPhoneError(false);

        // Copiar datos del formulario de corrección a los hidden fields
        this._syncCorrectionHiddenFields();

        const e164Number = this.iti.getNumber();
        if (phoneInput) phoneInput.value = e164Number;
        const hiddenField = this.el.querySelector('#phone_full');
        if (hiddenField) hiddenField.value = e164Number;
    },

    /**
     * Edición del campo teléfono:
     * - > 10 dígitos → error inmediato
     * - ≤ 10 dígitos → limpiar error
     * - 0 dígitos (campo vacío) → limpiar también nombre y email
     * - Ocultar mensaje y desbloquear campos (número cambió)
     */
    _onPhoneInput: function () {
        const digits = this._getNationalDigits();
        this._setPhoneError(digits > 10);
        this._resetPartnerState();
        if (digits === 0) {
            const nameInput = this.el.querySelector('#name_field');
            const emailInput = this.el.querySelector('#email_field');
            if (nameInput) nameInput.value = '';
            if (emailInput) emailInput.value = '';
        }
    },

    _onCountryChange: function () {
        if (this._getNationalDigits() === 10) {
            this._setPhoneError(false);
            this._triggerLookup();
        } else {
            this._resetPartnerState();
        }
    },

    _onPhoneBlur: function () {
        if (!this.iti) return;
        const digits = this._getNationalDigits();
        if (digits === 0) return;
        if (digits === 10) {
            this._setPhoneError(false);
            this._triggerLookup();
        } else {
            this._setPhoneError(true);
        }
    },

    // ── LOOKUP ──────────────────────────────────────────────────────────────

    _triggerLookup: function () {
        if (!this.iti) return;
        const phone = this.iti.getNumber();
        if (!phone || phone.length < 8) return;
        if (this._lastLookedPhone === phone) return;
        this._lastLookedPhone = phone;
        this._doPartnerLookup(phone);
    },

    _doPartnerLookup: async function (phone) {
        try {
            const response = await fetch('/appointment/partner_lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    id: Date.now(),
                    params: { phone: phone },
                }),
            });

            const json = await response.json();
            const result = json.result;

            if (!result || result.error) {
                this._resetPartnerState();
                return;
            }

            // Guardar el ID del partner encontrado en el hidden field
            const foundPartnerField = this.el.querySelector('#found_partner_id');
            if (foundPartnerField) {
                foundPartnerField.value = result.found ? (result.partner_id || '') : '';
            }

            if (result.found) {
                const state = result.has_email ? 'found' : 'found_no_email';
                this._autocompleteFields(result.name, result.email, state);
                this._showPartnerMessage(state, result.name);
            } else {
                this._showPartnerMessage('new');
            }

        } catch (err) {
            console.warn('[salon_customer_unifier] Error en lookup:', err);
            this._resetPartnerState();
        }
    },

    // ── AUTOCOMPLETE Y BLOQUEO DE CAMPOS ────────────────────────────────────

    _autocompleteFields: function (name, email, state) {
        const nameInput = this.el.querySelector('#name_field');
        const emailInput = this.el.querySelector('#email_field');
        if (nameInput) nameInput.value = name || '';
        if (emailInput) emailInput.value = email || '';

        if (state === 'found') {
            this._lockField(nameInput);
            this._lockField(emailInput);
        } else if (state === 'found_no_email') {
            this._lockField(nameInput);
            // email se deja editable para que el usuario lo ingrese
        }
    },

    _lockField: function (input) {
        if (!input) return;
        input.setAttribute('readonly', 'readonly');
        input.classList.add('o_salon_field_locked');
    },

    _unlockFields: function () {
        [
            this.el.querySelector('#name_field'),
            this.el.querySelector('#email_field'),
        ].forEach(function (input) {
            if (!input) return;
            input.removeAttribute('readonly');
            input.classList.remove('o_salon_field_locked');
        });
    },

    // ── MENSAJE INTELIGENTE ──────────────────────────────────────────────────

    /**
     * Estados:
     * - 'found'          → verde, campos nombre+email bloqueados, link "¿No eres tú?"
     * - 'found_no_email' → amarillo, nombre bloqueado, email editable, link "¿No eres tú?"
     * - 'new'            → azul, campos libres, sin link
     */
    _showPartnerMessage: function (state, name) {
        const msgEl = this.el.querySelector('#o_salon_partner_message');
        const alertEl = this.el.querySelector('#o_salon_partner_alert');
        const iconEl = this.el.querySelector('#o_salon_partner_icon');
        const textEl = this.el.querySelector('#o_salon_partner_text');
        if (!msgEl || !alertEl || !iconEl || !textEl) return;

        // Limpiar estado anterior
        alertEl.className = 'alert py-2 px-3 mb-0';
        iconEl.className = 'fa me-2';
        const prevLink = alertEl.querySelector('.o_salon_not_you');
        if (prevLink) prevLink.remove();

        const firstName = name ? name.split(' ')[0] : '';

        const configs = {
            found: {
                alertClass: 'alert-success',
                iconClass: 'fa-check-circle',
                text: firstName
                    ? `¡Hola ${firstName}! Encontramos tu perfil. Confirma que estos son tus datos.`
                    : '¡Encontramos tu perfil! Confirma que estos son tus datos.',
                notYouLink: true,
            },
            found_no_email: {
                alertClass: 'alert-warning',
                iconClass: 'fa-exclamation-triangle',
                text: firstName
                    ? `Hola ${firstName}, encontramos tu perfil. Por favor ingresa tu correo electrónico.`
                    : 'Encontramos tu perfil. Por favor ingresa tu correo electrónico.',
                notYouLink: true,
            },
            new: {
                alertClass: 'alert-info',
                iconClass: 'fa-user-plus',
                text: '¡Primera visita! Completa tus datos para registrarte como cliente.',
                notYouLink: false,
            },
        };

        const cfg = configs[state] || configs.new;
        alertEl.classList.add(cfg.alertClass);
        iconEl.classList.add(cfg.iconClass);
        textEl.textContent = cfg.text;

        if (cfg.notYouLink) {
            const link = document.createElement('a');
            link.href = '#';
            link.className = 'alert-link ms-2 o_salon_not_you small';
            link.textContent = '¿No eres tú?';
            link.addEventListener('click', this._onNotYouClick.bind(this));
            alertEl.appendChild(link);
        }

        msgEl.classList.remove('d-none');
    },

    // ── FLUJO "¿NO ERES TÚ?" ────────────────────────────────────────────────

    /**
     * Click en "¿No eres tú?":
     * - Muestra el formulario de corrección debajo del mensaje
     * - Los campos principales (nombre/email) quedan bloqueados
     * - El admin recibirá una actividad con los datos que el cliente indique
     */
    _onNotYouClick: function (ev) {
        ev.preventDefault();

        // Cambiar el mensaje a estado informativo
        const alertEl = this.el.querySelector('#o_salon_partner_alert');
        const textEl = this.el.querySelector('#o_salon_partner_text');
        const link = alertEl ? alertEl.querySelector('.o_salon_not_you') : null;

        if (alertEl) {
            alertEl.className = 'alert alert-warning py-2 px-3 mb-0';
        }
        const iconEl = this.el.querySelector('#o_salon_partner_icon');
        if (iconEl) {
            iconEl.className = 'fa fa-pencil me-2';
        }
        if (textEl) {
            textEl.textContent = 'Deja tus datos correctos abajo. Un administrador los actualizará en breve.';
        }
        if (link) link.remove();

        // Mostrar formulario de corrección
        const correctionForm = this.el.querySelector('#o_salon_correction_form');
        if (correctionForm) {
            correctionForm.classList.remove('d-none');
            const firstInput = correctionForm.querySelector('input[type="text"]');
            if (firstInput) firstInput.focus();
        }
    },

    /**
     * Click en "Cancelar": oculta el formulario de corrección y restaura el mensaje.
     */
    _onCancelCorrection: function () {
        const correctionForm = this.el.querySelector('#o_salon_correction_form');
        if (correctionForm) correctionForm.classList.add('d-none');

        const nameField = this.el.querySelector('#correction_name_field');
        const emailField = this.el.querySelector('#correction_email_field');
        if (nameField) nameField.value = '';
        if (emailField) emailField.value = '';

        // Restablecer estado "enviado" por si el usuario vuelve a abrir el form
        const sentMsg = this.el.querySelector('#o_salon_correction_sent');
        if (sentMsg) sentMsg.classList.add('d-none');
        const sendBtn = this.el.querySelector('#o_salon_send_correction');
        if (sendBtn) { sendBtn.disabled = false; sendBtn.classList.remove('d-none'); }

        this._lastLookedPhone = null;
        this._triggerLookup();
    },

    /**
     * Click en "Enviar solicitud":
     * Llama a /appointment/send_correction vía AJAX.
     * Si tiene éxito muestra la confirmación y limpia los hidden fields
     * para que el submit principal no duplique la actividad.
     */
    _onSendCorrection: async function () {
        const visibleName = this.el.querySelector('#correction_name_field');
        const visibleEmail = this.el.querySelector('#correction_email_field');
        const correctionName = (visibleName ? visibleName.value : '').trim();
        const correctionEmail = (visibleEmail ? visibleEmail.value : '').trim();

        if (!correctionName && !correctionEmail) {
            // Al menos un campo requerido
            if (visibleName) visibleName.focus();
            return;
        }

        const foundPartnerId = (this.el.querySelector('#found_partner_id') || {}).value || '';
        const phone = this.iti ? this.iti.getNumber() : '';
        const appointmentTypeId = this._getAppointmentTypeId();

        const sendBtn = this.el.querySelector('#o_salon_send_correction');
        if (sendBtn) sendBtn.disabled = true;

        try {
            const response = await fetch('/appointment/send_correction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    id: Date.now(),
                    params: {
                        found_partner_id: parseInt(foundPartnerId) || 0,
                        correction_name: correctionName,
                        correction_email: correctionEmail,
                        phone: phone,
                        appointment_type_id: appointmentTypeId,
                    },
                }),
            });

            const json = await response.json();
            const result = json.result;

            if (result && result.success) {
                // Mostrar confirmación dentro del formulario
                const sentMsg = this.el.querySelector('#o_salon_correction_sent');
                if (sentMsg) sentMsg.classList.remove('d-none');
                if (sendBtn) sendBtn.classList.add('d-none');

                // Limpiar hidden fields para no duplicar al submit del form principal
                const hiddenName = this.el.querySelector('#correction_name');
                const hiddenEmail = this.el.querySelector('#correction_email');
                const hiddenPartner = this.el.querySelector('#found_partner_id');
                if (hiddenName) hiddenName.value = '';
                if (hiddenEmail) hiddenEmail.value = '';
                if (hiddenPartner) hiddenPartner.value = '';
            } else {
                if (sendBtn) sendBtn.disabled = false;
                console.warn('[salon_customer_unifier] Error al enviar corrección:', result);
            }
        } catch (err) {
            if (sendBtn) sendBtn.disabled = false;
            console.warn('[salon_customer_unifier] Error de red al enviar corrección:', err);
        }
    },

    /**
     * Copia los datos ingresados en el formulario de corrección visible
     * a los hidden fields que se envían con el form principal.
     * Se llama justo antes del submit.
     */
    _syncCorrectionHiddenFields: function () {
        const correctionForm = this.el.querySelector('#o_salon_correction_form');
        const isVisible = correctionForm && !correctionForm.classList.contains('d-none');

        const hiddenName = this.el.querySelector('#correction_name');
        const hiddenEmail = this.el.querySelector('#correction_email');

        if (isVisible) {
            const visibleName = this.el.querySelector('#correction_name_field');
            const visibleEmail = this.el.querySelector('#correction_email_field');
            if (hiddenName) hiddenName.value = (visibleName ? visibleName.value : '').trim();
            if (hiddenEmail) hiddenEmail.value = (visibleEmail ? visibleEmail.value : '').trim();
        } else {
            if (hiddenName) hiddenName.value = '';
            if (hiddenEmail) hiddenEmail.value = '';
        }
    },

    // ── RESET ────────────────────────────────────────────────────────────────

    /**
     * Restablece el estado completo del componente:
     * oculta mensaje, oculta corrección, desbloquea campos, limpia partner ID.
     * Se llama cuando el usuario edita el teléfono (número cambió).
     */
    _resetPartnerState: function () {
        const msgEl = this.el.querySelector('#o_salon_partner_message');
        if (msgEl) msgEl.classList.add('d-none');

        const correctionForm = this.el.querySelector('#o_salon_correction_form');
        if (correctionForm) correctionForm.classList.add('d-none');

        const foundPartnerField = this.el.querySelector('#found_partner_id');
        if (foundPartnerField) foundPartnerField.value = '';

        const hiddenName = this.el.querySelector('#correction_name');
        const hiddenEmail = this.el.querySelector('#correction_email');
        if (hiddenName) hiddenName.value = '';
        if (hiddenEmail) hiddenEmail.value = '';

        this._unlockFields();
        this._lastLookedPhone = null;
    },

    // ── FALLBACK ─────────────────────────────────────────────────────────────

    _bindNativeFallback: function (phoneInput) {
        const confirmBtn = this.el.querySelector('.o_appointment_form_confirm_btn');
        if (!confirmBtn) return;
        confirmBtn.addEventListener('click', function (ev) {
            if (!phoneInput.value || phoneInput.value.trim() === '') {
                ev.preventDefault();
                phoneInput.focus();
            }
        });
    },

    // ── CLEANUP ──────────────────────────────────────────────────────────────

    destroy: function () {
        if (this.iti) {
            this.iti.destroy();
            this.iti = null;
        }
        this._super.apply(this, arguments);
    },
});
