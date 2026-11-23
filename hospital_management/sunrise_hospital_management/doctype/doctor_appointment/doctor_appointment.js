frappe.ui.form.on("Doctor Appointment", {

    setup(frm) {

        // Filter active doctors according to department
        frm.set_query("doctor", function() {

            if (!frm.doc.department) {
                return {
                    filters: {
                        name: ["=", ""]
                    }
                };
            }

            return {
                filters: {
                    department: frm.doc.department,
                    is_active: 1
                }
            };

        });

    },

    department(frm) {

        // Clear doctor when department changes
        frm.set_value("doctor", "");

        // Clear previous consultation fee
        frm.set_value("consultation_fee", "");

    },

    refresh(frm) {

        // Show billing buttons only for saved appointments
        if (frm.is_new()) {
            return;
        }

        // Existing invoice: provide a View button
        if (frm.doc.sales_invoice) {

            frm.add_custom_button(
                __("View Sales Invoice"),
                function() {

                    frappe.set_route(
                        "Form",
                        "Sales Invoice",
                        frm.doc.sales_invoice
                    );

                },
                __("Billing")
            );

        }

        // Completed appointment without an invoice:
        // provide a Create Sales Invoice button
        else if (frm.doc.appointment_status === "Completed") {

            frm.add_custom_button(
                __("Create Sales Invoice"),
                function() {

                    frappe.confirm(
                        __("Create a Sales Invoice for this appointment?"),

                        function() {

                            frm.call("create_sales_invoice").then(function(r) {

                                if (r.message) {

                                    frappe.show_alert({
                                        message: __(
                                            "Sales Invoice {0} created successfully.",
                                            [r.message]
                                        ),
                                        indicator: "green"
                                    });

                                    frm.reload_doc().then(function() {

                                        frappe.set_route(
                                            "Form",
                                            "Sales Invoice",
                                            r.message
                                        );

                                    });

                                }

                            });

                        }
                    );

                },
                __("Billing")
            );

        }

    }

});
