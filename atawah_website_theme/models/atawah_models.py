# -*- coding: utf-8 -*-
from odoo import fields, models


class AtawahService(models.Model):
    """الخدمات الست المعروضة في قسم 'What we do' بالصفحة الرئيسية.

    إدارة هذه السجلات تتم من: الموقع الإلكتروني ▸ Atawah ▸ Services
    بدلاً من تعديل كود XML مباشرة في كل مرة.
    """
    _name = 'atawah.service'
    _description = 'Atawah Service Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    code = fields.Char(
        string='Number', required=True, default='01',
        help="الرقم الظاهر أعلى البطاقة، مثال: 01"
    )
    category = fields.Char(
        string='Category Tag', required=True,
        help="الوسم الصغير أعلى العنوان، مثال: Official Supplier"
    )
    name = fields.Char(string='Title', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    link_url = fields.Char(string='Learn more URL', default='#contact')
    active = fields.Boolean(default=True)


class AtawahProcessStep(models.Model):
    """خطوات العمل الأربع في قسم 'How we work'."""
    _name = 'atawah.process.step'
    _description = 'Atawah Process Step'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    code = fields.Char(string='Number', required=True, default='01')
    name = fields.Char(string='Title', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(default=True)
