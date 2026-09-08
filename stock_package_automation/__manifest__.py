{
    'name': 'Stock Package Automation',
    'version': '19.0.1.0.0',
    'category': 'Stock',
    'summary': 'Automate package creation and lot number generation in stock moves',
    'author': 'Your Company',
    'depends': [
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',

        'wizards/stock_move_destination_wizard_views.xml',

        'views/stock_move_line_views.xml',
        'views/stock_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
