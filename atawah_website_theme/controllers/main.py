# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AtawahWebsite(http.Controller):
    """كونترولر بسيط يغذّي قسم 'Insights' في الصفحة الرئيسية.

    إن كان موديول website_blog مثبتًا يقوم بإرجاع أحدث 3 تدوينات منشورة،
    وإلا يرجّع قائمة فارغة فيبقى المحتوى الافتراضي (الثابت والقابل للتعديل
    من محرر الموقع) ظاهرًا كما هو دون كسر الصفحة.
    """

    @http.route(['/atawah/insights'], type='json', auth='public', website=True, csrf=False)
    def atawah_insights(self, limit=3, **kwargs):
        BlogPost = request.env.get('blog.post')
        if BlogPost is None:
            return {'posts': []}

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 3

        posts = BlogPost.sudo().search(
            [('is_published', '=', True)],
            limit=limit,
            order='post_date desc',
        )

        data = []
        for post in posts:
            data.append({
                'title': post.name,
                'subtitle': post.subtitle or '',
                'url': post.website_url,
                'date': post.post_date and post.post_date.strftime('%d %b %Y') or '',
            })
        return {'posts': data}
