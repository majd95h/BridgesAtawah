from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, *args, **kwargs):
        """
        تجاوز _action_confirm الأصلي
        """
        result = super()._action_confirm(*args, **kwargs)
        
        # تطبيق الأتمتة على move lines المنشأة للتو
        for move in self:
            if move.picking_id:
                for move_line in move.move_line_ids:
                    if move_line.product_id and not move_line.result_package_id:
                        package, lot = move.picking_id._create_destination_package_and_lot(move_line)
                        if package and lot:
                            move_line.result_package_id = package.id
                            move_line.lot_id = lot.id

        return result
