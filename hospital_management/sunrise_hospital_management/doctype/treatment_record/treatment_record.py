import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


def update_admission_treatment_charges(admission_name, exclude_name=None):

    if not admission_name:
        return

    query = """
        SELECT COALESCE(SUM(treatment_charges), 0)
        FROM `tabTreatment Record`
        WHERE patient_admission = %s
    """

    values = [admission_name]

    if exclude_name:
        query += " AND name != %s"
        values.append(exclude_name)

    result = frappe.db.sql(query, values)

    total_treatment = flt(result[0][0])

    admission = frappe.get_doc(
        "Patient Admission",
        admission_name
    )

    total_admission = (
        flt(admission.total_room_charges)
        + total_treatment
        + flt(admission.medicine_charges)
    )

    frappe.db.set_value(
        "Patient Admission",
        admission_name,
        {
            "treatment_charges": total_treatment,
            "total_admission_charges": total_admission
        },
        update_modified=False
    )


class TreatmentRecord(Document):

    def validate(self):
        self.validate_admission()
        self.fetch_patient_and_doctor()
        self.validate_treatment_date()
        self.validate_charges()

    # Validate the selected admission
    def validate_admission(self):

        if not self.patient_admission:
            frappe.throw(
                _("Please select a Patient Admission.")
            )

        admission = frappe.get_doc(
            "Patient Admission",
            self.patient_admission
        )

        if admission.admission_status != "Admitted":
            frappe.throw(
                _("Treatments can only be recorded for admitted patients.")
            )

    # Automatically fetch patient and doctor
    def fetch_patient_and_doctor(self):

        admission = frappe.get_doc(
            "Patient Admission",
            self.patient_admission
        )

        self.patient = admission.patient
        self.doctor = admission.doctor

    # Validate treatment date
    def validate_treatment_date(self):

        admission = frappe.get_doc(
            "Patient Admission",
            self.patient_admission
        )

        if not self.treatment_date:
            frappe.throw(
                _("Treatment Date is mandatory.")
            )

        treatment_date = getdate(self.treatment_date)
        admission_date = getdate(admission.admission_date)

        if treatment_date < admission_date:
            frappe.throw(
                _("Treatment date cannot be before admission date.")
            )

        if admission.discharge_date:
            if treatment_date > getdate(admission.discharge_date):
                frappe.throw(
                    _("Treatment date cannot be after discharge date.")
                )

    # Validate treatment charges
    def validate_charges(self):

        if flt(self.treatment_charges) < 0:
            frappe.throw(
                _("Treatment charges cannot be negative.")
            )

    # Synchronise charges with Patient Admission
    def on_update(self):

        old_doc = self.get_doc_before_save()

        if (
            old_doc
            and old_doc.patient_admission != self.patient_admission
        ):
            update_admission_treatment_charges(
                old_doc.patient_admission,
                exclude_name=self.name
            )

        update_admission_treatment_charges(
            self.patient_admission
        )

    # Recalculate charges when a treatment record is deleted
    def on_trash(self):

        update_admission_treatment_charges(
            self.patient_admission,
            exclude_name=self.name
        )