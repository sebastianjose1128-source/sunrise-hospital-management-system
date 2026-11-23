import re
from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, now_datetime


class PatientAppointmentRequest(Document):

    def validate(self):
        self.validate_mobile_number()
        self.validate_booking_details()

    def validate_mobile_number(self):
        mobile = (self.mobile_number or "").strip()
        digits = re.sub(r"\D", "", mobile)

        if not 7 <= len(digits) <= 15:
            frappe.throw(
                "Please enter a valid mobile number containing 7 to 15 digits."
            )

        self.mobile_number = mobile

    def validate_booking_details(self):

        if not frappe.db.exists("Hospital Department", self.department):
            frappe.throw("Selected department does not exist.")

        department_active = frappe.db.get_value(
            "Hospital Department", self.department, "is_active"
        )

        if not department_active:
            frappe.throw("Selected department is inactive.")

        if not frappe.db.exists("Doctor", self.doctor):
            frappe.throw("Selected doctor does not exist.")

        doctor = frappe.get_doc("Doctor", self.doctor)

        if not doctor.is_active:
            frappe.throw("Selected doctor is currently unavailable.")

        if doctor.department != self.department:
            frappe.throw(
                "The selected doctor does not belong to the selected department."
            )

        # Validate the selected time slot against configured options.
        time_field = self.meta.get_field("appointment_time")
        allowed_slots = [
            value.strip()
            for value in (time_field.options or "").splitlines()
            if value.strip()
        ]

        if self.appointment_time not in allowed_slots:
            frappe.throw("Please select a valid appointment time slot.")

        try:
            appointment_time = datetime.strptime(
                self.appointment_time, "%I:%M %p"
            ).strftime("%H:%M:%S")
        except ValueError:
            frappe.throw("Invalid appointment time slot.")

        appointment_datetime = get_datetime(
            f"{getdate(self.appointment_date)} {appointment_time}"
        )

        if appointment_datetime < now_datetime():
            frappe.throw("Appointment date and time cannot be in the past.")

        # Prevent booking an already occupied doctor/time slot.
        existing = frappe.db.exists(
            "Doctor Appointment",
            {
                "doctor": self.doctor,
                "appointment_date": self.appointment_date,
                "appointment_time": appointment_time,
                "appointment_status": ["!=", "Cancelled"]
            }
        )

        if existing:
            frappe.throw(
                "This time slot is already booked. Please choose another slot."
            )

    def after_insert(self):

        # Only process submissions from the public Web Form.
        if not frappe.flags.in_web_form:
            return

        patient = self.get_or_create_patient()

        appointment_time = datetime.strptime(
            self.appointment_time, "%I:%M %p"
        ).strftime("%H:%M:%S")

        # Create the official Doctor Appointment.
        appointment = frappe.new_doc("Doctor Appointment")

        appointment.patient = patient.name
        appointment.appointment_date = self.appointment_date
        appointment.appointment_time = appointment_time
        appointment.appointment_type = self.appointment_type
        appointment.department = self.department
        appointment.doctor = self.doctor
        appointment.reason_for_visit = self.reason_for_visit
        appointment.appointment_status = "Confirmed"
        appointment.payment_status = "Not Billed"

        # Existing Doctor Appointment validation will:
        # - Check the date and time.
        # - Check doctor availability.
        # - Prevent duplicate bookings.
        # - Automatically fetch the consultation fee.
        appointment.insert(ignore_permissions=True)

        # Link the generated appointment to the booking record.
        self.db_set(
            "doctor_appointment",
            appointment.name,
            update_modified=False
        )

    def get_or_create_patient(self):

        mobile = self.mobile_number.strip()

        matches = frappe.get_all(
            "Patient",
            filters={"mobile_number": mobile},
            fields=["name"],
            limit=2
        )

        if len(matches) > 1:
            frappe.throw(
                "Multiple patient records use this mobile number. "
                "Please contact the hospital."
            )

        if matches:
            patient = frappe.get_doc("Patient", matches[0].name)

            # Avoid accidentally linking a family member's record.
            if (
                patient.patient_name.strip().casefold()
                != self.patient_name.strip().casefold()
                or getdate(patient.date_of_birth)
                != getdate(self.date_of_birth)
            ):
                frappe.throw(
                    "This mobile number is already registered to another "
                    "patient. Please contact the hospital."
                )

            if not patient.is_active:
                frappe.throw("This patient record is inactive.")

            if not patient.customer:
                customer = self.create_customer(patient.patient_name)
                patient.customer = customer.name
                patient.save(ignore_permissions=True)

            return patient

        # Create an ERPNext Customer for the new patient.
        customer = self.create_customer(self.patient_name)

        # Create the new Patient record.
        patient = frappe.new_doc("Patient")

        patient.patient_name = self.patient_name
        patient.date_of_birth = self.date_of_birth
        patient.gender = self.gender
        patient.mobile_number = mobile
        patient.email = self.email
        patient.allergy_status = "Not Assessed"
        patient.is_active = 1
        patient.customer = customer.name

        patient.insert(ignore_permissions=True)

        return patient

    def create_customer(self, customer_name):

        customer = frappe.new_doc("Customer")

        customer.customer_name = customer_name
        customer.customer_type = "Individual"
        customer.customer_group = "Individual"
        customer.territory = "India"

        customer.insert(ignore_permissions=True)

        return customer
@frappe.whitelist(allow_guest=True)
def get_active_doctors_for_department(department):

    if not department:
        return []

    if not frappe.db.exists("Hospital Department", department):
        return []

    doctors = frappe.get_all(
        "Doctor",
        filters={
            "department": department,
            "is_active": 1
        },
        fields=["name", "doctor_name"],
        order_by="doctor_name asc",
        limit=100
    )

    return [
        {
            "label": doctor.doctor_name,
            "value": doctor.name
        }
        for doctor in doctors
    ]