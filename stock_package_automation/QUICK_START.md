# دليل البدء السريع

## التثبيت السريع

### 1. نسخ الملفات
```bash
cp -r stock_package_automation /path/to/odoo/addons/
```

### 2. التثبيت عبر Odoo
1. اذهب إلى `Apps > Update Apps List`
2. ابحث عن "Stock Package Automation"
3. انقر على "Install"

## الاستخدام الأساسي

### السيناريو 1: إنشاء تلقائي للـ Package و Lot

**الخطوات:**
1. اذهب إلى `Inventory > Operations > Receipts`
2. أنشئ عملية استلام جديدة
3. أضف منتج إلى الـ stock move
4. **النتيجة التلقائية:**
   - ✅ يتم إنشاء destination package
   - ✅ يتم إنشاء lot number

### السيناريو 2: تعديل الوجهات

**الخطوات:**
1. افتح أي stock picking
2. انقر على زر "معالج تعديل الوجهات"
3. عدّل الوجهات الجديدة في الـ wizard
4. انقر "حفظ التغييرات"

## البيانات المنشأة

### مثال عملي

إذا كنت تعمل مع:
- **Picking Name:** WH-CN/IN/00016
- **Product:** Laptop
- **Vendor:** Dell
- **Today's Date:** 2024-01-15

### ستحصل على:
```
✅ Package: pack00016
✅ Lot Number: Laptop_Dell_20240115_001
```

## الملفات الرئيسية

```
stock_package_automation/
├── __manifest__.py           # تعريف الموديول
├── __init__.py              # تحميل الموديول
├── models/                  # نماذج البيانات
│   ├── stock_picking.py     # منطق إنشاء الـ package و lot
│   ├── stock_move.py        # توسيع stock.move
│   └── stock_move_line.py   # توسيع stock.move.line
├── wizards/                 # الـ wizards
│   └── stock_move_destination_wizard.py
├── views/                   # الـ views
│   ├── stock_move_line_views.xml
│   ├── stock_move_views.xml
│   └── stock_move_destination_wizard_views.xml
├── security/
│   └── ir.model.access.csv  # الصلاحيات
└── tests/                   # الاختبارات
    └── test_stock_package_automation.py
```

## الدوال الرئيسية

### 1. `_create_destination_package_and_lot()`
```python
# ينشئ package و lot تلقائياً
picking._create_destination_package_and_lot(move_line)
```

### 2. `_generate_lot_name()`
```python
# يولد اسم lot بصيغة محددة
lot_name = picking._generate_lot_name(move_line)
# النتيجة: "Product_Vendor_20240115_001"
```

### 3. `action_apply_changes()`
```python
# يطبق التغييرات من الـ wizard
wizard.action_apply_changes()
```

## الأخطاء الشائعة وحلولها

### ❌ لم يتم إنشاء الـ package
**السبب:** المنتج بدون اسم أو picking بدون رقم
**الحل:** تأكد من:
- المنتج له اسم محدد
- الـ picking له رقم تسلسلي

### ❌ لم يتم إنشاء الـ lot
**السبب:** عدم تعريف المنتج كـ tracked
**الحل:**
- اذهب إلى Product > Settings > Tracking
- حدد "Track Lots"

### ❌ زر الـ wizard لا يظهر
**السبب:** قد لم يتم تحديث الصفحة
**الحل:**
- اضغط Ctrl + F5 (تحديث كامل)
- تحقق من تثبيت الموديول

## نصائح الاستخدام

### ✅ أفضل الممارسات

1. **قبل البدء:**
   - تأكد من ربط المنتجات بالموردين
   - تحدد tracking mode للمنتجات

2. **أثناء الاستخدام:**
   - استخدم رقم تسلسلي واضح للـ picking
   - تحقق من الـ package و lot المنشأة

3. **بعد العملية:**
   - ادخل إلى تقرير الـ packages
   - راقب السجلات للأخطاء

### ⚠️ تحذيرات

- لا تعدّل اسم الـ package أو lot يدويا بعد الإنشاء
- لا تستخدم أحرف خاصة في أسماء الـ picking
- تأكد من وجود المواقع قبل استخدام الـ wizard

## الإعدادات المتقدمة

### تخصيص صيغة الـ Lot Number

عدّل الدالة `_generate_lot_name()` في `models/stock_picking.py`:

```python
# الصيغة الحالية
lot_name = f"{product_name}_{vendor_name}_{today}_{sequence:03d}"

# مثال: صيغة مخصصة
lot_name = f"LOT-{product_name}-{today}-{sequence}"
```

### تخصيص صيغة اسم الـ Package

عدّل السطر في `models/stock_picking.py`:

```python
# الصيغة الحالية
package_name = f"pack{sequence_number}"

# مثال: صيغة مخصصة
package_name = f"PKG-{picking_name}-{sequence_number}"
```

## الاختبار

### اختبار سريع

```python
# في console Odoo
picking = env['stock.picking'].create({
    'name': 'WH-TEST/IN/00001',
    'picking_type_id': env.ref('stock.picking_type_in').id,
    'location_id': env.ref('stock.stock_location_suppliers').id,
    'location_dest_id': env.ref('stock.stock_location_stock').id,
})

move_line = env['stock.move.line'].create({
    'picking_id': picking.id,
    'product_id': env.ref('product.product_product_8').id,
    'qty_done': 5,
    'product_uom_id': env.ref('uom.product_uom_unit').id,
    'location_id': env.ref('stock.stock_location_suppliers').id,
    'location_dest_id': env.ref('stock.stock_location_stock').id,
})

# تحقق من النتائج
print(f"Package: {move_line.result_package_id.name}")
print(f"Lot: {move_line.lot_id.name}")
```

## الأسئلة الشائعة

### س: هل يمكن تعديل الـ package و lot بعد الإنشاء؟
**ج:** نعم، يمكنك تعديلها يدويا إذا لزم الأمر.

### س: ماذا يحدث إذا كان لديّ نفس رقم picking؟
**ج:** سيتم استخدام نفس الـ package للعمليات المتعددة.

### س: هل يعمل مع internal transfers؟
**ج:** نعم، يعمل مع جميع أنواع الـ picking.

### س: هل يؤثر على الأداء؟
**ج:** لا، الأتمتة خفيفة وسريعة جداً.

## معلومات التواصل

- **الإصدار:** 1.0.0
- **متطلب Odoo:** 19.0+
- **الترخيص:** LGPL-3.0

## الدعم الفني

في حالة وجود مشاكل:
1. افحص السجلات: `Settings > Technical > Logs`
2. تحقق من الصلاحيات
3. جرّب في بيئة اختبار

---

**آخر تحديث:** 2024-01-15
