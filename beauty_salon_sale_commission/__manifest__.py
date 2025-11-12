{
    'name': 'Beauty Salon - Sale Commission Enhancements',
    'version': '1.1', # Sugiero incrementar la versión
    'summary': 'Enhances sale_commission with fully invoiced types and real employee.',
    'description': """
        Este módulo extiende la funcionalidad de 'sale_commission' para:
        1. Agregar nuevos tipos de cálculo de comisión basados en órdenes "Totalmente Facturadas".
        2. Agregar un campo 'date_fully_invoiced' a 'sale.order' que se pobla automáticamente.
        3. Extender el reporte de 'achievement.report' para incluir la nueva fecha y el cliente.
        4. (CONSOLIDADO) Agregar el 'Empleado Real' a los reportes de comisión (movido de 'beauty_salon').
        5. (CORREGIDO) Arreglar el problema de zona horaria (timezone) en ambos reportes de comisiones.
    """,
    'author': 'Tu Nombre',
    'category': 'Sales/Commissions',
    'depends': [
        'sale_commission',  # Dependencia base
        'sale',             # Para extender sale.order
        'hr',               # NUEVA DEPENDENCIA: para 'real_employee_id'
    ],
    'data': [
        # Seguridad (Asegúrate de tener este archivo)
        'security/ir.model.access.csv',
        
        # Vistas de 'date_fully_invoiced'
        'views/sale_order_views.xml',
        'views/commission_plan_achievement_views.xml',
        'views/sale_commission_achievement_report_views.xml',
        
        # Vistas de 'real_employee_id' (MOVIDAS AQUÍ)
        'views/sale_commission_report_views.xml', # <-- LÍNEA NUEVA
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}