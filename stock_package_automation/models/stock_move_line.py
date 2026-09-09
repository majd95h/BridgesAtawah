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
        if not move_line or not move_line.product_id:
            return None, None

        try:
            # استخراج الرقم التسلصلي من picking
            picking_name = self.name if self.name else 'UNKNOWN'  # مثال: WH-CN/IN/00016
            # استخراج آخر جزء من الاسم
            sequence_number = picking_name.split('/')[-1] if '/' in picking_name else picking_name
        except Exception as e:
            _logger.warning(f"Error extracting sequence: {str(e)}")
            return None, None

        package = None
        lot = None
        
        try:
            # 1. إنشاء destination package
            package_name = f"pack{sequence_number}"
            try:
                existing_package = self.env['stock.package'].search(
                    [('name', '=', package_name)],
                    limit=1
                )
                
                if not existing_package:
                    package = self.env['stock.package'].create({
                        'name': package_name,
                    })
                else:
                    package = existing_package
            except Exception as e:
                _logger.warning(f"Error creating package {package_name}: {str(e)}")
                package = None

            # 2. إنشاء Lot/Serial Number
            try:
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
            except Exception as e:
                _logger.warning(f"Error creating lot: {str(e)}")
                lot = None
                
        except Exception as e:
            _logger.error(f"Error in _create_destination_package_and_lot: {str(e)}")
            return None, None

        return package, lot

    def _generate_lot_name(self, move_line):
        """
        توليد اسم الـ lot بصيغة: 
        اسم المنتج + اسم الموردي + تاريخ اليوم + رقم تسلسلي
        """
        try:
            product_name = move_line.product_id.name or 'PRODUCT'
            # تنظيف اسم المنتج من الأحرف الخاصة
            product_name = product_name.replace(' ', '_').replace('/', '_')
            
            vendor_name = 'NOVENDOR'
            
            # الحصول على اسم الموردي من supplier info
            if move_line.product_id.seller_ids:
                vendor_name = move_line.product_id.seller_ids[0].partner_id.name or 'UNKNOWN'
                vendor_name = vendor_name.replace(' ', '_').replace('/', '_')
            
            today = fields.Date.today().strftime('%Y%m%d')
            
            # البحث عن أكبر رقم تسلسلي موجود للـ lot اليوم
            try:
                existing_lots = self.env['stock.lot'].search(
                    [
                        ('product_id', '=', move_line.product_id.id),
                        ('name', 'like', f"{product_name}%{today}%")
                    ]
                )
                sequence = len(existing_lots) + 1
            except:
                sequence = 1
            
            lot_name = f"{product_name}_{vendor_name}_{today}_{sequence:03d}"
            
            return lot_name
        except Exception as e:
            _logger.warning(f"Error generating lot name: {str(e)}")
            # إرجاع اسم افتراضي في حالة الخطأ
            import time
            return f"LOT_{int(time.time())}"

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
