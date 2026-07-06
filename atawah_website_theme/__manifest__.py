# -*- coding: utf-8 -*-
{
    'name': 'Atawah Website Theme',
    'summary': 'Custom homepage theme (ATAWAH design) for the Odoo Website builder',
    'description': """
Atawah Website Theme
=====================
يقوم هذا الموديول بإعادة تصميم الصفحة الرئيسية للموقع الإلكتروني في أودو
لتطابق تصميم موقع ATAWAH (Financial Consultancy & Auditing):

- هيدر ثابت (Sticky) مع قائمة تنقل وأزرار Sign in / Get a quote
- قسم Hero مع بطاقة عائمة (Dashboard mockup) وعدادات إحصائيات متحركة
- قسم الخدمات الست (Services) مُدار من قاعدة البيانات (موديل atawah.service)
- قسم About / Vision / Mission / 5 Pillars
- قسم اقتباس "Why Atawah"
- قسم About ATAWAH مع نقاط + بطاقات معلومات
- قسم Process بأربع خطوات مُدار من قاعدة البيانات (موديل atawah.process.step)
- قسم Insights (يعرض أحدث تدوينات المدونة تلقائيًا إن كان موديول website_blog مثبتًا)
- قسم Contact / CTA مع فورم تواصل
- فوتر مبسّط

كل الأقسام مسجّلة أيضًا كـ Building Blocks (Snippets) يمكن سحبها وإفلاتها
على أي صفحة أخرى من محرر الموقع.
    """,
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'author': 'Atawah',
    'website': 'https://atawah.ae',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'data/atawah_demo_data.xml',
        'data/website_menu_data.xml',
        'views/atawah_backend_views.xml',
        'views/snippets/s_atawah_hero.xml',
        'views/snippets/s_atawah_stats.xml',
        'views/snippets/s_atawah_services.xml',
        'views/snippets/s_atawah_about.xml',
        'views/snippets/s_atawah_why.xml',
        'views/snippets/s_atawah_details.xml',
        'views/snippets/s_atawah_process.xml',
        'views/snippets/s_atawah_insights.xml',
        'views/snippets/s_atawah_contact.xml',
        'views/snippets_registry.xml',
        'views/website_page_templates.xml',
        # يجب أن يبقى هذا الملف آخر عنصر لأنه يستدعي (t-call) كل القوالب أعلاه
        'data/website_page_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'atawah_website_theme/static/src/scss/atawah_variables.scss',
            'atawah_website_theme/static/src/scss/atawah_theme.scss',
            'atawah_website_theme/static/src/js/atawah_theme.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
