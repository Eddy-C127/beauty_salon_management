# 🚀 Guía Rápida de Inicio

## Instalación en 3 Pasos

### 1️⃣ Instalar el Módulo
```bash
# Copiar módulo a custom addons
cp -r beauty_salon_appointment_auth /ruta/a/addons/

# Actualizar Odoo
docker restart odoo_container
```

### 2️⃣ Activar en Odoo
```
Apps → Buscar "Appointment Authentication" → Instalar
```

### 3️⃣ Configurar un Tipo de Cita
```
Citas → Tipos de Citas → [Tu cita] → ✅ Require Login to Book
```

---

## ✅ Verificar que Funciona

### Test 1: Usuario Público
1. Abrir navegador en modo incógnito
2. Ir a una cita con `require_login` activado
3. ¿Ves botones de "Ya tengo una cuenta" y "Crear una cuenta"? ✅

### Test 2: Usuario Autenticado
1. Hacer login
2. Ir a la misma cita
3. ¿Ves el botón "Proceed to Payment" o "Confirm Appointment"? ✅

---

## 🐛 ¿Problemas?

### No aparecen los botones de login
```bash
# Verificar configuración
docker exec -it odoo odoo shell -d tu_db
```
```python
appt = env['appointment.type'].browse(8)  # Cambia el ID
print(f"require_login: {appt.require_login}")
```

### Limpiar cache
```
Ctrl + Shift + R en el navegador
```

---

## 📞 Soporte

- 📧 soporte@popstudio.com
- 📖 README completo: [README.md](README.md)