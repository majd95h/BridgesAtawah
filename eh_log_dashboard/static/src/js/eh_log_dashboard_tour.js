/** @odoo-module **/
// ERP Heritage Logistics Suite onboarding tour.
// Walks a new operator through dashboard → quotation → freight → close
// in a small handful of steps so the suite shape is obvious within
// the first session.
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("eh_log_onboarding_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Welcome to ERP Heritage Logistics. Let's open the dashboard.",
            trigger: ".o_navbar_apps_menu",
            run: "click",
        },
        {
            content: "Pick the ERP Heritage Logistics app.",
            trigger: ".o_app:contains('Logistics')",
            run: "click",
        },
        {
            content:
                "This is your single pane: live KPI tiles for quotes, freight, customs, transport, and every installed vertical. Click any tile to drill down.",
            trigger: ".o_kanban_view, .o_form_view",
        },
        {
            content: "Open the Quotations menu to create your first logistics quotation.",
            trigger: ".o_menu_brand",
        },
    ],
});
