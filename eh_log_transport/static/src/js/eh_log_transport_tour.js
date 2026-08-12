/** @odoo-module **/
// ERP Heritage Logistics: Road Transport onboarding tour.
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("eh_log_transport_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open the Logistics app and go to Operations > Trips.",
            trigger: ".o_navbar_apps_menu, .o_app:contains('Logistics')",
            run: "click",
        },
        {
            content: "This is the trip list, grouped by state on the kanban: Planned, Dispatched, At Pickup, In Transit, At Delivery, Delivered, Closed.",
            trigger: ".o_kanban_view, .o_list_view",
        },
        {
            content: "Open a trip. The snapshot hero shows Pickup > truck pill with km > Delivery, plus customer, driver+vehicle, planned pickup, and planned delivery.",
            trigger: ".o_data_row:first, .o_kanban_record:first",
            run: "click",
        },
        {
            content: "Vehicle and driver are required at dispatch. The system checks the driver's licence expiry and surfaces a warning if it has passed.",
            trigger: "[name='vehicle_id'], [name='driver_id']",
        },
        {
            content: "Dispatch the trip. State moves planned > dispatched; the driver gets the manifest on the mobile portal.",
            trigger: "button[name='action_dispatch']",
        },
        {
            content: "Driver arrives at pickup, the gate-in event fires from the telematics adapter. State moves dispatched > at_pickup > in_transit when loaded.",
            trigger: ".o_statusbar_status",
        },
        {
            content: "POD capture: open the ePOD page on the notebook to attach the signature image and the recipient name. Required to close the trip.",
            trigger: ".o_notebook .nav-link:contains('ePOD'), .o_notebook .nav-link:contains('POD')",
        },
        {
            content: "Once POD is captured the trip moves to delivered. The manager closes the file after cost/revenue reconciliation.",
            trigger: "button[name='action_close']",
        },
    ],
});
