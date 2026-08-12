/** @odoo-module **/
// ERP Heritage Logistics: Last Mile onboarding tour.
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("eh_log_last_mile_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open the Logistics app and go to Operations > Last Mile Waves.",
            trigger: ".o_navbar_apps_menu, .o_app:contains('Logistics')",
            run: "click",
        },
        {
            content: "A wave groups deliveries by date / driver / vehicle. The kanban shows wave state: draft > dispatched > in_progress > completed > closed.",
            trigger: ".o_kanban_view, .o_list_view",
        },
        {
            content: "Open a wave. The deliveries page shows every drop sequenced for the route.",
            trigger: ".o_data_row:first, .o_kanban_record:first",
            run: "click",
        },
        {
            content: "Open a delivery. The snapshot hero shows customer > truck pill > wave; below that the time window, packages + weight, and COD amount.",
            trigger: ".o_data_row:first td:first, .o_field_one2many .o_data_row:first",
        },
        {
            content: "COD amount on a delivery: the driver records collection on the mobile POD form. Reconciliation finance task fires if collected differs from due.",
            trigger: "[name='cod_amount']",
        },
        {
            content: "Mass-mark delivered: select multiple deliveries from the list and use the wizard for bulk POD capture. State moves out_for_delivery > delivered.",
            trigger: ".o_list_button_add, button[name='action_mass_mark_delivered']",
        },
        {
            content: "Failed deliveries surface as red rows with the failure reason. Reschedule or return-to-sender from the action buttons.",
            trigger: "button[name='action_mark_failed'], .o_data_row.o_list_row_failed",
        },
    ],
});
