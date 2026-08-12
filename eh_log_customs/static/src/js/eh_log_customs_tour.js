/** @odoo-module **/
// ERP Heritage Logistics: Customs onboarding tour.
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("eh_log_customs_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open the Logistics app and go to Customs Declarations.",
            trigger: ".o_navbar_apps_menu, .o_app:contains('Logistics')",
            run: "click",
        },
        {
            content: "This is the customs declarations list. Each declaration is bound to a regulator-of-record per country (Mirsal 2, FASAH, Bayan, OFFS, Kuwait Customs, Al Nadeeb).",
            trigger: ".o_list_view, .o_kanban_view",
        },
        {
            content: "Open a declaration. Note the snapshot hero: Exporter > declaration type pill > Importer; below that, customer, declaration date, customs value, duty + VAT.",
            trigger: ".o_data_row:first, .o_kanban_record:first",
            run: "click",
        },
        {
            content: "The declaration type drives which fields are mandatory and which adapter the regulator submission uses.",
            trigger: "[name='declaration_type_id']",
        },
        {
            content: "The deferment account is optional. If set, duties debit it instead of paying at clearance. The form shows live balance and limit.",
            trigger: "[name='deferment_account_id']",
        },
        {
            content: "Submit to the regulator via the action button. The adapter posts the declaration; the regulator reference comes back on success.",
            trigger: "button[name='action_submit']",
        },
        {
            content: "If clearance comes back with a query, the queries page shows the regulator response. Resolve, attach evidence, resubmit.",
            trigger: ".o_notebook .nav-link:contains('Queries'), .o_notebook .nav-link:contains('Lines')",
        },
        {
            content: "When the regulator clears the declaration, the state moves to Cleared. The freight job is unblocked for delivery.",
            trigger: ".o_statusbar_status",
        },
    ],
});
