import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, date_diff, now_datetime


class PatientAdmission(Document):

    def validate(self):
        self.set_default_values()
        self.validate_patient()
        self.validate_doctor()
        self.validate_room_and_bed()
        self.set_room_charge()
        self.calculate_charges()
        self.validate_discharge()

    # Set default values
    def set_default_values(self):
        if not self.admission_status:
            self.admission_status = "Admitted"

        if not self.doctor_approval_status:
            self.doctor_approval_status = "Pending"

        if not self.payment_status:
            self.payment_status = "Not Billed"

    # Validate patient
    def validate_patient(self):
        patient = frappe.get_doc("Patient", self.patient)

        if not patient.is_active:
            frappe.throw(_("This patient is inactive."))

        filters = {
            "patient": self.patient,
            "admission_status": "Admitted"
        }

        if not self.is_new():
            filters["name"] = ["!=", self.name]

        existing = frappe.db.exists("Patient Admission", filters)

        if existing:
            frappe.throw(
                _("This patient already has an active admission: {0}")
                .format(existing)
            )

    # Validate doctor
    def validate_doctor(self):
        doctor = frappe.get_doc("Doctor", self.doctor)

        if not doctor.is_active:
            frappe.throw(_("The selected doctor is inactive."))

        if doctor.department != self.department:
            frappe.throw(
                _("The selected doctor's department does not match "
                  "the admission department.")
            )

    # Validate room and bed
    def validate_room_and_bed(self):

        room = frappe.get_doc("Hospital Room", self.room)
        bed = frappe.get_doc("Hospital Bed", self.bed)

        if not room.is_active:
            frappe.throw(_("The selected room is inactive."))

        if not bed.is_active:
            frappe.throw(_("The selected bed is inactive."))

        if bed.room != self.room:
            frappe.throw(
                _("The selected bed does not belong to this room.")
            )

        # Prevent another active admission from using this bed
        filters = {
            "bed": self.bed,
            "admission_status": "Admitted"
        }

        if not self.is_new():
            filters["name"] = ["!=", self.name]

        existing = frappe.db.exists("Patient Admission", filters)

        if existing:
            frappe.throw(
                _("This bed is already assigned to another patient.")
            )

        # Allow an existing admission to retain its own occupied bed
        current_admission = None

        if not self.is_new():
            current_admission = frappe.db.get_value(
                "Patient Admission",
                self.name,
                ["bed", "admission_status"],
                as_dict=True
            )

        same_active_bed = (
            current_admission
            and current_admission.bed == self.bed
            and current_admission.admission_status == "Admitted"
        )

        if bed.bed_status != "Available" and not same_active_bed:
            frappe.throw(
                _("This bed is not available. Current status: {0}")
                .format(bed.bed_status)
            )

        # Prevent changing the bed of an active admission directly
        if current_admission and current_admission.admission_status == "Admitted":
            if current_admission.bed != self.bed:
                frappe.throw(
                    _("Use a bed transfer process to change an "
                      "active patient's bed.")
                )

    # Automatically fetch daily room charge
    def set_room_charge(self):

        room_charge = frappe.db.get_value(
            "Hospital Room",
            self.room,
            "daily_charge"
        )

        self.daily_room_charge = flt(room_charge)

    # Calculate admission charges
    def calculate_charges(self):

        if self.discharge_date:

            stay_days = date_diff(
                self.discharge_date,
                self.admission_date
            ) + 1

            if stay_days < 1:
                frappe.throw(
                    _("Discharge date cannot be before admission date.")
                )

            self.total_stay_days = stay_days

            self.total_room_charges = (
                flt(self.daily_room_charge) * stay_days
            )

        else:
            self.total_stay_days = 0
            self.total_room_charges = 0

        self.total_admission_charges = (
            flt(self.total_room_charges)
            + flt(self.treatment_charges)
            + flt(self.medicine_charges)
        )

    # Validate discharge conditions
    def validate_discharge(self):

        if self.doctor_approval_status == "Approved":

            if not self.approved_by:
                frappe.throw(
                    _("Select the doctor who approved the discharge.")
                )

            if not self.approval_datetime:
                self.approval_datetime = now_datetime()

        if self.admission_status == "Discharged":

            if not self.discharge_date or not self.discharge_time:
                frappe.throw(
                    _("Discharge date and time are required.")
                )

            if not self.payment_verified:
                frappe.throw(
                    _("Payment must be verified before discharge.")
                )

            if self.doctor_approval_status != "Approved":
                frappe.throw(
                    _("Doctor approval is required before discharge.")
                )

    # Update bed availability after admission changes
    def on_update(self):

        if self.admission_status == "Admitted":

            frappe.db.set_value(
                "Hospital Bed",
                self.bed,
                "bed_status",
                "Occupied"
            )

        elif self.admission_status in ["Discharged", "Cancelled"]:

            frappe.db.set_value(
                "Hospital Bed",
                self.bed,
                "bed_status",
                "Available"
            )




    # Create Sales Invoice for final admission charges
    @frappe.whitelist()
    def create_sales_invoice(self):

        self.check_permission("write")

        # Only admitted patients can be billed
        if self.admission_status != "Admitted":
            frappe.throw(
                _("Only admitted patients can be billed.")
            )

        # Discharge date is required to calculate final room charges
        if not self.discharge_date:
            frappe.throw(
                _("Please enter the discharge date before generating the final bill.")
            )

        # Prevent duplicate invoice generation
        if self.sales_invoice:
            if frappe.db.exists("Sales Invoice", self.sales_invoice):
                frappe.throw(
                    _("An invoice is already linked to this admission: {0}")
                    .format(self.sales_invoice)
                )

        # Get patient and linked ERPNext Customer
        patient = frappe.get_doc("Patient", self.patient)

        if not patient.customer:
            frappe.throw(
                _("No ERPNext Customer is linked to this patient.")
            )

        if not frappe.db.exists("Customer", patient.customer):
            frappe.throw(
                _("The linked ERPNext Customer does not exist.")
            )

        # Calculate treatment charges from Treatment Records
        treatment_result = frappe.db.sql(
            """
            SELECT COALESCE(SUM(treatment_charges), 0)
            FROM `tabTreatment Record`
            WHERE patient_admission = %s
            """,
            (self.name,)
        )

        self.treatment_charges = flt(treatment_result[0][0])

        # Calculate medicine charges from submitted Medicine Usage
        medicine_result = frappe.db.sql(
            """
            SELECT COALESCE(SUM(total_medicine_charges), 0)
            FROM `tabMedicine Usage`
            WHERE patient_admission = %s
            AND docstatus = 1
            """,
            (self.name,)
        )

        self.medicine_charges = flt(medicine_result[0][0])

        # Calculate final room and admission charges
        self.set_room_charge()
        self.calculate_charges()

        if flt(self.total_admission_charges) <= 0:
            frappe.throw(
                _("Total admission charges must be greater than zero.")
            )

        # Get company
        company = frappe.defaults.get_user_default("Company")

        if not company or not frappe.db.exists("Company", company):
            frappe.throw(
                _("Please configure a valid default Company.")
            )

        # Create Sales Invoice
        invoice = frappe.new_doc("Sales Invoice")

        invoice.company = company
        invoice.customer = patient.customer
        invoice.posting_date = frappe.utils.today()
        invoice.selling_price_list = "Standard Selling"

        # Prepare admission charge items
        charge_items = [
            ("ROOM-CHARGE", flt(self.total_room_charges)),
            ("TREATMENT-CHARGE", flt(self.treatment_charges)),
            ("MEDICINE-CHARGE", flt(self.medicine_charges))
        ]

        for item_code, amount in charge_items:

            if amount > 0:

                if not frappe.db.exists("Item", item_code):
                    frappe.throw(
                        _("Billing item {0} does not exist.")
                        .format(item_code)
                    )

                invoice.append("items", {
                    "item_code": item_code,
                    "qty": 1,
                    "rate": amount
                })

        # Fetch accounting defaults
        invoice.set_missing_values()

        # Restore the calculated admission charges
        for invoice_item in invoice.items:

            for item_code, amount in charge_items:

                if invoice_item.item_code == item_code:
                    invoice_item.rate = amount
                    invoice_item.price_list_rate = amount

        invoice.calculate_taxes_and_totals()

        # Save as Draft for review
        invoice.insert()

        # Link invoice to Patient Admission
        self.sales_invoice = invoice.name
        self.payment_status = "Not Billed"
        self.save()

        return invoice.name