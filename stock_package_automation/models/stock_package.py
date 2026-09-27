from odoo import api, fields, models


class StockPackage(models.Model):
    _inherit = 'stock.package'

    cbm = fields.Float(
        string='CBM',
        compute='_compute_cbm',
        digits='Volume',
    )

    @api.depends(
        'contained_quant_ids.quantity',
        'contained_quant_ids.product_id',
        'contained_quant_ids.product_id.volume',
    )
    def _compute_cbm(self):
        for package in self:
            package.cbm = sum(
                quant.quantity * quant.product_id.volume
                for quant in package.contained_quant_ids
            )