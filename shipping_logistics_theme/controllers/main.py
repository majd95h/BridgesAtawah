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

    @http.route("/shipping/contact/submit", auth="public", methods=["POST"], csrf=False, type="json")
    def contact_form_submit(self, **post):
        """
        Handle contact form submission
        Creates a lead/opportunity in Odoo CRM
        """
        try:
            # Extract form data
            name = post.get("name", "").strip()
            company = post.get("company", "").strip()
            email = post.get("email", "").strip()
            phone = post.get("phone", "").strip()
            subject = post.get("subject", "").strip()
            message = post.get("message", "").strip()

            # Validate required fields
            if not all([name, email, phone, message]):
                return {
                    "status": "error",
                    "message": "Missing required fields"
                }

            # Validate email format
            if not self._is_valid_email(email):
                return {
                    "status": "error",
                    "message": "Invalid email format"
                }

            # Map subject codes to descriptions
            subject_map = {
                "commercial_import": "Request for importing commercial goods",
                "production_lines": "Inquiry about production lines and industrial machines",
                "building_materials": "Securing building materials for real estate project",
                "logistics": "Logistics inquiry (shipping and customs clearance)",
                "partnership": "General inquiry or commercial partnership"
            }

            subject_description = subject_map.get(subject, subject)

            # Create lead/opportunity in CRM
            lead_data = {
                "name": f"Inquiry from {name}",
                "contact_name": name,
                "email_from": email,
                "phone": phone,
                "company_name": company or "Not provided",
                "description": f"""
                        Subject: {subject_description}

                        Message:
                        {message}

                        Contact Information:
                        - Name: {name}
                        - Company: {company or 'Not provided'}
                        - Email: {email}
                        - Phone: {phone}
                """,
                "type": "lead",  # Can be 'lead' or 'opportunity'
                "source_id": self._get_or_create_source(),  # Website contact form
                "date_open": fields.Datetime.now(),
            }

            # Create the lead
            Lead = request.env["crm.lead"].sudo()
            lead = Lead.create(lead_data)

            # Send confirmation email to the user
            self._send_confirmation_email(
                email=email,
                name=name,
                subject=subject_description
            )

            # Send notification to sales team
            self._send_notification_to_team(
                lead_id=lead.id,
                name=name,
                email=email
            )

            _logger.info(f"Contact form submitted: {lead.id} - {name}")

            return {
                "status": "success",
                "message": "Your inquiry has been received. We'll contact you shortly.",
                "lead_id": lead.id
            }

        except Exception as e:
            _logger.error(f"Error submitting contact form: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "An error occurred while processing your request. Please try again."
            }

    @staticmethod
    def _is_valid_email(email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _get_or_create_source(self):
        """Get or create 'Website Contact Form' source"""
        Source = request.env["utm.source"].sudo()
        source = Source.search([("name", "=", "Website Contact Form")], limit=1)
        if not source:
            source = Source.create({"name": "Website Contact Form"})
        return source.id

    def _send_confirmation_email(self, email, name, subject):
        """Send confirmation email to the user"""
        try:
            template = request.env.ref("shipping_logistics_theme.contact_confirmation_email", raise_if_not_found=False)
            if template:
                template.sudo().send_mail(
                    request.env["crm.lead"].sudo().search([("email_from", "=", email)], limit=1).id,
                    force_send=True
                )
            else:
                # Send basic email if template not found
                mail_values = {
                    "subject": f"We Received Your Inquiry - {subject}",
                    "body": f"""
                            Hi {name},

                            Thank you for reaching out to us. We have received your inquiry and will review it shortly.

                            Our team will get back to you within 24-48 hours.

                            Best regards,
                            Shipping & Logistics Team
                    """,
                    "email_to": email,
                }
                request.env["mail.mail"].sudo().create(mail_values).send()
        except Exception as e:
            _logger.warning(f"Failed to send confirmation email: {str(e)}")

    def _send_notification_to_team(self, lead_id, name, email):
        """Send notification to sales team"""
        try:
            # Get sales channel
            channel = request.env["mail.channel"].sudo().search(
                [("name", "=", "Sales"), ("channel_type", "=", "channel")],
                limit=1
            )

            if channel:
                message = f"""
                    🔔 New Contact Form Submission

                    Name: {name}
                    Email: {email}
                    Lead ID: {lead_id}

                    Click here to view the full inquiry details.
                """
                channel.message_post(
                    body=message,
                    message_type="notification",
                    subtype_id=request.env.ref("mail.mt_note").id
                )
        except Exception as e:
            _logger.warning(f"Failed to send team notification: {str(e)}")

    @http.route("/shipping/blog", auth="public", methods=["GET"], type="json")
    def get_blog_articles(self, limit=4):
        """
        Get blog articles for the blog section
        This endpoint integrates with your existing blog module
        """
        try:
            Blog = request.env["blog.post"].sudo()
            articles = Blog.search([], limit=limit, order="published_date desc")

            return {
                "status": "success",
                "articles": [
                    {
                        "id": article.id,
                        "title": article.name,
                        "excerpt": article.subtitle or article.name,
                        "author": article.author_id.name if article.author_id else "Admin",
                        "date": article.published_date.strftime("%Y-%m-%d") if article.published_date else "",
                        "url": f"/blog/{article.blog_id.slug}/{article.slug}",
                    }
                    for article in articles
                ]
            }
        except Exception as e:
            _logger.error(f"Error fetching blog articles: {str(e)}")
            return {
                "status": "error",
                "articles": []
            }


    