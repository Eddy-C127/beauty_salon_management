# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [18.0.1.0.0] - 2025-10-28

### ✨ Agregado
- Campo booleano `require_login` en `appointment.type`
- Template QWeb que muestra botones de login/signup para usuarios públicos
- Ocultación automática de botones de submit cuando se requiere autenticación
- Preservación de parámetros de URL durante el flujo de login/signup
- Autocompletado de formulario después de autenticación
- Compatibilidad con `website_appointment_sale` para pagos
- Traducciones completas a español México (es_MX)
- Documentación README completa
- Guía rápida de inicio (QUICKSTART.md)
- Vista de configuración en backend con mensajes informativos

### 🔧 Técnico
- Herencia limpia de templates sin modificar código core
- JavaScript para URL encoding correcto de parámetros de redirect
- CSS para ocultar botones cuando es necesario
- Prioridad de template: 99 (evita conflictos)
- Sin controladores custom (usa flujo nativo de Odoo)

### 🐛 Correcciones
- Fix: Botones duplicados cuando usuario autenticado
- Fix: Parámetros perdidos en redirect de login
- Fix: Compatibilidad con módulos de pago de Enterprise
- Fix: Responsive en dispositivos móviles

### 📚 Documentación
- README.md completo con casos de uso
- Guía de troubleshooting
- Ejemplos de configuración
- Estructura del módulo explicada

### 🔐 Seguridad
- Validación frontend y backend
- URL encoding correcto para prevenir inyección
- No expone datos sensibles en URLs

---

## [Futuras Versiones]

### 🎯 Planeado para 18.0.2.0.0
- [ ] Traducciones adicionales (inglés, español de España)
- [ ] Configuración de mensaje personalizado por tipo de cita
- [ ] Opción de "login con Google/Facebook"
- [ ] Analytics de conversión de signup
- [ ] Webhook para notificar creación de cuenta desde cita

### 💡 Ideas en Consideración
- [ ] Permitir reserva temporal con confirmación por email
- [ ] Recordatorio automático para usuarios que no completaron registro
- [ ] Dashboard de estadísticas de conversión
- [ ] A/B testing de mensajes de autenticación

---

## Notas de Versión

### Convenciones de Versionado

Seguimos [Semantic Versioning](https://semver.org/):
- **MAJOR**: Cambios incompatibles con versiones anteriores
- **MINOR**: Nueva funcionalidad compatible con versiones anteriores
- **PATCH**: Correcciones de bugs compatibles con versiones anteriores

Formato de versión: `ODOO_VERSION.MAJOR.MINOR.PATCH`
- Ejemplo: `18.0.1.2.3` = Odoo 18.0, Major 1, Minor 2, Patch 3

### Categorías de Cambios

- **✨ Agregado**: Nueva funcionalidad
- **🔧 Cambiado**: Cambios en funcionalidad existente
- **❌ Deprecado**: Funcionalidad que será removida
- **🗑️ Removido**: Funcionalidad removida
- **🐛 Corregido**: Corrección de bugs
- **🔐 Seguridad**: Cambios relacionados con seguridad

---

*Última actualización: 28 de Octubre, 2025*