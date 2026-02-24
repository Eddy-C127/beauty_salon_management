/** @odoo-module **/

/**
 * Pop Studio - Mobile Wizard Component
 * 
 * Mejoras UX mobile-first para los wizards de Iniciar/Concluir Cita:
 * - Detecta si el dispositivo es móvil
 * - Aplica clases de Bottom Sheet en dispositivos pequeños
 * - Activa la cámara automáticamente al abrir campos de imagen en móvil
 * - Gestiona scroll y navegación en pestañas
 */

import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted, useRef, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";

// ══ UTILIDADES MÓVIL ══════════════════════════════════════════════════════

/**
 * Detecta si el dispositivo actual es móvil/tablet
 * @returns {boolean}
 */
function isMobileDevice() {
    return window.innerWidth <= 768 ||
        /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

/**
 * Detecta si el dispositivo tiene cámara disponible
 * @returns {Promise<boolean>}
 */
async function hasCameraAvailable() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        return false;
    }
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        return devices.some(device => device.kind === 'videoinput');
    } catch (e) {
        return false;
    }
}

// ══ PATCH DIALOG: Agregar clase Bottom Sheet en móvil ═════════════════════

/**
 * Extiende el comportamiento del Dialog nativo de Odoo para aplicar
 * el estilo Bottom Sheet en dispositivos móviles.
 */
patch(Dialog.prototype, {
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            if (isMobileDevice()) {
                this._applyBottomSheetBehavior();
            }
        });
    },

    /**
     * Aplica clases CSS y comportamiento de Bottom Sheet al dialog.
     * Solo para wizards de Pop Studio (detecta por clase del formulario).
     */
    _applyBottomSheetBehavior() {
        const dialogEl = document.querySelector('.o_dialog:last-child');
        if (!dialogEl) return;

        const formEl = dialogEl.querySelector('.ps-wizard, .popstudio-form');
        if (!formEl) return; // Solo aplicar a wizards Pop Studio

        // Agregar clase de bottom sheet
        dialogEl.classList.add('ps-bottom-sheet-dialog');

        const modalDialog = dialogEl.querySelector('.modal-dialog');
        if (modalDialog) {
            modalDialog.classList.add('ps-modal-bottom-sheet');
        }

        // Agregar soporte para swipe hacia abajo para cerrar
        this._addSwipeToClose(dialogEl);

        // Hacer scroll al tab activo si hay tabs
        this._initTabScroll(dialogEl);

        // Activar cámara en campos de imagen si es disponible
        this._initCameraFields(dialogEl);
    },

    /**
     * Implementa gesture de swipe hacia abajo para cerrar el modal.
     */
    _addSwipeToClose(dialogEl) {
        const modalHeader = dialogEl.querySelector('.modal-header, .ps-wizard-header');
        if (!modalHeader) return;

        let startY = 0;
        let isDragging = false;
        const modalContent = dialogEl.querySelector('.modal-content');

        modalHeader.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            isDragging = true;
        }, { passive: true });

        modalHeader.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            const deltaY = e.touches[0].clientY - startY;
            if (deltaY > 0 && modalContent) {
                modalContent.style.transform = `translateY(${Math.min(deltaY * 0.4, 150)}px)`;
                modalContent.style.opacity = `${Math.max(1 - deltaY / 400, 0.5)}`;
            }
        }, { passive: true });

        modalHeader.addEventListener('touchend', (e) => {
            isDragging = false;
            const deltaY = e.changedTouches[0].clientY - startY;

            if (modalContent) {
                if (deltaY > 100) {
                    // Cerrar modal con swipe suficiente
                    modalContent.style.transform = 'translateY(100%)';
                    modalContent.style.opacity = '0';
                    setTimeout(() => {
                        const closeBtn = dialogEl.querySelector('[special="cancel"], .btn-close');
                        if (closeBtn) closeBtn.click();
                    }, 200);
                } else {
                    // Volver a posición original
                    modalContent.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
                    modalContent.style.transform = 'translateY(0)';
                    modalContent.style.opacity = '1';
                    setTimeout(() => {
                        if (modalContent) {
                            modalContent.style.transition = '';
                        }
                    }, 300);
                }
            }
        }, { passive: true });
    },

    /**
     * Inicializa scroll horizontal en tabs (Pills) para móvil.
     */
    _initTabScroll(dialogEl) {
        const tabs = dialogEl.querySelector('.ps-wizard-notebook .nav-tabs, .ps-wizard-notebook .nav-pills');
        if (!tabs) return;

        // Scroll suave al tab activo
        const activeTab = tabs.querySelector('.nav-link.active');
        if (activeTab) {
            setTimeout(() => {
                activeTab.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }, 100);
        }

        // Scroll al tab al hacer click
        tabs.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                setTimeout(() => {
                    link.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
                }, 50);
            });
        });
    },

    /**
     * Configura campos de imagen para activar la cámara automáticamente en móvil.
     * Agrega atributo 'capture' a los inputs file de imágenes.
     */
    async _initCameraFields(dialogEl) {
        const hasCamera = await hasCameraAvailable();
        if (!hasCamera) return;

        const imageFields = dialogEl.querySelectorAll(
            '.ps-foto-upload-field input[type="file"], ' +
            '.ps-foto-required input[type="file"]'
        );

        imageFields.forEach(input => {
            input.setAttribute('accept', 'image/*');
            input.setAttribute('capture', 'camera');
        });
    },
});

