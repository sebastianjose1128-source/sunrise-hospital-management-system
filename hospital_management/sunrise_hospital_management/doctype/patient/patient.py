import re

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class Patient(Document):

    def validate(self):
        self.validate_date_of_birth()
        self.validate_contact_numbers()
        self.validate_indian_pincode()
        self.validate_allergy_information()

    def validate_date_of_birth(self):
        if self.date_of_birth:
            if getdate(self.date_of_birth) > getdate():
                frappe.throw("Date of Birth cannot be in the future.")

    def validate_contact_numbers(self):
        phone_fields = {
            "mobile_number": "Mobile Number",
            "alternate_mobile_number": "Alternate Mobile Number",
            "emergency_contact_number": "Emergency Contact Number"
        }

        for fieldname, label in phone_fields.items():
            value = (self.get(fieldname) or "").strip()

            if not value:
                continue

            if not re.fullmatch(r"\+?[0-9\s().-]+", value):
                frappe.throw(
                    f"{label} contains an invalid character."
                )

            digits = re.sub(r"\D", "", value)

            if not 7 <= len(digits) <= 15:
                frappe.throw(
                    f"{label} must contain between 7 and 15 digits."
                )

    def validate_indian_pincode(self):
        if self.country == "India" and self.pincode:
            pincode = self.pincode.strip()

            if not re.fullmatch(r"[1-9][0-9]{5}", pincode):
                frappe.throw(
                    "Indian PIN Code must contain exactly "
                    "6 digits and cannot start with zero."
                )

    def validate_allergy_information(self):
        status = self.allergy_status
        allergies = (self.known_allergies or "").strip()

        if status == "Allergies Reported" and not allergies:
            frappe.throw(
                "Please enter the reported allergies "
                "in the Known Allergies field."
            )

        if status == "No Known Allergies" and allergies:
            frappe.throw(
                "Known Allergies contains information. "
                "Please review the Allergy Status."
            )

        if status == "Not Assessed" and allergies:
            frappe.throw(
                "Allergy information is entered. "
                "Please change Allergy Status to Allergies Reported."
            )
