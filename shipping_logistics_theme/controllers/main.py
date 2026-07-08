# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class ShippingWebsite(http.Controller):
    @http.route(['/shipping/blog'], type='json', auth='public', website=True, csrf=False)
    def shipping_blog(self, limit=4, **kwargs):
        Article = request.env.get('shipping.blog.article')
        if Article is None:
            return {'articles': []}
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 4
        articles = Article.sudo().search(
            [('is_published', '=', True)],
            limit=limit,
            order='create_date desc',
        )
        data = []
        for article in articles:
            data.append({
                'title': article.name,
                'excerpt': article.excerpt or '',
                'url': '/blog/' + article.slug if hasattr(article, 'slug') else '#',
                'date': article.create_date and article.create_date.strftime('%d %b %Y') or '',
            })
        return {'articles': data}
