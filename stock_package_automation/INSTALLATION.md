# دليل التثبيت والتكوين

## متطلبات النظام
- Odoo 19.0 أو أحدث
- قاعدة بيانات PostgreSQL
- Python 3.8 أو أحدث

## خطوات التثبيت

### الخطوة 1: نسخ الموديول
```bash
cd /path/to/odoo/addons
cp -r stock_package_automation ./
```

### الخطوة 2: تحديث قاعدة البيانات
```bash
python /path/to/odoo-bin -d database_name -u stock_package_automation --stop-after-init
```

أو عبر واجهة Odoo:
1. اذهب إلى Settings > Apps
2. اضغط على "Update Apps List"
3. ابحث عن "Stock Package Automation"
4. اضغط على "Install"

### الخطوة 3: التحقق من التثبيت
بعد التثبيت، تحقق من:
- ظهور الزر الجديد في stock.picking
- ظهور الحقول الجديدة في stock.move.line

## التكوين الأساسي

### 1. التأكد من إعدادات المنتجات
تأكد من أن لديك:
- اسم منتج محدد
- موردي مسند إلى المنتج (اختياري ولكن مفضل)

### 2. إعدادات المواقع (Locations)
تأكد من وجود المواقع المطلوبة:
- موقع المصدر (Source Location)
- موقع الوجهة (Destination Location)

### 3. إعدادات الأنماط (Picking Types)
تحقق من أنماط الـ picking المستخدمة:
- الاسم والرقم التسلسلي محددان بشكل صحيح

## سير العمل التفصيلي

### مثال عملي: إضافة منتج في Stock Move

**السيناريو:**
- لديك stock picking باسم: `WH-CN/IN/00016`
- تريد إضافة منتج "Laptop" من الموردي "Dell"
- التاريخ الحالي: 2024-01-15

**النتيجة المتوقعة:**
1. **Destination Package:** `pack00016`
2. **Lot Number:** `Laptop_Dell_20240115_001`

**الخطوات:**
1. اذهب إلى Inventory > Operations > Stock Moves
2. قم بإنشاء stock move جديد
3. اختر الـ picking من القائمة
4. أضف المنتج والكمية
5. اضغط Save
6. يتم إنشاء الـ package و lot تلقائياً

### استخدام معالج الوجهات

**خطوات الاستخدام:**
1. افتح stock picking
2. اضغط على زر "معالج تعديل الوجهات"
3. يفتح نافذة جديدة تعرض:
   - المنتجات المدرجة
   - الوجهة الحالية لكل منتج
   - حقل لإدخال الوجهة الجديدة
4. عدّل الوجهات حسب الحاجة
5. اضغط "حفظ التغييرات"
6. يتم تحديث الوجهات في stock.move.line

## استكشاف الأخطاء

### المشكلة: لم يتم إنشاء الـ package تلقائياً
**الحلول:**
- تحقق من أن المنتج له اسم محدد
- تأكد من أن الـ picking له رقم تسلسلي
- افحص السجلات للأخطاء: `Logs > Database > Error`

### المشكلة: لم يتم إنشاء الـ lot number
**الحلول:**
- تحقق من أن المنتج مرتبط بـ tracking في الإعدادات
- تأكد من أن تاريخ النظام صحيح
- تحقق من أذونات المستخدم

### المشكلة: زر الـ wizard لا يظهر
**الحلول:**
- قم بتحديث الصفحة (Ctrl + F5)
- تأكد من تثبيت الموديول بشكل صحيح
- افحص السجلات للأخطاء عند التحميل

### المشكلة: خطأ عند الحفظ في الـ wizard
**الحلول:**
- تأكد من أن جميع الحقول مملوءة
- تحقق من أن الموقع الجديد صحيح
- افحص صلاحيات المستخدم

## الخيارات المتقدمة

### تخصيص صيغة Lot Number
لتخصيص صيغة الـ lot number، عدّل الدالة `_generate_lot_name()` في `models/stock_picking.py`:

```python
def _generate_lot_name(self, move_line):
    # مثال: تخصيص الصيغة
    product_name = move_line.product_id.name or ''
    vendor_name = move_line.product_id.seller_ids[0].partner_id.name or '' if move_line.product_id.seller_ids else 'UNKNOWN'
    today = fields.Date.today().strftime('%Y%m%d')
    sequence = len(self.env['stock.lot'].search([('product_id', '=', move_line.product_id.id)])) + 1
    
    # الصيغة المخصصة
    lot_name = f"CUSTOM_{product_name}_{vendor_name}_{today}_{sequence}"
    return lot_name
```

### تغيير صيغة اسم Package
لتغيير صيغة اسم الـ package، عدّل الكود في `models/stock_picking.py`:

```python
# الصيغة الحالية
package_name = f"pack{sequence_number}"

# مثال: صيغة جديدة
package_name = f"PKG-{picking_name}-{sequence_number}"
```

## نصائح الإنتاج

1. **النسخ الاحتياطية:** اعمل نسخة احتياطية من قاعدة البيانات قبل التثبيت
2. **الاختبار:** اختبر الموديول في بيئة تطوير أولاً
3. **المراقبة:** راقب السجلات للتأكد من عدم وجود أخطاء
4. **التوثيق:** احفظ تسجيلات الـ warehouse الخاصة بك

## معايير الأداء

- إنشاء الـ package: أقل من 100 ميلي ثانية
- إنشاء الـ lot: أقل من 150 ميلي ثانية
- تحديث الوجهات: أقل من 50 ميلي ثانية لكل صف

## الصلاحيات المطلوبة

- إدارة Stock / الوصول إلى المستخدم
- إنشاء وتحرير Stock Picking
- إنشاء وتحرير Packages و Lots

## الدعم الفني

للمساعدة:
1. افحص السجلات: `Settings > Technical > Logs`
2. تحقق من صلاحيات المستخدم
3. تأكد من تثبيت المتطلبات

## الإصدارات

| الإصدار | التاريخ | الملاحظات |
|--------|--------|---------|
| 1.0.0 | 2024-01-15 | الإصدار الأول |

## التوافقية

- Odoo 19.0: ✓ كامل الدعم
- Odoo 18.0 وأقدم: ✗ غير مدعوم

## الترخيص

GNU General Public License v3.0 (LGPL-3.0)
