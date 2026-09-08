from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import datetime


class StockPackageAutomationTest(TransactionCase):
    
    def setUp(self):
        super().setUp()
        
        # إعداد البيانات الأساسية
        self.warehouse = self.env['stock.warehouse'].search([], limit=1)
        self.picking_type_in = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming')], limit=1
        )
        
        # إنشاء منتج
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'tracking': 'lot',
        })
        
        # إنشاء موردي
        self.vendor = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'is_company': True,
        })
        
        # ربط الموردي بالمنتج
        self.env['product.supplierinfo'].create({
            'product_id': self.product.id,
            'partner_id': self.vendor.id,
            'product_code': 'TEST-001',
        })
    
    def test_package_creation_on_picking(self):
        """
        اختبار إنشاء package عند إنشاء picking
        """
        # إنشاء picking
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00016',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # إنشاء move line
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 5,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # التحقق من إنشاء package
        self.assertIsNotNone(
            move_line.result_package_id,
            "Package should be created automatically"
        )
        
        # التحقق من اسم package
        expected_package_name = 'pack00016'
        self.assertEqual(
            move_line.result_package_id.name,
            expected_package_name,
            f"Package name should be {expected_package_name}"
        )
    
    def test_lot_number_creation(self):
        """
        اختبار إنشاء lot number تلقائياً
        """
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00017',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 3,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # التحقق من إنشاء lot
        self.assertIsNotNone(
            move_line.lot_id,
            "Lot should be created automatically"
        )
        
        # التحقق من صيغة اسم lot
        lot_name = move_line.lot_id.name
        today = fields.Date.today().strftime('%Y%m%d')
        
        self.assertIn(
            self.product.name,
            lot_name,
            "Lot name should contain product name"
        )
        
        self.assertIn(
            today,
            lot_name,
            "Lot name should contain today's date"
        )
    
    def test_package_and_lot_format(self):
        """
        اختبار صيغة الـ package و lot
        """
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00020',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 10,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # التحقق من صيغة package
        package_name = move_line.result_package_id.name
        self.assertTrue(
            package_name.startswith('pack'),
            "Package name should start with 'pack'"
        )
        
        # التحقق من صيغة lot
        lot_name = move_line.lot_id.name
        parts = lot_name.split('_')
        
        self.assertGreaterEqual(
            len(parts),
            3,
            "Lot name should have at least 3 parts separated by underscore"
        )
    
    def test_wizard_line_creation(self):
        """
        اختبار إنشاء wizard lines
        """
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00025',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # إنشاء عدة move lines
        for i in range(3):
            self.env['stock.move.line'].create({
                'picking_id': picking.id,
                'product_id': self.product.id,
                'product_uom_id': self.product.uom_id.id,
                'qty_done': 5 + i,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })
        
        # إنشاء wizard
        wizard = self.env['stock.move.destination.wizard'].create({
            'picking_id': picking.id,
        })
        
        # التحقق من إنشاء wizard lines
        self.assertEqual(
            len(wizard.wizard_line_ids),
            3,
            "Wizard should have 3 lines"
        )
        
        # التحقق من بيانات wizard lines
        for line in wizard.wizard_line_ids:
            self.assertIsNotNone(line.move_line_id)
            self.assertIsNotNone(line.product_id)
            self.assertIsNotNone(line.location_dest_id)
    
    def test_wizard_apply_changes(self):
        """
        اختبار تطبيق التغييرات من الـ wizard
        """
        # إنشاء موقعين مختلفين
        location_1 = self.warehouse.lot_stock_id
        location_2 = self.env['stock.location'].create({
            'name': 'Test Location 2',
            'location_id': self.warehouse.view_location_id.id,
            'usage': 'internal',
        })
        
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00030',
            'picking_type_id': self.picking_type_in.id,
            'location_id': location_1.id,
            'location_dest_id': location_1.id,
        })
        
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 5,
            'location_id': location_1.id,
            'location_dest_id': location_1.id,
        })
        
        # إنشاء wizard و wizard line
        wizard = self.env['stock.move.destination.wizard'].create({
            'picking_id': picking.id,
        })
        
        # تعديل وجهة wizard line
        wizard_line = wizard.wizard_line_ids[0]
        wizard_line.new_location_dest_id = location_2.id
        
        # تطبيق التغييرات
        wizard.action_apply_changes()
        
        # التحقق من تحديث location
        self.assertEqual(
            move_line.location_dest_id.id,
            location_2.id,
            "Location should be updated"
        )
    
    def test_duplicate_package_handling(self):
        """
        اختبار التعامل مع أسماء packages المكررة
        """
        # إنشاء picking أولى
        picking_1 = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00040',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # إنشاء picking ثانية بنفس الرقم التسلسلي
        picking_2 = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00040',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # إنشاء move lines
        move_line_1 = self.env['stock.move.line'].create({
            'picking_id': picking_1.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 5,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        move_line_2 = self.env['stock.move.line'].create({
            'picking_id': picking_2.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 3,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # التحقق من أن package نفسه يتم استخدامه
        self.assertEqual(
            move_line_1.result_package_id.id,
            move_line_2.result_package_id.id,
            "Same package should be used for duplicate names"
        )
    
    def test_lot_number_uniqueness(self):
        """
        اختبار فرادة الـ lot numbers
        """
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00050',
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        # إنشاء عدة move lines في نفس الوقت
        move_lines = []
        for i in range(3):
            move_line = self.env['stock.move.line'].create({
                'picking_id': picking.id,
                'product_id': self.product.id,
                'product_uom_id': self.product.uom_id.id,
                'qty_done': 5,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })
            move_lines.append(move_line)
        
        # التحقق من فرادة الـ lot numbers
        lot_ids = [ml.lot_id.id for ml in move_lines]
        unique_lot_ids = set(lot_ids)
        
        self.assertEqual(
            len(lot_ids),
            len(unique_lot_ids),
            "All lot numbers should be unique"
        )
