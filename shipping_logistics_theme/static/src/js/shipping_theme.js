/** @odoo-module **/
/**
 * ============================================================
 * SHIPPING & LOGISTICS THEME - COMPLETE WIDGET SUITE
 * ============================================================
 * 
 * Production-ready theme with all widgets:
 * - Navigation & Scroll Effects
 * - Carousels & Sliders
 * - Interactive Maps
 * - Forms & Validation
 * - Animations & Effects
 * 
 * Version: 1.0.0
 * Last Updated: 2024
 * ============================================================
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// ============================================================
// DEBUGGING & AUDIT TOOLS
// ============================================================

/**
 * Section ID Audit Tool
 * Run in console: window._sectionIdAudit()
 */
window._sectionIdAudit = function() {
    console.log("\n" + "=".repeat(70));
    console.log("🔍 SHIPPING THEME - SECTION ID AUDIT");
    console.log("=".repeat(70));
    
    // Expected IDs from navigation
    const navLinks = document.querySelectorAll(".shipping_nav_link, .shipping_dropdown_item");
    console.log("\n📍 EXPECTED IDs (from navigation):");
    const expectedIds = new Set();
    navLinks.forEach(link => {
        const href = link.getAttribute("href");
        if (href && href.startsWith("#")) {
            const id = href.substring(1);
            expectedIds.add(id);
            console.log(`  ✓ ${id}`);
        }
    });
    
    // Actual IDs in DOM
    console.log("\n✅ ACTUAL IDs in DOM:");
    const allElements = document.querySelectorAll("[id]");
    const actualIds = new Set();
    allElements.forEach(el => {
        if (el.id.includes("shipping") || el.id.startsWith("s_")) {
            actualIds.add(el.id);
            console.log(`  ✓ ${el.id} (${el.tagName})`);
        }
    });
    
    // Find mismatches
    console.log("\n❌ MISSING IDs (These need to be fixed!):");
    let hasMissing = false;
    expectedIds.forEach(id => {
        if (!actualIds.has(id)) {
            console.log(`  ⚠️  ${id} ← NOT FOUND`);
            hasMissing = true;
        }
    });
    if (!hasMissing) {
        console.log("  ✅ All expected IDs found! Navigation should work.");
    }
    
    console.log("\n" + "=".repeat(70));
};

// Run audit on page load
window.addEventListener("load", () => {
    setTimeout(() => window._sectionIdAudit(), 1000);
});

// ============================================================
// 1. HERO BACKGROUND CAROUSEL
// ============================================================
publicWidget.registry.ShippingHeroBgCarousel = publicWidget.Widget.extend({
    selector: ".shipping_hero_bg_carousel",

    init() {
        this._super(...arguments);
        this.currentIndex = 0;
        this.interval = 5000; // change image every 5 seconds
        this.timer = null;
    },

    start() {
        this.slides = this.el.querySelectorAll(".shipping_hero_bg_slide");
        if (this.slides.length > 0) {
            this._showSlide(0);
            this._startTimer();
        }
        return this._super(...arguments);
    },

    destroy() {
        clearInterval(this.timer);
        this._super(...arguments);
    },

    _showSlide(index) {
        // Remove 'active' from all slides
        this.slides.forEach(slide => slide.classList.remove("active"));
        // Add to the target slide
        this.slides[index].classList.add("active");
    },

    _startTimer() {
        this.timer = setInterval(() => {
            this.currentIndex = (this.currentIndex + 1) % this.slides.length;
            this._showSlide(this.currentIndex);
        }, this.interval);
    },
});

