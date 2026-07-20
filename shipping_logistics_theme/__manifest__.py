# -*- coding: utf-8 -*-
{
    'name': 'Shipping & Logistics Theme',
    'summary': 'Professional homepage theme for import/shipping business (Inspired by ATAWAH design)',
    'description': """
Shipping & Logistics Business Theme
====================================
موديول متخصص لشركات الاستيراد والخدمات اللوجستية

يقوم هذا الموديول بإعادة تصميم الصفحة الرئيسية للموقع الإلكتروني في أودو
بتصميم احترافي مطابق لأفضل الممارسات العالمية (مستوحى من تصميم ATAWAH):

**الأقسام الرئيسية (7 أقسام):**
- هيدر ثابت (Sticky) مع قائمة تنقل وأزرار CTA
- قسم Hero مع 4 بطاقات معلومات عائمة ومائلة + حركات floating
- قسم Services Canvas قابل للسحب مع كروت متناثرة
- قسم Why Choose Us مع 3 نقاط أساسية
- قسم Our Process مع 4 خطوات منطقية
- **🌍 قسم Global Network Map** - خريطة عالمية تفاعلية مع خطوط منحنية
- قسم Blog & Knowledge Base مع تحميل المقالات تلقائياً
- قسم Call to Action مع نموذج استشارة
- فوتر احترافي

**الميزات التقنية:**
- موديلات ORM: shipping.service، shipping.process.step، shipping.blog.article
- كونترولر: تحميل المقالات من قاعدة البيانات
- JS: Drag & Drop للخدمات، عدادات متحركة، ظهور تدريجي، خطوط منحنية تفاعلية
- SCSS: متغيرات ألوان مركزية، responsive design تام
- جميع الأقسام مسجلة كـ Building Blocks قابلة للسحب على أي صفحة
- **خريطة SVG تفاعلية** مع خطوط منحنية (Bezier curves) وحركات سلسة
    """,
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'author': 'Logistics & Import Team',
    'website': 'https://yourshippingdomain.com',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'data/shipping_demo_data.xml',
        'data/website_menu_data.xml',
        'views/shipping_backend_views.xml',
        'views/snippets/s_shipping_hero.xml',
        'views/snippets/s_shipping_cards_carousel.xml',
        'views/snippets/s_shipping_services.xml',
        'views/snippets/s_shipping_why.xml',
        'views/snippets/s_shipping_process.xml',
        'views/snippets/s_shipping_network.xml',
        'views/snippets/s_shipping_blog.xml',
        'views/snippets/s_shipping_cta.xml',
        'views/snippets_registry.xml',
        'views/website_page_templates.xml',
        'views/missing_sections_complete.xml',
        'data/website_page_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'shipping_logistics_theme/static/src/scss/shipping_variables.scss',
            'shipping_logistics_theme/static/src/scss/shipping_theme.scss',
            'shipping_logistics_theme/static/src/js/shipping_theme.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}