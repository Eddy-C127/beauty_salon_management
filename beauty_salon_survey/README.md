# Beauty Salon - Survey & Warranty System

## Descripción

Sistema integral de encuestas de satisfacción, gestión de garantías y ajuste de comisiones para Pop Studio.

## Características Principales

### ✅ Iteración 1 (Actual)
- Campos de encuesta en citas (`calendar.event`)
- Campos de garantía en citas
- Nuevo estado: `warranty_completed`
- Campos relacionados en órdenes de venta
- Ajuste de comisiones (solo cuando `invoice_status='invoiced'`)
- Vistas extendidas con información de encuestas
- Sistema de permisos

### 🔄 Próximas Iteraciones
- [ ] Configuración del sistema
- [ ] Trigger automático al concluir cita
- [ ] Envío de encuestas
- [ ] Clasificación automática (positiva/negativa)
- [ ] Sistema de garantías con aprobación
- [ ] Webhook a n8n
- [ ] Dashboards y reportes

## Instalación

1. Copiar módulo a `addons/`
2. Actualizar lista de aplicaciones
3. Instalar `Beauty Salon - Survey & Warranty System`
```bash
docker-compose restart