// ============================================================
// 2. SHIPPING NETWORK MAP (AMCHARTS)
// ============================================================
publicWidget.registry.ShippingNetworkMap = publicWidget.Widget.extend({
    selector: "#shipping_routes_map",

    start() {
        this._renderAmChart();
        return this._super(...arguments);
    },

    _renderAmChart() {
        try {
            // 1. Initialize amCharts Root
            let root = am5.Root.new(this.el);

            // Set animated theme with custom colors
            root.setThemes([am5themes_Animated.new(root)]);

            // 2. Create the Map Chart with enhanced settings
            let chart = root.container.children.push(am5map.MapChart.new(root, {
                panX: "none",
                panY: "none",
                wheelX: "none",
                wheelY: "none",
                projection: am5map.geoMercator(),
                homeGeoPoint: { longitude: 85, latitude: 28 },
                homeZoomLevel: 1.6
            }));

            // 3. Add the Asia Map (Polygons) with enhanced styling
            let polygonSeries = chart.series.push(am5map.MapPolygonSeries.new(root, {
                geoJSON: am5geodata_region_world_asiaLow
            }));

            // Enhanced polygon styling
            polygonSeries.mapPolygons.template.setAll({
                fill: am5.color(0xe8e8e8),
                stroke: am5.color(0xffffff),
                strokeWidth: 1.5,
                strokeOpacity: 0.8
            });

            // List of country ISO codes to highlight
            const highlightedCountries = ["CN", "SA", "AE", "QA", "KW", "BH", "OM"];

            // Apply gold fill to highlighted countries
            polygonSeries.mapPolygons.template.adapters.add("fill", function(fill, target) {
                if (target.dataItem && target.dataItem.dataContext) {
                    const id = target.dataItem.dataContext.id;
                    if (highlightedCountries.includes(id)) {
                        return am5.color(0xD4AF37);   // gold
                    }
                }
                return fill;
            });

            // Add subtle hover effect to countries
            polygonSeries.mapPolygons.template.set("tooltipText", "{name}");
            polygonSeries.mapPolygons.template.adapters.add("strokeOpacity", function(opacity, target) {
                if (target.isHover || target.isActive) {
                    return 1;
                }
                return 0.8;
            });

            // 4. Define the Cities (Origin and Destinations)
            const origin = { 
                id: "cn", 
                title: "Central China", 
                subtitle: "Distribution Hub",
                geometry: { type: "Point", coordinates: [104.0, 36.0] },
                color: 0xD4AF37 
            };
            
            const destinations = [
                { id: "sa", title: "Saudi Arabia", subtitle: "Riyadh", geometry: { type: "Point", coordinates: [45.0792, 23.8859] }, color: 0xD4AF37 },
                { id: "ae", title: "UAE", subtitle: "Dubai", geometry: { type: "Point", coordinates: [54.3666, 24.4667] }, color: 0xD4AF37 },
                { id: "qa", title: "Qatar", subtitle: "Doha", geometry: { type: "Point", coordinates: [51.5310, 25.2854] }, color: 0xD4AF37 },
                { id: "kw", title: "Kuwait", subtitle: "Kuwait City", geometry: { type: "Point", coordinates: [47.9774, 29.3759] }, color: 0xD4AF37 },
                { id: "bh", title: "Bahrain", subtitle: "Manama", geometry: { type: "Point", coordinates: [50.5860, 26.2285] }, color: 0xD4AF37 },
                { id: "om", title: "Oman", subtitle: "Muscat", geometry: { type: "Point", coordinates: [58.4059, 23.5859] }, color: 0xD4AF37 }
            ];

            // 5. Add Points (Cities) to the Map with Enhanced Animation
            let pointSeries = chart.series.push(am5map.MapPointSeries.new(root, {}));
            
            pointSeries.bullets.push(function(root, series, dataItem) {
                let container = am5.Container.new(root, {});
                
                // Main solid circle (smaller)
                let mainCircle = container.children.push(am5.Circle.new(root, {
                    radius: 8,
                    fill: am5.color(dataItem.dataContext.color),
                    strokeWidth: 2,
                    stroke: am5.color(0xffffff)
                }));

                // Glow layers (multiple circles with opacity decay)
                for (let i = 0; i < 3; i++) {
                    let glowCircle = container.children.push(am5.Circle.new(root, {
                        radius: 8,
                        fill: am5.color(dataItem.dataContext.color),
                        opacity: 0.3 - (i * 0.1)
                    }));
                    
                    glowCircle.animate({
                        key: "radius",
                        to: 20 + (i * 6),
                        duration: 1500 + (i * 300),
                        easing: am5.ease.out(am5.ease.cubic),
                        loops: Infinity
                    });
                }

                // Pulsing animation on main circle
                mainCircle.animate({
                    key: "opacity",
                    from: 1,
                    to: 0.7,
                    duration: 1000,
                    easing: am5.ease.inOut(am5.ease.sine),
                    loops: Infinity
                });

                return am5.Bullet.new(root, {
                    sprite: container,
                    tooltipText: "{title}"
                });
            });

            pointSeries.data.push(origin);
            destinations.forEach(dest => pointSeries.data.push(dest));

            // 6. Draw the Lines with Enhanced Styling
            let lineSeries = chart.series.push(am5map.MapLineSeries.new(root, {}));
            
            lineSeries.mapLines.template.setAll({
                strokeWidth: 3,
                strokeOpacity: 0.7,
                strokeDasharray: [5, 5],
                strokeLinecap: "round"
            });

            destinations.forEach((dest, index) => {
                lineSeries.data.push({
                    geometry: {
                        type: "LineString",
                        coordinates: [
                            origin.geometry.coordinates,
                            dest.geometry.coordinates
                        ]
                    },
                    stroke: am5.color(dest.color),
                    dataContext: { index: index }
                });
            });

            // Add subtle shadows to lines
            lineSeries.mapLines.template.set("tooltipText", "Trade Route");

            // 7. Auto-zoom to show all data
            polygonSeries.events.on("datavalidated", function () {
                chart.goHome();
            });

            // Add entrance animation
            chart.appear(1000, 100);
            
        } catch (error) {
            console.error("❌ AmCharts map initialization error:", error);
        }
    }
});

// ============================================================
// 3. COVERFLOW TESTIMONIALS
// ============================================================
publicWidget.registry.ShippingCoverflow = publicWidget.Widget.extend({
    selector: ".shipping_coverflow_wrapper",
    events: {
        "click .btn_next": "_onNextClick",
        "click .btn_prev": "_onPrevClick",
        "click .shipping_coverflow_card": "_onCardClick",
        "mouseenter .shipping_coverflow_deck": "_pauseAutoPlay",
        "mouseleave .shipping_coverflow_deck": "_startAutoPlay",
    },

    init() {
        this._super(...arguments);
        this.currentIndex = 0;
        this.autoPlayInterval = null;
        this.delay = 5000;
    },

    start() {
        this.cards = Array.from(this.el.querySelectorAll(".shipping_coverflow_card"));
        if (this.cards.length > 0) {
            this._updateCoverflow();
            this._startAutoPlay();
        }
        return this._super(...arguments);
    },

    destroy() {
        this._pauseAutoPlay();
        this._super(...arguments);
    },

    _updateCoverflow() {
        const total = this.cards.length;
        
        this.cards.forEach((card, index) => {
            let offset = index - this.currentIndex;
            
            if (offset > Math.floor(total / 2)) {
                offset -= total;
            } else if (offset < -Math.floor(total / 2)) {
                offset += total;
            }

            if (Math.abs(offset) > 2) {
                card.dataset.pos = "hidden";
            } else {
                card.dataset.pos = offset;
            }
        });
    },

    _onNextClick() {
        this.currentIndex = (this.currentIndex + 1) % this.cards.length;
        this._updateCoverflow();
    },

    _onPrevClick() {
        this.currentIndex = (this.currentIndex - 1 + this.cards.length) % this.cards.length;
        this._updateCoverflow();
    },

    _onCardClick(ev) {
        const clickedPos = parseInt(ev.currentTarget.dataset.pos);
        if (clickedPos === 0 || isNaN(clickedPos)) return;

        this.currentIndex = (this.currentIndex + clickedPos + this.cards.length) % this.cards.length;
        this._updateCoverflow();
    },

    _startAutoPlay() {
        this._pauseAutoPlay();
        this.autoPlayInterval = setInterval(() => {
            this._onNextClick();
        }, this.delay);
    },

    _pauseAutoPlay() {
        if (this.autoPlayInterval) {
            clearInterval(this.autoPlayInterval);
            this.autoPlayInterval = null;
        }
    }
});

