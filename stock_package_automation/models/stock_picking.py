from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _create_destination_package_and_lot(self, move_line):
        """
        إنشاء destination package و lot number تلقائياً
        """
        if not move_line.product_id:
            return

        # استخراج الرقم التسلسلي من picking
        picking_name = self.name  # مثال: WH-CN/IN/00016
        sequence_number = picking_name.split('/')[-1]  # استخراج 00016

        # 1. إنشاء destination package
        package_name = f"pack{sequence_number}"
        existing_package = self.env['stock.quant.package'].search(
            [('name', '=', package_name)],
            limit=1
        )
        
        if not existing_package:
            package = self.env['stock.quant.package'].create({
                'name': package_name,
            })
        else:
            package = existing_package

        # 2. إنشاء Lot/Serial Number
        lot_name = self._generate_lot_name(move_line)
        existing_lot = self.env['stock.lot'].search(
            [
                ('name', '=', lot_name),
                ('product_id', '=', move_line.product_id.id)
            ],
            limit=1
        )

        if not existing_lot:
            lot = self.env['stock.lot'].create({
                'name': lot_name,
                'product_id': move_line.product_id.id,
            })
        else:
            lot = existing_lot

        return package, lot

    def _generate_lot_name(self, move_line):
        """
        توليد اسم الـ lot بصيغة: 
        اسم المنتج + اسم الموردي + تاريخ اليوم + رقم تسلسلي
        """
        product_name = move_line.product_id.name or ''
        vendor_name = ''
        
        # الحصول على اسم الموردي من supplier info
        if move_line.product_id.seller_ids:
            vendor_name = move_line.product_id.seller_ids[0].partner_id.name or ''
        
        today = fields.Date.today().strftime('%Y%m%d')
        
        # البحث عن أكبر رقم تسلسلي موجود للـ lot اليوم
        existing_lots = self.env['stock.lot'].search(
            [
                ('product_id', '=', move_line.product_id.id),
                ('name', 'like', f"{product_name}%{today}%")
            ]
        )
        
        sequence = len(existing_lots) + 1
        
        lot_name = f"{product_name}_{vendor_name}_{today}_{sequence:03d}".replace(' ', '_')
        
        return lot_name

    def button_validate(self):
        """
        تجاوز validate الأصلي لتطبيق الأتمتة
        """
        for picking in self:
            # تطبيق الأتمتة قبل التحقق من الصحة
            for move_line in picking.move_line_ids:
                if move_line.product_id and not move_line.result_package_id:
                    package, lot = picking._create_destination_package_and_lot(move_line)
                    if package and lot:
                        move_line.result_package_id = package.id
                        move_line.lot_id = lot.id

        return super().button_validate()
