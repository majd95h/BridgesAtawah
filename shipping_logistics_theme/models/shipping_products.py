# -*- coding: utf-8 -*-
from odoo import fields, models

class ShippingProduct(models.Model):
    _name = 'shipping.product'
    _description = 'Shipping Service Product'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Product Name', required=True, translate=True)
    sku = fields.Char(string='SKU', unique=True)
    category = fields.Selection([
        ('machinery', 'Machinery & Equipment'),
        ('materials', 'Building Materials'),
        ('commercial', 'Commercial Goods'),
        ('supplies', 'Supplies & Parts'),
        ('furniture', 'Furniture & Fixtures'),
        ('electronics', 'Electronics'),
    ], string='Category', required=True, default='commercial')
    
    description = fields.Text(string='Description', translate=True)
    image = fields.Image(string='Product Image', max_width=1024, max_height=1024)
    
    price = fields.Float(string='Price (USD)', required=True, digits=(12, 2))
    cost = fields.Float(string='Cost (Internal)', digits=(12, 2))
    
    stock_quantity = fields.Integer(string='Stock Available', default=0)
    lead_time = fields.Integer(string='Lead Time (Days)', default=15)
    
    specs = fields.Text(string='Technical Specifications', translate=True)
    origin = fields.Char(string='Origin', default='China')
    
    is_featured = fields.Boolean(string='Featured Product', default=False)
    is_active = fields.Boolean(string='Active', default=True)
    
    rating = fields.Float(string='Rating', default=4.5, digits=(3, 2))
    review_count = fields.Integer(string='Number of Reviews', default=0)
    
    tags = fields.Char(string='Tags (comma-separated)', translate=True)