// ============================================================
// 4. NETWORK INTERACTIVE HOVER EFFECTS
// ============================================================
publicWidget.registry.ShippingNetworkInteractive = publicWidget.Widget.extend({
    selector: ".shipping_world_map",
    events: {
        "mouseover .shipping_location": "_onLocationHover",
        "mouseout .shipping_location": "_onLocationOut",
    },

    _onLocationHover(ev) {
        const circle = ev.currentTarget.querySelector("circle:first-of-type");
        if (circle) {
            circle.style.transition = "r 0.3s ease";
            const currentR = parseFloat(circle.getAttribute("r"));
            circle.setAttribute("r", currentR * 1.3);
        }
    },

    _onLocationOut(ev) {
        const circle = ev.currentTarget.querySelector("circle:first-of-type");
        if (circle) {
            const currentR = parseFloat(circle.getAttribute("r"));
            circle.setAttribute("r", currentR / 1.3);
        }
    },
});

// ============================================================
// 5. DRAG & DROP SERVICE CARDS
// ============================================================
publicWidget.registry.ShippingDragDrop = publicWidget.Widget.extend({
    selector: ".shipping_services_scatter",
    events: {
        "mousedown .shipping_drag_card": "_onMouseDown",
        "touchstart .shipping_drag_card": "_onTouchStart",
    },

    start() {
        this._dragging = null;
        this._onMouseMove = this._onMouseMove.bind(this);
        this._onMouseUp = this._onMouseUp.bind(this);
        this._onTouchMove = this._onTouchMove.bind(this);
        this._onTouchEnd = this._onTouchEnd.bind(this);
        
        document.addEventListener("mousemove", this._onMouseMove);
        document.addEventListener("mouseup", this._onMouseUp);
        document.addEventListener("touchmove", this._onTouchMove, {passive: false});
        document.addEventListener("touchend", this._onTouchEnd);
        return this._super(...arguments);
    },

    destroy() {
        document.removeEventListener("mousemove", this._onMouseMove);
        document.removeEventListener("mouseup", this._onMouseUp);
        document.removeEventListener("touchmove", this._onTouchMove);
        document.removeEventListener("touchend", this._onTouchEnd);
        this._super(...arguments);
    },

    _onMouseDown(ev) {
        this._startDrag(ev.currentTarget, ev.clientX, ev.clientY);
    },

    _onTouchStart(ev) {
        const touch = ev.touches[0];
        this._startDrag(ev.currentTarget, touch.clientX, touch.clientY);
    },

    _startDrag(card, x, y) {
        this._dragging = {
            card: card,
            startX: x,
            startY: y,
            offsetX: x - card.getBoundingClientRect().left,
            offsetY: y - card.getBoundingClientRect().top,
        };
        card.classList.add("shipping_dragging");
    },

    _onMouseMove(ev) {
        if (this._dragging) {
            this._drag(ev.clientX, ev.clientY);
        }
    },

    _onTouchMove(ev) {
        if (this._dragging) {
            const touch = ev.touches[0];
            this._drag(touch.clientX, touch.clientY);
            ev.preventDefault();
        }
    },

    _drag(x, y) {
        const card = this._dragging.card;
        const newX = x - this._dragging.offsetX;
        const newY = y - this._dragging.offsetY;
        card.style.left = newX + "px";
        card.style.top = newY + "px";
        card.style.position = "absolute";
    },

    _onMouseUp() {
        if (this._dragging) {
            this._dragging.card.classList.remove("shipping_dragging");
            this._dragging = null;
        }
    },

    _onTouchEnd() {
        if (this._dragging) {
            this._dragging.card.classList.remove("shipping_dragging");
            this._dragging = null;
        }
    },
});

// ============================================================
// 6. BLOG ARTICLES LOADER
// ============================================================
publicWidget.registry.ShippingBlog = publicWidget.Widget.extend({
    selector: "#shipping_blog_grid",
    async start() {
        const _super = this._super(...arguments);
        try {
            const data = await rpc("/shipping/blog", { limit: 4 });
            const articles = (data && data.articles) || [];
            if (articles.length) {
                const backs = this.el.querySelectorAll('.shipping_blog_back');
                articles.forEach((article, index) => {
                    if (backs[index]) {
                        backs[index].innerHTML = `
                            <h3>${this._escape(article.title)}</h3>
                            <p>${this._escape(article.excerpt)}</p>
                        `;
                    }
                });
            }
        } catch (error) {
            console.log("Blog loading failed, static cards remain as fallback");
        }
        return _super;
    },

    _escape(text) {
        const div = document.createElement("div");
        div.textContent = text || "";
        return div.innerHTML;
    },
});

