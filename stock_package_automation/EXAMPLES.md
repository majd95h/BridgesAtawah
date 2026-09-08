# أمثلة على الاستخدام البرمجي

## مثال 1: إنشاء Stock Move مع Package و Lot تلقائياً

```python
from odoo import models, fields, api

class MyCustomModel(models.Model):
    _name = 'my.custom.model'

    @api.model
    def create_stock_move_with_automation(self):
        """
        مثال على إنشاء stock move مع الأتمتة
        """
        # إنشاء picking
        picking = self.env['stock.picking'].create({
            'name': 'WH-CN/IN/00016',
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        })
        
        # إنشاء move line
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'move_id': False,  # سيتم إنشاء move تلقائياً
            'product_id': self.env.ref('product.product_product_laptop').id,
            'qty_done': 5,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        })
        
        # تلقائياً سيتم إنشاء:
        # - destination package باسم: pack00016
        # - lot number باسم: Laptop_Dell_20240115_001
        
        return picking
```

## مثال 2: البحث عن Packages المنشأة

```python
def search_auto_created_packages(self):
    """
    البحث عن جميع الـ packages المنشأة تلقائياً
    """
    # البحث عن packages التي تبدأ بـ "pack"
    packages = self.env['stock.quant.package'].search([
        ('name', 'ilike', 'pack%')
    ])
    
    for package in packages:
        print(f"Package: {package.name}")
        print(f"Quants: {len(package.quant_ids)}")
```

## مثال 3: تحديث وجهات Multiple Items برمجياً

```python
def update_destinations_programmatically(self, picking_id, new_destination):
    """
    تحديث وجهات جميع items في picking محددة
    """
    picking = self.env['stock.picking'].browse(picking_id)
    
    for move_line in picking.move_line_ids:
        # تحديث الوجهة الجديدة
        move_line.write({
            'location_dest_id': new_destination.id
        })
        
        # تحديث الـ move المرتبط
        if move_line.move_id:
            move_line.move_id.location_dest_id = new_destination.id
    
    return True
```

## مثال 4: إنشاء Lot Number مخصص

```python
def create_custom_lot_number(self, product_id, vendor_id):
    """
    إنشاء lot number مخصص بصيغة مختلفة
    """
    product = self.env['product.product'].browse(product_id)
    vendor = self.env['res.partner'].browse(vendor_id)
    
    # الصيغة المخصصة
    today = fields.Date.today().strftime('%d-%m-%Y')
    lot_name = f"{product.name}_{vendor.name}_{today}"
    
    # التحقق من عدم وجود lot بنفس الاسم
    existing = self.env['stock.lot'].search([
        ('name', '=', lot_name),
        ('product_id', '=', product_id)
    ])
    
    if not existing:
        lot = self.env['stock.lot'].create({
            'name': lot_name,
            'product_id': product_id,
        })
        return lot
    
    return existing[0]
```

## مثال 5: استخدام الـ Wizard برمجياً

```python
def open_destination_wizard(self, picking_id):
    """
    فتح معالج الوجهات برمجياً
    """
    wizard = self.env['stock.move.destination.wizard'].create({
        'picking_id': picking_id,
    })
    
    # الحصول على القيم الافتراضية
    default_vals = wizard.default_get(['wizard_line_ids'])
    
    # تحديث الـ wizard
    wizard.write(default_vals)
    
    return {
        'type': 'ir.actions.act_window',
        'name': 'معالج تعديل الوجهات',
        'res_model': 'stock.move.destination.wizard',
        'res_id': wizard.id,
        'view_mode': 'form',
        'target': 'new',
    }
```

## مثال 6: إنشاء Report مخصص للـ Packages

```python
class PackageReport(models.AbstractModel):
    _name = 'report.stock_package_automation.package_report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        """
        إنشاء report يعرض جميع الـ packages المنشأة
        """
        picking = self.env['stock.picking'].browse(docids)
        
        packages_data = []
        for move_line in picking.move_line_ids:
            if move_line.result_package_id:
                packages_data.append({
                    'package': move_line.result_package_id.name,
                    'product': move_line.product_id.name,
                    'quantity': move_line.qty_done,
                    'lot': move_line.lot_id.name if move_line.lot_id else '-',
                })
        
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'picking': picking,
            'packages': packages_data,
        }
```

## مثال 7: دالة Helper للتحقق من الـ Automation

