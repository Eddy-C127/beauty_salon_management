# Copyright 2025 SmartGeeks
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Beauty Salon",
    "version": "18.0.1.0.1",
    "summary": """Beauty Salon Management""",
    "author": "SmartGeeks",
    "website": "https://smartgeeks.mx/",
    "license": "LGPL-3",
    "category": "Installer",
    "depends": [
        "base",
        "website_appointment_sale",
        "web",
        "sale_management",
        "calendar",
        "appointment_account_payment",
        "hr",
        "sale_commission"
    ],
    "data": [
        "views/hr_employee_views.xml",
        "views/calendar_event_views.xml",
        "views/sale_commissions_views.xml",
    ],
    "demo": [],
    "auto_install": False,
    "application": False,
}
