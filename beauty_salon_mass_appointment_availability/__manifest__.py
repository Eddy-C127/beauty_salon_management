# -*- coding: utf-8 -*-
{
    'name': 'Gestión de Disponibilidad de Citas',
    'version': '18.0.1.0.0',
    'category': 'Services/Appointment',
    'summary': 'Gestión masiva de disponibilidad de citas por sucursal y categoría',
    'description': """
        Gestión de Disponibilidad de Citas
        ===================================
        
        Este módulo permite gestionar la disponibilidad de citas de forma masiva,
        facilitando cerrar y abrir períodos de agenda para múltiples tipos de cita
        simultáneamente.
        
        Características principales:
        ---------------------------
        * Cerrar disponibilidad: Bloquea citas en períodos específicos
        * Abrir disponibilidad: Restaura configuración normal de citas
        * Modo Masivo: Selección automática por sucursal y categoría
        * Modo Individual: Selección manual de tipos de cita
        * Categorización de servicios: Pestañas, Cejas, Tattoo Lips, Tattoo Brows
        * Campo de estado de disponibilidad visible para usuarios
        * Registro en chatter de todos los cambios
        
        Flujo de trabajo:
        ----------------
        1. Acceder desde Calendar (gantt/list/calendar) o Appointment Types
        2. Seleccionar acción: Cerrar o Abrir disponibilidad
        3. Elegir modo masivo (sucursal + categoría) o individual
        4. Para cerrar: Definir período y motivo
        5. Para abrir: Elegir configuración de disponibilidad normal
        6. Sistema actualiza los appointment types automáticamente
        
        Ventajas:
        ---------
        * Usa la lógica nativa de Odoo (category_time_display)
        * Reversible en segundos
        * Sin registros adicionales innecesarios
        * Totalmente auditable vía chatter
        * Interfaz intuitiva y limpia
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'appointment',        # Módulo de citas
        'calendar',           # Módulo de calendario
        'stock',              # Para stock.warehouse (sucursales)
    ],
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        
        # Vistas
        'views/mass_availability_wizard_view.xml',
        'views/appointment_type_views.xml',
        'views/calendar_event_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}