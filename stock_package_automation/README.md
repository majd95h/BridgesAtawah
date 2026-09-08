# موديول Stock Package Automation

## الوصف
موديول مخصص لـ Odoo 19 لأتمتة إنشاء الحزم (Packages) والرقم المسلسل (Lot Numbers) في عمليات نقل المخزون.

## الميزات الرئيسية

### 1. إنشاء Destination Package تلقائياً
عند إضافة منتج في stock move، يتم إنشاء destination package تلقائياً:
- يحمل اسم يتضمن الرقم التسلسلي لـ stock.picking
- مثال: إذا كان اسم picking هو `WH-CN/IN/00016`، سيتم إنشاء package باسم `pack00016`

### 2. إنشاء Lot/Serial Number تلقائياً
يتم إنشاء رقم مسلسل تلقائي بالصيغة التالية:
```
اسم_المنتج_اسم_الموردي_تاريخ_اليوم_رقم_تسلسلي
```

**مثال:**
```
Product_A_Vendor_Name_20240115_001
```

### 3. معالج تعديل الوجهات (Destination Wizard)
زر جديد في نموذج stock.picking يفتح معالج يحتوي على:
- قائمة بجميع المنتجات المدرجة في stock move
- الوجهة الحالية لكل منتج
- إمكانية تعديل الوجهة الجديدة
- زر حفظ التغييرات يطبق التعديلات على جميع المنتجات

## التثبيت

1. انسخ الموديول إلى مجلد addons:
```bash
cp -r stock_package_automation /path/to/addons/
```

2. قم بتحديث قائمة التطبيقات في Odoo:
   - اذهب إلى Settings > Apps
   - ابحث عن "Stock Package Automation"
   - انقر على Install

## الاستخدام

### سير العمل الأساسي
1. قم بإنشاء stock picking جديد
2. أضف المنتجات إلى الـ stock move
3. سيتم إنشاء destination package و lot number تلقائياً
4. للتحقق من الوجهات أو تعديلها، انقر على زر "معالج تعديل الوجهات"
5. في الـ wizard، قم بتعديل الوجهات إذا لزم الأمر
6. انقر على "حفظ التغييرات"

## الملفات الرئيسية

### Models
- `models/stock_picking.py` - توسيع stock.picking
- `models/stock_move.py` - توسيع stock.move
- `models/stock_move_line.py` - توسيع stock.move.line

### Wizards
- `wizards/stock_move_destination_wizard.py` - معالج تعديل الوجهات

### Views
- `views/stock_move_line_views.xml` - واجهات stock.move.line
- `views/stock_move_views.xml` - واجهات stock.move
- `views/stock_move_destination_wizard_views.xml` - واجهات الـ wizard

### Security
- `security/ir.model.access.csv` - صلاحيات الوصول

## الدوال الرئيسية

### `_create_destination_package_and_lot()`
تقوم بإنشاء destination package و lot number بناءً على معايير محددة.

### `_generate_lot_name()`
توليد اسم الـ lot بصيغة محددة تتضمن معلومات المنتج والموردي والتاريخ.

### `action_apply_changes()`
تطبيق التغييرات على وجهات المنتجات المحددة في الـ wizard.

## ملاحظات تقنية

- الموديول يستخدم overrides على الدوال الأصلية:
  - `create()` في stock.move.line
  - `write()` في stock.move.line
  - `_action_confirm()` في stock.move
  - `button_validate()` في stock.picking

- يتم استخدام TransientModel للـ wizard لضمان عدم حفظ البيانات مؤقتة في قاعدة البيانات

- جميع الحقول المرتبطة readonly في الـ wizard لمنع الأخطاء أثناء التحديث

## معالجة الأخطاء

الموديول يتعامل مع الحالات التالية:
- عدم وجود موردي محدد للمنتج
- وجود اسم package مشابه
- وجود lot number مشابه
- عدم وجود اسم تسلسلي في الـ picking

## الإصدار
- إصدار Odoo: 19.0
- إصدار الموديول: 1.0.0

## الدعم والتطوير
للمزيد من المعلومات أو الإبلاغ عن المشاكل، يرجى التواصل مع فريق التطوير.
