/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

/**
 * يحرّك رقم عداد من 0 إلى target خلال duration ميلي ثانية.
 */
function animateAtawahCount(el, target, suffix, duration = 1400) {
    let startTime = null;

    function step(timestamp) {
        if (!startTime) {
            startTime = timestamp;
        }
        const progress = Math.min((timestamp - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const value = Math.round(eased * target);
        el.textContent = value + suffix;

        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            el.textContent = target + suffix;
        }
    }

    window.requestAnimationFrame(step);
}

function escapeAtawahHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}

// ==========================================================================
// الهيدر: تظليل عند التمرير + قائمة الموبايل
// ==========================================================================
publicWidget.registry.AtawahHeader = publicWidget.Widget.extend({
    selector: ".atawah_header",
    events: {
        "click .atawah_nav_toggle": "_onToggleNav",
        "click .atawah_nav a": "_onNavLinkClick",
    },

    start() {
        this._onScroll = this._onScroll.bind(this);
        window.addEventListener("scroll", this._onScroll, { passive: true });
        this._onScroll();
        return this._super(...arguments);
    },

    destroy() {
        window.removeEventListener("scroll", this._onScroll);
        this._super(...arguments);
    },

    _onScroll() {
        this.el.classList.toggle("atawah_header_scrolled", window.scrollY > 12);
    },

    _onToggleNav(ev) {
        const isOpen = this.el.classList.toggle("atawah_nav_open");
        ev.currentTarget.setAttribute("aria-expanded", isOpen ? "true" : "false");
    },

    _onNavLinkClick() {
        this.el.classList.remove("atawah_nav_open");
    },
});

// ==========================================================================
// عدادات الإحصائيات (Years of practice / Clients served / ...)
// ==========================================================================
publicWidget.registry.AtawahStats = publicWidget.Widget.extend({
    selector: ".s_atawah_stats",

    start() {
        this._played = false;

        this._observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting && !this._played) {
                    this._played = true;
                    this.el.querySelectorAll(".atawah_stat_number[data-count]").forEach((numberEl) => {
                        const target = parseInt(numberEl.dataset.count, 10) || 0;
                        const suffix = numberEl.dataset.suffix || "";
                        animateAtawahCount(numberEl, target, suffix);
                    });
                    this._observer.disconnect();
                }
            });
        }, { threshold: 0.3 });

        this._observer.observe(this.el);
        return this._super(...arguments);
    },

    destroy() {
        if (this._observer) {
            this._observer.disconnect();
        }
        this._super(...arguments);
    },
});

// ==========================================================================
// ظهور تدريجي للبطاقات عند التمرير (Services / Pillars / Insights / Process)
// ==========================================================================
publicWidget.registry.AtawahReveal = publicWidget.Widget.extend({
    selector: "#wrapwrap",

    start() {
        const items = this.el.querySelectorAll(
            ".atawah_service_card, .atawah_pillar_card, .atawah_insight_card, " +
            ".atawah_process_step, .atawah_info_card"
        );

        if (items.length) {
            items.forEach((item) => item.classList.add("atawah_reveal"));

            this._revealObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("atawah_in-view");
                        this._revealObserver.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.15 });

            items.forEach((item) => this._revealObserver.observe(item));
        }

        return this._super(...arguments);
    },

    destroy() {
        if (this._revealObserver) {
            this._revealObserver.disconnect();
        }
        this._super(...arguments);
    },
});

// ==========================================================================
// قسم Insights: يستبدل البطاقات الثابتة بأحدث تدوينات المدونة إن وُجدت
// ==========================================================================
publicWidget.registry.AtawahInsights = publicWidget.Widget.extend({
    selector: "#atawah_insights_grid",

    async start() {
        const _super = this._super(...arguments);
        try {
            const data = await rpc("/atawah/insights", { limit: 3 });
            const posts = (data && data.posts) || [];
            if (posts.length) {
                this.el.innerHTML = posts.map((post) => `
                    <a class="atawah_insight_card" href="${escapeAtawahHtml(post.url)}">
                        <span class="atawah_insight_tag">${escapeAtawahHtml(post.date || "Insight")}</span>
                        <h3>${escapeAtawahHtml(post.title)}</h3>
                        <p>${escapeAtawahHtml(post.subtitle)}</p>
                    </a>
                `).join("");
            }
        } catch (error) {
            // لا مشكلة: تبقى بطاقات المحتوى الثابت الافتراضية ظاهرة كما هي
        }
        return _super;
    },
});
