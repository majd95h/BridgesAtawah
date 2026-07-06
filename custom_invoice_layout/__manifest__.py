# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice Layout (Gold Bilingual)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom gold-themed bilingual (English/Arabic) invoice PDF layout',
    'description': """
Custom Invoice Layout
======================
Adds a new "Gold Bilingual Invoice" print button on customer invoices.
Includes bilingual header, billing, totals sections, amount-in-words,
and custom SVG decorations.
""",
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/invoice_view.xml',
    ],
  
    'installable': True,
    'application': False,
    'auto_install': False,
}