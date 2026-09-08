from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # إضافة حقل لتتبع ما إذا تم إنشاء الـ package والـ lot تلقائياً
    auto_package_lot_created = fields.Boolean(
        'Auto Package & Lot Created',
        default=False,
        readonly=True
    )

    @api.model
    def create(self, values):
        """
        تجاوز create لتطبيق الأتمتة على الـ move lines المنشأة حديثاً
        """
        result = super().create(values)
        
        # تطبيق الأتمتة إذا لم تكن مطبقة سابقاً
        if result.move_id and result.move_id.picking_id:
            if result.product_id and not result.result_package_id:
                package, lot = result.move_id.picking_id._create_destination_package_and_lot(result)
                if package and lot:
                    result.result_package_id = package.id
                    result.lot_id = lot.id
                    result.auto_package_lot_created = True
        
        return result

    def write(self, values):
        """
        تجاوز write لتطبيق الأتمتة عند تحديث الـ product_id
        """
        # تطبيق الأتمتة إذا تم تحديث product_id
        if 'product_id' in values:
            for line in self:
                if line.move_id and line.move_id.picking_id:
                    if not line.result_package_id or not line.lot_id:
                        package, lot = line.move_id.picking_id._create_destination_package_and_lot(line)
                        if package and lot:
                            values['result_package_id'] = package.id
                            values['lot_id'] = lot.id
                            values['auto_package_lot_created'] = True

        return super().write(values)
