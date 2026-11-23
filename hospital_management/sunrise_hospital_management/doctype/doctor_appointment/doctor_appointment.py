import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class DoctorAppointment(Document):

    def validate(self):
        self.validate_appointment_datetime()
        self.validate_doctor_details()
        self.validate_doctor_availability()

    # 1. Validate Appointment Date and Time
    def validate_appointment_datetime(self):

        if not self.appointment_date or not self.appointment_time:
            return

        appointment_datetime = get_datetime(
            f"{self.appointment_date} {self.appointment_time}"
        )

        # Allow updates when the original appointment
        # date and time remain unchanged.
        if not self.is_new():

            previous_appointment = frappe.db.get_value(
                "Doctor Appointment",
                self.name,
                ["appointment_date", "appointment_time"],
                as_dict=True
            )

            if previous_appointment:

                previous_datetime = get_datetime(
                    f"{previous_appointment.appointment_date} "
                    f"{previous_appointment.appointment_time}"
                )

                if appointment_datetime == previous_datetime:
                    return

        # Prevent booking or rescheduling into the past.
        if appointment_datetime < now_datetime():

            frappe.throw(
                "Appointment date and time cannot be in the past."
            )

    # 2. Validate Doctor Details
    def validate_doctor_details(self):

        if not self.doctor or not self.department:
            return

        doctor = frappe.get_doc("Doctor", self.doctor)

        if not doctor.is_active:
            frappe.throw(
                "This doctor is inactive and cannot receive appointments."
            )

        if doctor.department != self.department:
            frappe.throw(
                "The selected doctor does not belong to "
                "the selected department."
            )

        # Automatically fetch consultation fee
        self.consultation_fee = doctor.consultation_fee

    # 3. Prevent Duplicate Doctor Appointments
    def validate_doctor_availability(self):

        if not all([
            self.doctor,
            self.appointment_date,
            self.appointment_time
        ]):
            return

        if self.appointment_status == "Cancelled":
            return

        filters = {
            "doctor": self.doctor,
            "appointment_date": self.appointment_date,
            "appointment_time": self.appointment_time,
            "appointment_status": ["!=", "Cancelled"]
        }

        # Exclude current appointment when editing
        if not self.is_new():
            filters["name"] = ["!=", self.name]

        existing_appointment = frappe.db.exists(
            "Doctor Appointment",
            filters
        )

        if existing_appointment:

            frappe.throw(
                "This doctor already has an appointment "
                "scheduled for the selected date and time."
            )




    # 4. Create Sales Invoice
    @frappe.whitelist()
    def create_sales_invoice(self):

        self.check_permission("write")

        # Only completed appointments can be billed
        if self.appointment_status != "Completed":
            frappe.throw(
                "Sales Invoice can only be created "
                "for completed appointments."
            )

        # Prevent duplicate invoice generation
        if self.sales_invoice:
            if frappe.db.exists("Sales Invoice", self.sales_invoice):
                frappe.throw(
                    f"Sales Invoice {self.sales_invoice} "
                    "is already linked to this appointment."
                )

        # Get patient details
        patient = frappe.get_doc("Patient", self.patient)

        if not patient.customer:
            frappe.throw(
                "No ERPNext Customer is linked to this patient. "
                "Please link the customer in the Patient record."
            )

        if not frappe.db.exists("Customer", patient.customer):
            frappe.throw(
                "The linked ERPNext Customer does not exist."
            )

        # Validate consultation fee
        consultation_fee = frappe.utils.flt(self.consultation_fee)

        if consultation_fee <= 0:
            frappe.throw(
                "Consultation Fee must be greater than zero."
            )

        # Get company
        company = frappe.defaults.get_user_default("Company")

        if not company or not frappe.db.exists("Company", company):
            frappe.throw(
                "Please configure a valid default Company."
            )

        # Validate consultation service item
        item_code = "DOC-CONSULT"

        if not frappe.db.exists("Item", item_code):
            frappe.throw(
                "Doctor Consultation service item was not found."
            )

        item = frappe.get_doc("Item", item_code)

        if not item.is_sales_item or item.is_stock_item:
            frappe.throw(
                "Doctor Consultation must be a non-stock sales item."
            )

        # Create Sales Invoice
        invoice = frappe.new_doc("Sales Invoice")

        invoice.company = company
        invoice.customer = patient.customer
        invoice.posting_date = frappe.utils.today()
        invoice.selling_price_list = "Standard Selling"

        # Add consultation service
        invoice.append("items", {
            "item_code": item_code,
            "qty": 1,
            "rate": consultation_fee
        })

        # Fetch ERPNext accounting defaults
        invoice.set_missing_values()

        # Apply actual appointment consultation fee
        invoice.items[0].rate = consultation_fee
        invoice.items[0].price_list_rate = consultation_fee

        # Calculate invoice totals
        invoice.calculate_taxes_and_totals()

        # Save invoice as Draft
        invoice.insert()

        # Link invoice to appointment
        self.sales_invoice = invoice.name
        self.save()

        return invoice.name
