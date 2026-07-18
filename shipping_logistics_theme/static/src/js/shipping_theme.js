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

        // Set animated theme
        root.setThemes([am5themes_Animated.new(root)]);

        // 2. Create the Map Chart with a static default center (No auto-zoom animation)
        let chart = root.container.children.push(am5map.MapChart.new(root, {
            panX: "translateX",
            panY: "translateY",
            projection: am5map.geoMercator(),
            homeGeoPoint: { longitude: 85, latitude: 28 }, // Centers map statically between China and Gulf
            homeZoomLevel: 1.6 // Adjust this number if you want the map slightly closer or further out
        }));

        // 3. Add the Asia Map (Polygons)
        let polygonSeries = chart.series.push(am5map.MapPolygonSeries.new(root, {
    geoJSON: am5geodata_region_world_asiaLow
}));

// Default look for all countries
polygonSeries.mapPolygons.template.setAll({
    fill: am5.color(0xe3e3e3),   // light grey for non-highlighted
    stroke: am5.color(0xffffff),
    strokeWidth: 1
});

// List of country ISO codes you want to highlight in gold
const highlightedCountries = ["CN", "SA", "AE", "QA", "KW", "BH", "OM"];

// Conditionally apply the gold fill
polygonSeries.mapPolygons.template.adapters.add("fill", function(fill, target) {
    if (target.dataItem && target.dataItem.dataContext) {
        const id = target.dataItem.dataContext.id;   // country ISO code
        if (highlightedCountries.includes(id)) {
            return am5.color(0xD4AF37);   // gold fill
        }
    }
    return fill;  // keep default grey
});

        // 4. Define the Cities (Origin and Destinations)
      const origin = { 
    id: "cn", 
    title: "Central China", 
    geometry: { type: "Point", coordinates: [104.0, 36.0] },  // roughly Lanzhou region – centrally placed
    color: 0xD4AF37 
};
        
        const destinations = [
    { id: "sa", title: "Saudi Arabia", geometry: { type: "Point", coordinates: [45.0792, 23.8859] }, color: 0xD4AF37 },
    { id: "ae", title: "UAE",          geometry: { type: "Point", coordinates: [54.3666, 24.4667] }, color: 0xD4AF37 },
    { id: "qa", title: "Qatar",        geometry: { type: "Point", coordinates: [51.5310, 25.2854] }, color: 0xD4AF37 },
    { id: "kw", title: "Kuwait",       geometry: { type: "Point", coordinates: [47.9774, 29.3759] }, color: 0xD4AF37 },
    { id: "bh", title: "Bahrain",      geometry: { type: "Point", coordinates: [50.5860, 26.2285] }, color: 0xD4AF37 },
    { id: "om", title: "Oman",         geometry: { type: "Point", coordinates: [58.4059, 23.5859] }, color: 0xD4AF37 }
];

        // 5. Add Points (Cities) to the Map
        let pointSeries = chart.series.push(am5map.MapPointSeries.new(root, {}));
        
        pointSeries.bullets.push(function(root, series, dataItem) {
            let container = am5.Container.new(root, {});
            
            container.children.push(am5.Circle.new(root, {
                radius: 6,
                fill: am5.color(dataItem.dataContext.color),
                tooltipText: "{title}"
            }));

            let circle = container.children.push(am5.Circle.new(root, {
                radius: 6,
                fill: am5.color(dataItem.dataContext.color),
                opacity: 0.5
            }));
            
            circle.animate({
                key: "radius",
                to: 15,
                duration: 1500,
                easing: am5.ease.out(am5.ease.cubic),
                loops: Infinity
            });

            return am5.Bullet.new(root, {
                sprite: container
            });
        });

        pointSeries.data.push(origin);
        destinations.forEach(dest => pointSeries.data.push(dest));

        // 6. Draw the Lines between Origin and Destinations
        let lineSeries = chart.series.push(am5map.MapLineSeries.new(root, {}));
        
        lineSeries.mapLines.template.setAll({
            strokeWidth: 2,
            strokeOpacity: 0.6,
            strokeDasharray: [4, 4]
        });

        destinations.forEach(dest => {
            lineSeries.data.push({
                geometry: {
                    type: "LineString",
                    coordinates: [
                        origin.geometry.coordinates,
                        dest.geometry.coordinates
                    ]
                },
                stroke: am5.color(dest.color)
            });
        });

        lineSeries.mapLines.template.adapters.add("stroke", function(stroke, target) {
            if (target.dataItem) {
                return target.dataItem.dataContext.stroke;
            }
            return stroke;
        });

        // Tells amCharts to automatically show the map at the home position instantly
        polygonSeries.events.on("datavalidated", function () {
            chart.goHome();
        });

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