// ============================================================
// 7. FOOTER CONTACT FORM
// ============================================================
publicWidget.registry.ShippingFooterContact = publicWidget.Widget.extend({
    selector: ".s_shipping_footer_contact",
    events: {
        "submit #shipping_contact_form": "_onFormSubmit",
        "click .chat_channel_btn": "_onChatClick",
        "focus .form_input, .form_select, .form_textarea": "_onFormFieldFocus",
        "blur .form_input, .form_select, .form_textarea": "_onFormFieldBlur",
    },

    start() {
        this._initializeAnimations();
        this._setupFormValidation();
        return this._super(...arguments);
    },

    _initializeAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: "0px 0px -50px 0px"
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = "slideUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards";
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        this.el.querySelectorAll(".shipping_office_card, .email_channel_card, .chat_channel_btn").forEach(card => {
            observer.observe(card);
        });
    },

    _setupFormValidation() {
        this.form = this.el.querySelector("#shipping_contact_form");
        if (this.form) {
            this.form.noValidate = true;
        }
    },

    async _onFormSubmit(ev) {
        ev.preventDefault();

        if (!this._validateForm()) {
            return;
        }

        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData);

        const submitBtn = this.form.querySelector(".form_submit_btn");
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";

        try {
            const result = await rpc("/shipping/contact/submit", {
                name: data.name,
                company: data.company,
                email: data.email,
                phone: data.phone,
                subject: data.subject,
                message: data.message,
            });

            if (result.status === "success") {
                this._showSuccessMessage();
                this.form.reset();
            } else {
                this._showErrorMessage("Failed to send inquiry. Please try again.");
            }
        } catch (error) {
            console.error("Form submission error:", error);
            this._showErrorMessage("An error occurred. Please try again later.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    },

    _validateForm() {
        const form = this.form;
        const fields = form.querySelectorAll("[required]");
        let isValid = true;

        fields.forEach(field => {
            if (!field.value.trim()) {
                this._showFieldError(field, `${field.previousElementSibling.textContent} is required`);
                isValid = false;
            } else if (field.type === "email" && !this._isValidEmail(field.value)) {
                this._showFieldError(field, "Please enter a valid email address");
                isValid = false;
            } else if (field.type === "tel" && !this._isValidPhone(field.value)) {
                this._showFieldError(field, "Please enter a valid phone number");
                isValid = false;
            } else {
                this._clearFieldError(field);
            }
        });

        const privacyCheckbox = form.querySelector("#contact_privacy");
        if (privacyCheckbox && !privacyCheckbox.checked) {
            this._showFieldError(privacyCheckbox, "You must agree to the privacy policy");
            isValid = false;
        }

        return isValid;
    },

    _showFieldError(field, message) {
        this._clearFieldError(field);
        
        const errorDiv = document.createElement("div");
        errorDiv.className = "form_error";
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            color: #e74c3c;
            font-size: 0.85rem;
            margin-top: 0.4rem;
            display: block;
        `;

        field.parentNode.insertBefore(errorDiv, field.nextSibling);
        field.style.borderColor = "#e74c3c";
        field.style.boxShadow = "0 0 0 3px rgba(231, 76, 60, 0.1)";
    },

    _clearFieldError(field) {
        const errorDiv = field.parentNode.querySelector(".form_error");
        if (errorDiv) {
            errorDiv.remove();
        }
        field.style.borderColor = "";
        field.style.boxShadow = "";
    },

    _isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    _isValidPhone(phone) {
        const phoneRegex = /^[+\d\s\-()]+$/;
        return phoneRegex.test(phone) && phone.replace(/\D/g, "").length >= 7;
    },

    _showSuccessMessage() {
        const toast = document.createElement("div");
        toast.className = "shipping_toast shipping_toast_success";
        toast.innerHTML = `
            <div class="toast_icon">✓</div>
            <div class="toast_content">
                <div class="toast_title">Inquiry Sent Successfully!</div>
                <div class="toast_message">We'll get back to you within 24-48 hours.</div>
            </div>
        `;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            gap: 1rem;
            align-items: center;
            max-width: 400px;
            z-index: 9999;
            animation: slideUpToast 0.4s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "slideDownToast 0.4s ease-out forwards";
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    },

    _showErrorMessage(message) {
        const toast = document.createElement("div");
        toast.className = "shipping_toast shipping_toast_error";
        toast.innerHTML = `
            <div class="toast_icon">!</div>
            <div class="toast_content">
                <div class="toast_title">Error</div>
                <div class="toast_message">${message}</div>
            </div>
        `;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            gap: 1rem;
            align-items: center;
            max-width: 400px;
            z-index: 9999;
            animation: slideUpToast 0.4s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "slideDownToast 0.4s ease-out forwards";
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    },

    _onChatClick(ev) {
        const btn = ev.currentTarget;
        
        btn.style.transform = "scale(0.98)";
        setTimeout(() => {
            btn.style.transform = "";
        }, 100);

        if (btn.classList.contains("wechat")) {
            const wechatId = btn.dataset.wechatId;
            this._showWeChatInfo(wechatId);
            ev.preventDefault();
        }
    },

    _showWeChatInfo(wechatId) {
        const modal = document.createElement("div");
        modal.className = "shipping_wechat_modal";
        modal.innerHTML = `
            <div class="modal_overlay"></div>
            <div class="modal_content">
                <button class="modal_close">&times;</button>
                <h3>Connect on WeChat</h3>
                <p>Scan the QR code below or search for our WeChat ID:</p>
                <div class="wechat_id_box">${wechatId}</div>
                <p style="font-size: 0.85rem; color: #666; margin-top: 1rem;">
                    WeChat is primarily used for coordination with our industrial clients and our China office.
                </p>
            </div>
        `;

        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease-out;
        `;

        const overlay = modal.querySelector(".modal_overlay");
        overlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
        `;

        const content = modal.querySelector(".modal_content");
        content.style.cssText = `
            position: relative;
            background: white;
            border-radius: 12px;
            padding: 2.5rem;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            z-index: 2;
            text-align: center;
            animation: slideUp 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
        `;

        const closeBtn = modal.querySelector(".modal_close");
        closeBtn.style.cssText = `
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: none;
            border: none;
            font-size: 2rem;
            cursor: pointer;
            color: #999;
            padding: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.2s ease;
        `;

        closeBtn.onmouseover = () => closeBtn.style.color = "#1a1a1a";
        closeBtn.onmouseout = () => closeBtn.style.color = "#999";

        const wechatIdBox = modal.querySelector(".wechat_id_box");
        wechatIdBox.style.cssText = `
            background: linear-gradient(135deg, #09B83E 0%, #08A030 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            font-size: 1.2rem;
            font-weight: 700;
            margin: 1.5rem 0;
            font-family: monospace;
        `;

        closeBtn.onclick = () => modal.remove();
        overlay.onclick = () => modal.remove();

        document.body.appendChild(modal);
    },

    _onFormFieldFocus(ev) {
        const field = ev.currentTarget;
        field.style.background = "#fffbf5";
    },

    _onFormFieldBlur(ev) {
        const field = ev.currentTarget;
        if (!field.value.trim()) {
            field.style.background = "#fff";
        }
    }
});

// ============================================================
// 8. SERVICES DETAIL TABS
// ============================================================
publicWidget.registry.ShippingServicesDetailTabs = publicWidget.Widget.extend({
    selector: ".s_shipping_services_detail",
    events: {
        "click .shipping_tab_btn": "_onTabClick",
    },

    start() {
        this.tabs = this.el.querySelectorAll(".shipping_tab_btn");
        this.panes = this.el.querySelectorAll(".shipping_tab_pane");
        
        if (this.tabs.length > 0) {
            this.tabs[0].classList.add("active");
            const firstPane = this.el.querySelector(`.shipping_tab_pane[data-pane="0"]`);
            if (firstPane) {
                firstPane.classList.add("active");
            }
        }
        
        return this._super(...arguments);
    },

    _onTabClick(ev) {
        const btn = ev.currentTarget;
        const tabIndex = btn.dataset.tab;
        
        this.tabs.forEach(tab => tab.classList.remove("active"));
        this.panes.forEach(pane => pane.classList.remove("active"));
        
        btn.classList.add("active");
        const pane = this.el.querySelector(`.shipping_tab_pane[data-pane="${tabIndex}"]`);
        if (pane) {
            pane.classList.add("active");
        }
    },
});

// ============================================================
// 9. IMPORT REQUEST FORM
// ============================================================
publicWidget.registry.ShippingImportForm = publicWidget.Widget.extend({
    selector: ".s_shipping_import_form",
    events: {
        "submit #shipping_import_form": "_onFormSubmit",
        "focus .form_input, .form_select, .form_textarea": "_onFormFieldFocus",
        "blur .form_input, .form_select, .form_textarea": "_onFormFieldBlur",
        "change [name='category']": "_onCategoryChange",
    },

    start() {
        this.form = this.el.querySelector("#shipping_import_form");
        this._setupFormValidation();
        return this._super(...arguments);
    },

    _setupFormValidation() {
        if (this.form) {
            this.form.noValidate = true;
        }
    },

    async _onFormSubmit(ev) {
        ev.preventDefault();

        if (!this._validateForm()) {
            this._scrollToError();
            return;
        }

        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData);

        const submitBtn = this.form.querySelector(".form_submit_btn");
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting...";

        try {
            const result = await rpc("/shipping/import/submit", {
                name: data.name,
                company: data.company,
                email: data.email,
                phone: data.phone,
                country: data.country,
                category: data.category,
                product_name: data.product_name,
                specifications: data.specifications,
                quantity: data.quantity,
                budget: data.budget,
                currency: data.currency,
                custom_branding: data.custom_branding,
                shipping_method: data.shipping_method,
                customs_help: data.customs_help,
                import_license: data.import_license,
            });

            if (result.status === "success") {
                this._showSuccessMessage();
                this.form.reset();
                
                setTimeout(() => {
                    window.scrollTo({ top: 0, behavior: "smooth" });
                }, 500);
            } else {
                this._showErrorMessage(result.message || "Failed to submit request. Please try again.");
            }
        } catch (error) {
            console.error("Form submission error:", error);
            this._showErrorMessage("An error occurred. Please try again later.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    },

    _validateForm() {
        const form = this.form;
        const fields = form.querySelectorAll("[required]");
        let isValid = true;

        fields.forEach(field => {
            if (!field.value.trim()) {
                const label = field.previousElementSibling?.textContent || field.name;
                this._showFieldError(field, `${label} is required`);
                isValid = false;
            } else if (field.type === "email" && !this._isValidEmail(field.value)) {
                this._showFieldError(field, "Please enter a valid email address");
                isValid = false;
            } else if (field.type === "tel" && !this._isValidPhone(field.value)) {
                this._showFieldError(field, "Please enter a valid phone number");
                isValid = false;
            } else {
                this._clearFieldError(field);
            }
        });

        const privacyCheckbox = form.querySelector("[name='privacy_consent']");
        if (privacyCheckbox && !privacyCheckbox.checked) {
            this._showFieldError(privacyCheckbox, "You must agree to the privacy policy");
            isValid = false;
        }

        return isValid;
    },

    _showFieldError(field, message) {
        this._clearFieldError(field);
        
        const errorDiv = document.createElement("div");
        errorDiv.className = "form_error";
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            color: #e74c3c;
            font-size: 0.8rem;
            margin-top: 0.3rem;
            display: block;
        `;

        field.parentNode.appendChild(errorDiv);
        field.style.borderColor = "#e74c3c";
        field.style.boxShadow = "0 0 0 3px rgba(231, 76, 60, 0.1)";
    },

    _clearFieldError(field) {
        const errorDiv = field.parentNode.querySelector(".form_error");
        if (errorDiv) {
            errorDiv.remove();
        }
        field.style.borderColor = "";
        field.style.boxShadow = "";
    },

    _isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    _isValidPhone(phone) {
        const phoneRegex = /^[+\d\s\-()]+$/;
        return phoneRegex.test(phone) && phone.replace(/\D/g, "").length >= 7;
    },

    _showSuccessMessage() {
        const toast = document.createElement("div");
        toast.className = "shipping_toast shipping_toast_success";
        toast.innerHTML = `
            <div class="toast_icon">✓</div>
            <div class="toast_content">
                <div class="toast_title">Request Submitted Successfully!</div>
                <div class="toast_message">We'll review your request and contact you within 24-48 hours.</div>
            </div>
        `;
        toast.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            gap: 1rem;
            align-items: center;
            max-width: 400px;
            z-index: 9999;
            animation: slideUpToast 0.4s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "slideDownToast 0.4s ease-out forwards";
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    },

    _showErrorMessage(message) {
        const toast = document.createElement("div");
        toast.className = "shipping_toast shipping_toast_error";
        toast.innerHTML = `
            <div class="toast_icon">!</div>
            <div class="toast_content">
                <div class="toast_title">Error</div>
                <div class="toast_message">${message}</div>
            </div>
        `;
        toast.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            gap: 1rem;
            align-items: center;
            max-width: 400px;
            z-index: 9999;
            animation: slideUpToast 0.4s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "slideDownToast 0.4s ease-out forwards";
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    },

    _scrollToError() {
        const errorField = this.form.querySelector(".form_error")?.previousElementSibling;
        if (errorField) {
            errorField.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    },

    _onFormFieldFocus(ev) {
        const field = ev.currentTarget;
        field.style.background = "#fffbf5";
    },

    _onFormFieldBlur(ev) {
        const field = ev.currentTarget;
        if (!field.value.trim()) {
            field.style.background = "white";
        }
    },

    _onCategoryChange(ev) {
        const category = ev.currentTarget.value;
        const productNameField = this.form.querySelector("[name='product_name']");
        
        const placeholders = {
            machinery: "e.g., CNC Drilling Machine, 5-axis Processing Center, etc.",
            construction: "e.g., Ceramic Tiles 60x60cm, Marble Slabs, Bathroom Fixtures, etc.",
            furniture: "e.g., Office Desk, LED Ceiling Lights, Hotel Chair Set, etc.",
            wholesale: "e.g., USB Cables (1000 units), T-Shirt Wholesale (500 pieces), etc.",
            partial: "e.g., Combination of small orders from multiple suppliers",
        };
        
        if (productNameField) {
            productNameField.placeholder = placeholders[category] || "Enter product name...";
        }
    },
});

// ============================================================
// 10. BLOG NEWSLETTER SIGNUP
// ============================================================
publicWidget.registry.ShippingBlogNewsletter = publicWidget.Widget.extend({
    selector: ".s_shipping_blog_articles",
    events: {
        "submit .newsletter_form": "_onNewsletterSubmit",
    },

    async _onNewsletterSubmit(ev) {
        ev.preventDefault();

        const form = ev.currentTarget;
        const email = form.querySelector("[type='email']").value;
        const submitBtn = form.querySelector("[type='submit']");

        if (!this._isValidEmail(email)) {
            this._showErrorMessage("Please enter a valid email address");
            return;
        }

        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = "Subscribing...";

        try {
            const result = await rpc("/shipping/newsletter/subscribe", {
                email: email,
            });

            if (result.status === "success") {
                this._showSuccessMessage("Successfully subscribed to our newsletter!");
                form.reset();
            } else {
                this._showErrorMessage(result.message || "Subscription failed. Please try again.");
            }
        } catch (error) {
            console.error("Newsletter subscription error:", error);
            this._showErrorMessage("An error occurred. Please try again later.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    },

    _isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    _showSuccessMessage(message) {
        const toast = document.createElement("div");
        toast.innerHTML = `
            <div class="toast_icon">✓</div>
            <div class="toast_content">
                <div class="toast_message">${message}</div>
            </div>
        `;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            gap: 1rem;
            align-items: center;
            z-index: 9999;
            animation: slideUpToast 0.4s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "slideDownToast 0.4s ease-out forwards";
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    },

    _showErrorMessage(message) {
        const toast = document.createElement("div");
        toast.innerHTML = `
            <div class="toast_icon">!</div>
            <div class="toast_content">
                <div class="toast_message">${message}</div>
            </div>
        `;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            gap: 1rem;
            align-items: center;
            z-index: 9999;
            animation: slideUpToast 0.4s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "slideDownToast 0.4s ease-out forwards";
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    },
});

// ============================================================
// 11. SMOOTH SCROLL NAVIGATION (UNIFIED - NO DUPLICATES)
// ============================================================
publicWidget.registry.ShippingSmoothScrollNavigation = publicWidget.Widget.extend({
    selector: "a[href*='#']",
    events: {
        "click": "_onLinkClick",
    },

    _onLinkClick(ev) {
        const href = ev.currentTarget.getAttribute("href");
        
        if (href && href.startsWith("#")) {
            const targetId = href.substring(1);
            const target = document.getElementById(targetId);
            
            if (target) {
                ev.preventDefault();
                
                console.log("🔗 Link clicked:", href);
                console.log("✅ Target element found:", target.tagName);
                
                // Update URL
                window.history.pushState(null, null, href);
                
                // Close dropdowns
                this._closeDropdowns();
                
                // Scroll to target
                this._scrollToTarget(target);
            } else {
                console.warn("❌ Target element NOT FOUND for ID:", targetId);
                window._sectionIdAudit();
            }
        }
    },

    _scrollToTarget(target) {
        setTimeout(() => {
            try {
                const headerHeight = document.querySelector(".shipping_header")?.offsetHeight || 0;
                const elementTop = target.getBoundingClientRect().top + window.pageYOffset;
                const scrollPosition = elementTop - headerHeight - 20;
                
                window.scrollTo({
                    top: scrollPosition,
                    behavior: 'smooth'
                });
                
                console.log("✅ Scrolling to:", target.id, "at position:", scrollPosition);
            } catch (error) {
                console.error("Scroll error:", error);
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    },

    _closeDropdowns() {
        const dropdowns = document.querySelectorAll(".shipping_nav_dropdown");
        dropdowns.forEach(dropdown => {
            dropdown.style.opacity = "0";
            dropdown.style.visibility = "hidden";
        });
    }
});

// ============================================================
// 12. ACTIVE LINK DETECTOR
// ============================================================
publicWidget.registry.ShippingActiveLinkDetector = publicWidget.Widget.extend({
    selector: ".shipping_nav",
    
    init() {
        this._super(...arguments);
        this._onScroll = this._onScroll.bind(this);
        this.scrollTimeout = null;
    },

    start() {
        window.addEventListener("scroll", this._onScroll, { passive: true });
        this._updateActiveLink();
        return this._super(...arguments);
    },

    destroy() {
        window.removeEventListener("scroll", this._onScroll);
        if (this.scrollTimeout) clearTimeout(this.scrollTimeout);
        this._super(...arguments);
    },

    _onScroll() {
        if (this.scrollTimeout) clearTimeout(this.scrollTimeout);
        this.scrollTimeout = setTimeout(() => {
            this._updateActiveLink();
        }, 50);
    },

    _updateActiveLink() {
        const navLinks = this.el.querySelectorAll("a[href^='#']");
        const sections = document.querySelectorAll("[id^='s_shipping_']");
        
        let activeId = null;
        const headerHeight = document.querySelector(".shipping_header")?.offsetHeight || 80;
        
        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            if (rect.top <= headerHeight + 150 && rect.bottom > 0) {
                activeId = section.id;
            }
        });

        navLinks.forEach(link => {
            const href = link.getAttribute("href");
            const targetId = href?.substring(1);
            
            link.classList.remove("active");
            
            if (targetId === activeId) {
                link.classList.add("active");
                
                const navGroup = link.closest(".shipping_nav_group");
                if (navGroup) {
                    const parentLink = navGroup.querySelector(".shipping_nav_link");
                    if (parentLink) {
                        parentLink.classList.add("active");
                    }
                }
            }
        });
    }
});

// ============================================================
// 13. HEADER SCROLL EFFECT
// ============================================================
publicWidget.registry.ShippingHeaderScroll = publicWidget.Widget.extend({
    selector: ".shipping_header",
    events: {},

    start() {
        this._onScroll = this._onScroll.bind(this);
        window.addEventListener("scroll", this._onScroll, { passive: true });
        return this._super(...arguments);
    },

    destroy() {
        window.removeEventListener("scroll", this._onScroll);
        this._super(...arguments);
    },

    _onScroll() {
        const header = this.el;
        if (window.scrollY > 20) {
            header.classList.add("header_scrolled");
        } else {
            header.classList.remove("header_scrolled");
        }
    }
});

// ============================================================
// 14. DROPDOWN ACCESSIBILITY
// ============================================================
publicWidget.registry.ShippingDropdownA11y = publicWidget.Widget.extend({
    selector: ".shipping_nav_group",
    events: {
        "keydown .shipping_nav_link": "_onKeyDown",
        "keydown .shipping_dropdown_item": "_onDropdownKeyDown",
    },

    _onKeyDown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            const dropdown = this.el.querySelector(".shipping_nav_dropdown");
            if (dropdown) {
                ev.preventDefault();
                const firstItem = dropdown.querySelector(".shipping_dropdown_item");
                if (firstItem) {
                    firstItem.focus();
                }
            }
        }
    },

    _onDropdownKeyDown(ev) {
        if (ev.key === "Escape") {
            ev.preventDefault();
            const navLink = this.el.querySelector(".shipping_nav_link");
            if (navLink) {
                navLink.focus();
            }
        }
        
        if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
            ev.preventDefault();
            const items = Array.from(
                this.el.querySelectorAll(".shipping_dropdown_item")
            );
            const currentIndex = items.indexOf(ev.currentTarget);
            let nextIndex;
            
            if (ev.key === "ArrowDown") {
                nextIndex = (currentIndex + 1) % items.length;
            } else {
                nextIndex = (currentIndex - 1 + items.length) % items.length;
            }
            
            items[nextIndex].focus();
        }
    }
});

// ============================================================
// 15. MOBILE NAVIGATION
// ============================================================
publicWidget.registry.ShippingMobileNav = publicWidget.Widget.extend({
    selector: ".shipping_header",
    events: {
        "click .shipping_mobile_menu_toggle": "_toggleMobileMenu",
        "click .shipping_dropdown_item": "_onMobileMenuItemClick",
    },

    init() {
        this._super(...arguments);
        this.mobileMenuOpen = false;
    },

    start() {
        this._checkMobileView();
        window.addEventListener("resize", this._checkMobileView.bind(this));
        return this._super(...arguments);
    },

    _checkMobileView() {
        if (window.innerWidth <= 991) {
            this._initMobileMenu();
        }
    },

    _initMobileMenu() {
        // Mobile menu initialization
    },

    _toggleMobileMenu() {
        this.mobileMenuOpen = !this.mobileMenuOpen;
        const nav = this.el.querySelector(".shipping_nav");
        if (nav) {
            nav.classList.toggle("mobile_open");
        }
    },

    _onMobileMenuItemClick() {
        if (this.mobileMenuOpen) {
            this._toggleMobileMenu();
        }
    }
});

// ============================================================
// INITIALIZATION & DOM READY
// ============================================================

document.addEventListener("DOMContentLoaded", function() {
    console.log("✅ DOM Ready - Shipping theme initialized");
    
    const isSupported = window.CSS && window.CSS.supports && 
                       window.CSS.supports('scroll-behavior', 'smooth');
    console.log("📋 Native smooth-scroll supported:", isSupported);
});

// Handle hash navigation on page load
window.addEventListener("load", function() {
    console.log("✅ Page fully loaded");
    
    if (window.location.hash) {
        const targetId = window.location.hash.substring(1);
        const target = document.getElementById(targetId);
        console.log("🔗 Navigating to hash on load:", targetId);
        
        if (target) {
            setTimeout(() => {
                const headerHeight = document.querySelector(".shipping_header")?.offsetHeight || 0;
                const elementTop = target.getBoundingClientRect().top + window.pageYOffset;
                const scrollPosition = elementTop - headerHeight - 20;
                
                window.scrollTo({
                    top: scrollPosition,
                    behavior: 'smooth'
                });
            }, 500);
        } else {
            console.warn("❌ Hash target not found:", targetId);
            window._sectionIdAudit();
        }
    }
});
publicWidget.registry.ShippingShop = publicWidget.Widget.extend({
    selector: ".s_shipping_shop",
    events: {
        "keyup #shipping_product_search": "_onSearchInput",
        "change #shipping_category_filter": "_onCategoryChange",
        "click .shipping_add_to_cart": "_onAddToCart",
    },

    start() {
        this._initProducts();
        return this._super(...arguments);
    },

    _initProducts() {
        this.products = Array.from(document.querySelectorAll(".shipping_product_card"));
        this.cart = JSON.parse(localStorage.getItem("shipping_cart") || "[]");
        this._updateCartCount();
    },

    _onSearchInput(ev) {
        const query = ev.currentTarget.value.toLowerCase();
        this._filterProducts(query, null);
    },

    _onCategoryChange(ev) {
        const category = ev.currentTarget.value;
        const query = document.getElementById("shipping_product_search").value.toLowerCase();
        this._filterProducts(query, category);
    },

    _filterProducts(query, category) {
        let visibleCount = 0;

        this.products.forEach((card) => {
            const name = card.querySelector(".shipping_product_name").textContent.toLowerCase();
            const description = card.querySelector(".shipping_product_description").textContent.toLowerCase();
            const cardCategory = card.getAttribute("data-category");

            const matchesSearch = !query || name.includes(query) || description.includes(query);
            const matchesCategory = !category || cardCategory === category;

            if (matchesSearch && matchesCategory) {
                card.style.display = "";
                visibleCount++;
            } else {
                card.style.display = "none";
            }
        });

        const emptyState = document.getElementById("shipping_shop_empty");
        if (visibleCount === 0 && emptyState) {
            emptyState.style.display = "block";
        } else if (emptyState) {
            emptyState.style.display = "none";
        }
    },

    _onAddToCart(ev) {
        const btn = ev.currentTarget;
        const productId = btn.getAttribute("data-product-id");
        const productName = btn.getAttribute("data-product-name");
        const productPrice = parseFloat(btn.getAttribute("data-product-price"));

        const existingItem = this.cart.find((item) => item.id === productId);
        if (existingItem) {
            existingItem.qty += 1;
        } else {
            this.cart.push({
                id: productId,
                name: productName,
                price: productPrice,
                qty: 1,
            });
        }

        localStorage.setItem("shipping_cart", JSON.stringify(this.cart));
        this._updateCartCount();

        // Animation feedback
        btn.textContent = "✓ Added!";
        setTimeout(() => {
            btn.textContent = "Add to Cart";
        }, 1500);
    },

    _updateCartCount() {
        const totalQty = this.cart.reduce((sum, item) => sum + item.qty, 0);
        console.log("Cart updated:", totalQty, "items");
    },
});


// ============================================================
// GLOBAL TOAST ANIMATIONS
// ============================================================

const styleSheet = document.createElement("style");
styleSheet.textContent = `
    @keyframes slideUpToast {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideDownToast {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(20px);
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @media (max-width: 575px) {
        .shipping_toast {
            bottom: 1rem !important;
            right: 1rem !important;
            left: 1rem !important;
            max-width: none !important;
        }
    }
`;
document.head.appendChild(styleSheet);

console.log("✅ Shipping Theme Complete - All widgets loaded");
