/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

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

publicWidget.registry.ShippingNetworkMap = publicWidget.Widget.extend({
        selector: "#shipping_routes_map",

    start() {
        this._renderAmChart();
        return this._super(...arguments);
    },

    _renderAmChart() {
        // 1. Initialize amCharts Root
        let root = am5.Root.new(this.el);

        // Set animated theme with custom colors
        root.setThemes([am5themes_Animated.new(root)]);

        // 2. Create the Map Chart with enhanced settings
        let chart = root.container.children.push(am5map.MapChart.new(root, {
                panX: "none",      // Locks horizontal map panning
    panY: "none",      // Locks vertical map panning
    wheelX: "none",    // Locks mouse wheel horizontal zoom
    wheelY: "none" ,    // Locks mouse wheel vertical zoom
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
            fill: am5.color(0xe8e8e8),      // slightly warmer grey
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

        // Apply animated dash offset for flowing effect
        lineSeries.mapLines.template.adapters.add("strokeDasharray", function(dasharray, target) {
            // Animated effect will be handled by CSS if needed
            return dasharray;
        });

        // Add subtle shadows to lines
        lineSeries.mapLines.template.set("tooltipText", "Trade Route");

        // 7. Auto-zoom to show all data
        polygonSeries.events.on("datavalidated", function () {
            chart.goHome();
        });

        // Add entrance animation
        chart.appear(1000, 100);
    }
});
// 3D Depth-of-Field Coverflow Testimonials
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
        this.delay = 5000; // Auto-play delay
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
            // Calculate distance from current index
            let offset = index - this.currentIndex;
            
            // Adjust offset for an infinite circular loop
            if (offset > Math.floor(total / 2)) {
                offset -= total;
            } else if (offset < -Math.floor(total / 2)) {
                offset += total;
            }

            // Assign the dataset position for CSS targeting
            // If the card is more than 2 spaces away, hide it deep in the background
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
        // If the user clicks a side card, move the carousel to that card
        const clickedPos = parseInt(ev.currentTarget.dataset.pos);
        if (clickedPos === 0 || isNaN(clickedPos)) return; // Already active

        // Calculate new index
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

// Interactive hover effects
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


// Header Scroll Effect
publicWidget.registry.ShippingHeader = publicWidget.Widget.extend({
    selector: ".shipping_header",
    events: {},

    start() {
        this._onScroll = this._onScroll.bind(this);
        window.addEventListener("scroll", this._onScroll, {passive: true});
        return this._super(...arguments);
    },

    destroy() {
        window.removeEventListener("scroll", this._onScroll);
        this._super(...arguments);
    },

    _onScroll() {
        if (window.scrollY > 20) {
            this.el.classList.add("header_scrolled");
        } else {
            this.el.classList.remove("header_scrolled");
        }
    },
});

// Drag & Drop for service cards
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

// Blog Articles Loader
publicWidget.registry.ShippingBlog = publicWidget.Widget.extend({
    selector: "#shipping_blog_grid",
    async start() {
        const _super = this._super(...arguments);
        try {
            const data = await rpc("/shipping/blog", { limit: 4 });
            const articles = (data && data.articles) || [];
            if (articles.length) {
                // Get all back faces (same order as static cards)
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

    /**
     * Initialize scroll animations for elements
     */
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

        // Observe all cards for animation
        this.el.querySelectorAll(".shipping_office_card, .email_channel_card, .chat_channel_btn").forEach(card => {
            observer.observe(card);
        });
    },

    /**
     * Setup form validation
     */
    _setupFormValidation() {
        this.form = this.el.querySelector("#shipping_contact_form");
        if (this.form) {
            this.form.noValidate = true; // Use custom validation
        }
    },

    /**
     * Handle form submission
     */
    async _onFormSubmit(ev) {
        ev.preventDefault();

        if (!this._validateForm()) {
            return;
        }

        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData);

        // Show loading state
        const submitBtn = this.form.querySelector(".form_submit_btn");
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";

        try {
            // Send to RPC endpoint
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

    /**
     * Validate form fields
     */
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
        if (!privacyCheckbox.checked) {
            this._showFieldError(privacyCheckbox, "You must agree to the privacy policy");
            isValid = false;
        }

        return isValid;
    },

    /**
     * Show field error message
     */
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

    /**
     * Clear field error message
     */
    _clearFieldError(field) {
        const errorDiv = field.parentNode.querySelector(".form_error");
        if (errorDiv) {
            errorDiv.remove();
        }
        field.style.borderColor = "";
        field.style.boxShadow = "";
    },

    /**
     * Validate email format
     */
    _isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    /**
     * Validate phone format (basic)
     */
    _isValidPhone(phone) {
        const phoneRegex = /^[+\d\s\-()]+$/;
        return phoneRegex.test(phone) && phone.replace(/\D/g, "").length >= 7;
    },

    /**
     * Show success message
     */
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

    /**
     * Show error message
     */
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

    /**
     * Handle chat channel clicks
     */
    _onChatClick(ev) {
        const btn = ev.currentTarget;
        
        // Add click animation
        btn.style.transform = "scale(0.98)";
        setTimeout(() => {
            btn.style.transform = "";
        }, 100);

        // Handle WeChat specially (show QR code or message)
        if (btn.classList.contains("wechat")) {
            const wechatId = btn.dataset.wechatId;
            this._showWeChatInfo(wechatId);
            ev.preventDefault();
        }
    },

    /**
     * Show WeChat information
     */
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

    /**
     * Handle form field focus
     */
    _onFormFieldFocus(ev) {
        const field = ev.currentTarget;
        field.style.background = "#fffbf5";
    },

    /**
     * Handle form field blur
     */
    _onFormFieldBlur(ev) {
        const field = ev.currentTarget;
        if (!field.value.trim()) {
            field.style.background = "#fff";
        }
    }
});

// Add global toast animations
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
