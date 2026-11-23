frappe.ui.form.on("Patient Admission", {

    setup(frm) {

        // Show only active patients
        frm.set_query("patient", function() {
            return {
                filters: {
                    is_active: 1
                }
            };
        });

        // Show only active doctors
        frm.set_query("doctor", function() {
            return {
                filters: {
                    is_active: 1
                }
            };
        });

        // Show only active rooms
        frm.set_query("room", function() {
            return {
                filters: {
                    is_active: 1
                }
            };
        });

        // Show only available beds belonging to selected room
        frm.set_query("bed", function() {

            if (!frm.doc.room) {
                return {
                    filters: {
                        name: ["=", ""]
                    }
                };
            }

            return {
                filters: {
                    room: frm.doc.room,
                    bed_status: "Available",
                    is_active: 1
                }
            };
        });
    },

    // Automatically fetch doctor's department
    doctor(frm) {

        if (!frm.doc.doctor) {
            frm.set_value("department", "");
            return;
        }

        frappe.db.get_value(
            "Doctor",
            frm.doc.doctor,
            "department"
        ).then(function(r) {

            if (r.message) {
                frm.set_value("department", r.message.department);
            }

        });
    },
    // Admission Billing Buttons
    refresh(frm) {

        if (frm.is_new()) {
            return;
        }

        // If invoice already exists, show View button
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

        // Show Create button when discharge date is entered
        else if (
            frm.doc.admission_status === "Admitted" &&
            frm.doc.discharge_date
        ) {

            frm.add_custom_button(
                __("Create Sales Invoice"),
                function() {

                    // Ensure discharge date is saved first
                    if (frm.is_dirty()) {

                        frappe.msgprint(
                            __("Please save the admission before creating the invoice.")
                        );

                        return;
                    }

                    frappe.confirm(
                        __("Create the final admission Sales Invoice?"),

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

    },
    // When room changes, clear the previous bed
    // and fetch the room's daily charge
    room(frm) {

        frm.set_value("bed", "");

        if (!frm.doc.room) {
            frm.set_value("daily_room_charge", 0);
            return;
        }

        frappe.db.get_value(
            "Hospital Room",
            frm.doc.room,
            "daily_charge"
        ).then(function(r) {

            if (r.message) {
                frm.set_value(
                    "daily_room_charge",
                    r.message.daily_charge || 0
                );
            }

        });
    }

});