```python
def verify_automation_applied(self, move_line_id):
    """
    التحقق من أن الأتمتة تم تطبيقها بشكل صحيح
    """
    move_line = self.env['stock.move.line'].browse(move_line_id)
    
    checks = {
        'has_package': bool(move_line.result_package_id),
        'has_lot': bool(move_line.lot_id),
        'package_name_valid': move_line.result_package_id.name.startswith('pack') if move_line.result_package_id else False,
        'lot_format_valid': '_' in move_line.lot_id.name if move_line.lot_id else False,
    }
    
    all_passed = all(checks.values())
    
    return {
        'passed': all_passed,
        'details': checks,
        'move_line': {
            'product': move_line.product_id.name,
            'package': move_line.result_package_id.name if move_line.result_package_id else None,
            'lot': move_line.lot_id.name if move_line.lot_id else None,
        }
    }
```

## مثال 8: Batch Processing لـ Multiple Pickings

```python
def process_multiple_pickings(self, picking_ids):
    """
    معالجة عدة pickings مرة واحدة
    """
    pickings = self.env['stock.picking'].browse(picking_ids)
    
    results = []
    for picking in pickings:
        try:
            # تطبيق الأتمتة على جميع move lines
            for move_line in picking.move_line_ids:
                if not move_line.result_package_id or not move_line.lot_id:
                    package, lot = picking._create_destination_package_and_lot(move_line)
                    if package and lot:
                        move_line.result_package_id = package.id
                        move_line.lot_id = lot.id
            
            results.append({
                'picking': picking.name,
                'status': 'success',
                'items': len(picking.move_line_ids)
            })
        except Exception as e:
            results.append({
                'picking': picking.name,
                'status': 'error',
                'error': str(e)
            })
    
    return results
```

## مثال 9: Event Handler للتكامل مع Signals

```python
from odoo.addons.base.models.ir_model import IrModel

def post_init_hook(cr, registry):
    """
    Hook يتم تنفيذه بعد تثبيت الموديول
    """
    env = registry['ir.model'].env(user=registry['ir.model'].SUPERUSER_ID)
    
    # إنشاء account tags أو أي إعداد أولي
    print("Stock Package Automation module initialized successfully")

def uninstall_hook(cr, registry):
    """
    Hook يتم تنفيذه عند حذف الموديول
    """
    # تنظيف أي بيانات إذا لزم الأمر
    print("Stock Package Automation module uninstalled")
```

## مثال 10: Scheduled Action

```python
class StockPickingAutomation(models.Model):
    _name = 'stock.picking.automation'
    
    @api.model
    def scheduled_package_verification(self):
        """
        عملية مجدولة للتحقق من الـ packages
        """
        # البحث عن pickings التي لم يتم التحقق منها
        pickings = self.env['stock.picking'].search([
            ('state', '=', 'confirmed'),
            ('create_date', '>=', fields.Date.today()),
        ])
        
        for picking in pickings:
            missing_packages = 0
            for move_line in picking.move_line_ids:
                if not move_line.result_package_id:
                    missing_packages += 1
            
            if missing_packages > 0:
                # إرسال تنبيه
                message = f"Picking {picking.name} has {missing_packages} items without packages"
                picking.message_post(body=message)
```

## ملاحظات مهمة

1. **التعامل مع الأخطاء:** دائماً استخدم try-except عند التعامل مع العمليات الحرجة
2. **الأداء:** للـ batch operations، استخدم `batch_create()` بدلاً من create loop
3. **التسجيل:** استخدم logging للتتبع في بيئة الإنتاج
4. **الاختبار:** اختبر كل الأمثلة في بيئة تطوير أولاً

## تشخيص المشاكل

```python
def diagnose_automation_issues(self):
    """
    دالة تشخيصية للعثور على المشاكل
    """
    issues = []
    
    # التحقق من وجود packages بدون lot
    lines_without_lot = self.env['stock.move.line'].search([
        ('result_package_id', '!=', False),
        ('lot_id', '=', False),
    ])
    
    if lines_without_lot:
        issues.append(f"{len(lines_without_lot)} lines have packages but no lots")
    
    # التحقق من duplicate package names
    packages = self.env['stock.quant.package'].search([
        ('name', 'ilike', 'pack%')
    ])
    
    package_names = [p.name for p in packages]
    duplicates = [name for name in set(package_names) if package_names.count(name) > 1]
    
    if duplicates:
        issues.append(f"Duplicate package names found: {duplicates}")
    
    return {
        'has_issues': len(issues) > 0,
        'issues': issues,
    }
```
