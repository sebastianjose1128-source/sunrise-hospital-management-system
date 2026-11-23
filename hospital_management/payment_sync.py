import frappe
from frappe.utils import flt


def get_invoice_payment_status(invoice):

    # Draft or cancelled invoice
    if invoice.docstatus != 1:
        return "Not Billed"

    grand_total = flt(invoice.grand_total)
    outstanding = flt(invoice.outstanding_amount)

    if outstanding <= 0 and grand_total > 0:
        return "Paid"

    elif outstanding < grand_total:
        return "Partially Paid"

    return "Unpaid"


def update_appointment_payment_status(sales_invoice_name):

    # Get the Sales Invoice
    if not frappe.db.exists("Sales Invoice", sales_invoice_name):
        return

    invoice = frappe.get_doc(
        "Sales Invoice",
        sales_invoice_name
    )

    payment_status = get_invoice_payment_status(invoice)

    # Find linked Doctor Appointments
    appointments = frappe.get_all(
        "Doctor Appointment",
        filters={
            "sales_invoice": sales_invoice_name
        },
        pluck="name"
    )

    # Update Doctor Appointment payment status
    for appointment_name in appointments:

        frappe.db.set_value(
            "Doctor Appointment",
            appointment_name,
            "payment_status",
            payment_status
        )

    # Find linked Patient Admissions
    admissions = frappe.get_all(
        "Patient Admission",
        filters={
            "sales_invoice": sales_invoice_name
        },
        pluck="name"
    )

    # Update Patient Admission payment status
    for admission_name in admissions:

        frappe.db.set_value(
            "Patient Admission",
            admission_name,
            {
                "payment_status": payment_status,
                "payment_verified": 1 if payment_status == "Paid" else 0
            },
            update_modified=False
        )


# Sales Invoice submitted
def sales_invoice_on_submit(doc, method=None):

    update_appointment_payment_status(doc.name)


# Sales Invoice cancelled
def sales_invoice_on_cancel(doc, method=None):

    update_appointment_payment_status(doc.name)


# Payment Entry submitted
def payment_entry_on_submit(doc, method=None):

    for reference in doc.references:

        if reference.reference_doctype == "Sales Invoice":

            update_appointment_payment_status(
                reference.reference_name
            )


# Payment Entry cancelled
def payment_entry_on_cancel(doc, method=None):

    for reference in doc.references:

        if reference.reference_doctype == "Sales Invoice":

            update_appointment_payment_status(
                reference.reference_name
            )