// ══ COMPONENTE: INDICADOR DE PASOS MOBILE ═════════════════════════════════

/**
 * Indicador visual de progreso para los wizards de Pop Studio.
 * Muestra en qué paso se encuentra el usuario (para móvil).
 */
class PopStudioStepIndicator extends Component {
    static template = "beauty_salon_file_management.StepIndicator";
    static props = {
        steps: Array,
        currentStep: Number,
    };
}

// Registrar el componente
registry.category("components").add("PopStudioStepIndicator", PopStudioStepIndicator);

// ══ GESTIÓN DE SCROLL EN MÓVIL ══════════════════════════════════════════

/**
 * Mejora la experiencia de scroll en formularios móviles.
 * Previene que el scroll del modal interfiera con el scroll de la página.
 */
document.addEventListener('DOMContentLoaded', () => {

    // Observer para detectar cuando se abren dialogs de Pop Studio
    const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1 && node.classList?.contains('o_dialog')) {
                    const psWizard = node.querySelector('.ps-wizard');
                    if (psWizard && isMobileDevice()) {
                        _enhanceMobileDialog(node);
                    }
                }
            });
        });
    });

    observer.observe(document.body, { childList: true, subtree: true });
});

/**
 * Mejoras adicionales al dialog en móvil.
 * @param {HTMLElement} dialogEl - El elemento del dialog
 */
function _enhanceMobileDialog(dialogEl) {
    // Prevenir que el fondo haga scroll cuando el dialog está abierto
    document.body.style.overflow = 'hidden';

    // Restaurar cuando el dialog se cierre
    const closeObserver = new MutationObserver(() => {
        if (!document.body.contains(dialogEl)) {
            document.body.style.overflow = '';
            closeObserver.disconnect();
        }
    });
    closeObserver.observe(document.body, { childList: true, subtree: true });

    // Auto-focus al primer campo del tab activo
    setTimeout(() => {
        const activePane = dialogEl.querySelector('.tab-pane.active');
        const firstInput = activePane?.querySelector('input, textarea');
        if (firstInput && !firstInput.readOnly) {
            firstInput.focus();
        }
    }, 400);
}

// ══ FAB BUTTONS: Gestión en móvil ════════════════════════════════════════

/**
 * En móvil, convierte los botones de acción en FABs (Floating Action Buttons).
 * Se aplica a los botones .ps-btn-iniciar y .ps-btn-concluir.
 */
function initFABButtons() {
    if (!isMobileDevice()) return;

    const fabButtons = document.querySelectorAll('.ps-btn-iniciar, .ps-btn-concluir');

    fabButtons.forEach(btn => {
        // Ya están posicionados con CSS fixed, solo agregar clase FAB
        btn.classList.add('ps-fab-btn');

        // Agregar efecto ripple al toque
        btn.addEventListener('touchstart', function (e) {
            const rect = this.getBoundingClientRect();
            const ripple = document.createElement('span');
            ripple.className = 'ps-ripple';
            ripple.style.cssText = `
                position: absolute;
                width: 20px;
                height: 20px;
                background: rgba(255,255,255,0.5);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                left: ${e.touches[0].clientX - rect.left - 10}px;
                top: ${e.touches[0].clientY - rect.top - 10}px;
            `;
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        }, { passive: true });
    });
}

// Inicializar FABs cuando el DOM esté listo y en navegaciones SPA
document.addEventListener('DOMContentLoaded', initFABButtons);
window.addEventListener('popstate', () => setTimeout(initFABButtons, 500));

// ══ LIGHTBOX: Visualizador de fotos en expedientes ══════════════════════

/**
 * Intercepta clics en imágenes de fotos del expediente (modo readonly)
 * y las muestra en un visor fullscreen tipo lightbox.
 */
document.addEventListener('click', (e) => {
    // Buscar si el clic fue en una imagen dentro de las zonas de fotos
    const imgEl = e.target.closest(
        '.ps-foto-card img, ' +
        '.ps-foto-before img, ' +
        '.ps-foto-after img, ' +
        '.ps-foto-upload-container .o_attachment_image'
    );
    if (!imgEl) return;

    // No activar lightbox en modo edición
    const formView = imgEl.closest('.o_form_view');
    if (formView && formView.classList.contains('o_form_editable')) return;

    e.preventDefault();
    e.stopPropagation();

    const overlay = document.createElement('div');
    overlay.className = 'ps-lightbox-overlay';
    overlay.innerHTML = `
        <div class="ps-lightbox-content">
            <img src="${imgEl.src}" alt="Foto del expediente"/>
            <button class="ps-lightbox-close" aria-label="Cerrar">&times;</button>
        </div>
    `;

    overlay.addEventListener('click', (ev) => {
        if (ev.target === overlay || ev.target.classList.contains('ps-lightbox-close')) {
            overlay.style.opacity = '0';
            setTimeout(() => overlay.remove(), 200);
        }
    });

    // Cerrar con Escape
    const escHandler = (ev) => {
        if (ev.key === 'Escape') {
            overlay.style.opacity = '0';
            setTimeout(() => overlay.remove(), 200);
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);

    document.body.appendChild(overlay);
});
