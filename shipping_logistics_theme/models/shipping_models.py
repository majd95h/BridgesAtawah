# -*- coding: utf-8 -*-
from odoo import fields, models

class ShippingService(models.Model):
    _name = 'shipping.service'
    _description = 'Shipping Service'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    code = fields.Char(string='Number', required=True, default='01')
    category = fields.Char(string='Category Tag', required=True)
    name = fields.Char(string='Title', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    icon_type = fields.Selection([
        ('factory', 'Factory/Machinery'),
        ('construction', 'Construction'),
        ('wholesale', 'Wholesale'),
        ('lcl', 'LCL/Small'),
    ], string='Icon Type', default='factory')
    link_url = fields.Char(string='Learn more URL', default='#contact')
    active = fields.Boolean(default=True)

class ShippingProcessStep(models.Model):
    _name = 'shipping.process.step'
    _description = 'Shipping Process Step'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    code = fields.Char(string='Number', required=True, default='01')
    name = fields.Char(string='Title', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(default=True)

class ShippingBlogArticle(models.Model):
    _name = 'shipping.blog.article'
    _description = 'Shipping Blog Article'
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True, translate=True)
    slug = fields.Char(string='URL Slug', unique=True)
    excerpt = fields.Text(string='Excerpt', translate=True)
    content = fields.Html(string='Content', translate=True)
    is_published = fields.Boolean(default=False)
    create_date = fields.Datetime(readonly=True)
