{
    'category': 'services',
    'name': 'Automotive & Spare Parts Management',
    'version': '19.0.1.0.0',
    'depends': ['fleet','mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/vehicle_record_rules.xml',
        'views/spare_part_views.xml',
        'views/fleet_vehicle_views.xml',
        'report/vehicle_spare_parts_report.xml',
    ],
    'installable': True,
    'application': True,
}