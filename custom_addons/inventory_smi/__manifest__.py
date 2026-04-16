{
    'name': 'Sistem Manajemen Inventaris',
    'version': '17.0.1.0.0',
    'summary': 'Manajemen inventaris bahan baku CV Dunia Offset Printing',
    'author': 'K02-G06',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'bus'],
    'data': [
        'security/smi_security.xml',
        'security/ir.model.access.csv',
        'data/demo_users.xml',
        'views/auth_templates.xml',
        'views/material_views.xml',
        'views/stock_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
