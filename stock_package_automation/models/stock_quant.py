from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    cbm = fields.Float(
        string='CBM',
        compute='_compute_cbm',
        store=True,
    )

    @api.depends('quantity', 'product_id.volume')
    def _compute_cbm(self):
        for quant in self:
            quant.cbm = quant.quantity * quant.product_id.volume