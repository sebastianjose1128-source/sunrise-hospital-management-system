import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, nowtime

from erpnext.stock.doctype.batch.batch import get_batch_qty


def update_admission_medicine_charges(admission_name):
    """
    Calculate medicine charges from all submitted Medicine Usage records
    and update the related Patient Admission.
    """

    if not admission_name:
        return

    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(total_medicine_charges), 0)
        FROM `tabMedicine Usage`
        WHERE patient_admission = %s
        AND docstatus = 1
        """,
        (admission_name,),
        as_list=True
    )

    total_medicine = flt(result[0][0])

    admission = frappe.get_doc(
        "Patient Admission",
        admission_name
    )

    total_admission = (
        flt(admission.total_room_charges)
        + flt(admission.treatment_charges)
        + total_medicine
    )

    frappe.db.set_value(
        "Patient Admission",
        admission_name,
        {
            "medicine_charges": total_medicine,
            "total_admission_charges": total_admission
        },
        update_modified=False
    )


class MedicineUsage(Document):

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    def validate(self):
        self.set_default_values()
        self.validate_admission()
        self.fetch_patient_and_doctor()
        self.validate_usage_date()
        self.validate_item()
        self.validate_warehouse()
        self.validate_batch()
        self.validate_qty()
        self.validate_available_stock()

    def set_default_values(self):
        if not self.usage_date:
            self.usage_date = nowdate()

    def validate_admission(self):
        if not self.patient_admission:
            frappe.throw(_("Please select a Patient Admission."))

        admission = frappe.get_doc(
            "Patient Admission",
            self.patient_admission
        )

        if admission.admission_status != "Admitted":
            frappe.throw(
                _("Medicine can only be issued for an active admission.")
            )

    def fetch_patient_and_doctor(self):
        admission = frappe.get_doc(
            "Patient Admission",
            self.patient_admission
        )

        self.patient = admission.patient
        self.doctor = admission.doctor

    def validate_usage_date(self):
        admission_date = frappe.db.get_value(
            "Patient Admission",
            self.patient_admission,
            "admission_date"
        )

        if getdate(self.usage_date) < getdate(admission_date):
            frappe.throw(
                _("Usage date cannot be before the admission date.")
            )

        if getdate(self.usage_date) > getdate(nowdate()):
            frappe.throw(
                _("Usage date cannot be in the future.")
            )

    def validate_item(self):
        if not self.item_code:
            frappe.throw(_("Please select a medicine."))

        item = frappe.get_doc("Item", self.item_code)

        if item.disabled:
            frappe.throw(_("This medicine is disabled."))

        if not item.is_stock_item:
            frappe.throw(_("Please select a stock item."))

        if not item.has_batch_no:
            frappe.throw(
                _("The selected medicine must have batch tracking enabled.")
            )

    def validate_warehouse(self):
        if not self.warehouse:
            frappe.throw(_("Please select a warehouse."))

        warehouse = frappe.db.get_value(
            "Warehouse",
            self.warehouse,
            ["company", "is_group"],
            as_dict=True
        )

        if not warehouse:
            frappe.throw(_("Selected warehouse does not exist."))

        if warehouse.is_group:
            frappe.throw(
                _("Please select an actual warehouse, not a warehouse group.")
            )

    def validate_batch(self):
        if not self.batch_no:
            frappe.throw(_("Please select a medicine batch."))

        batch = frappe.db.get_value(
            "Batch",
            self.batch_no,
            ["item", "expiry_date", "disabled"],
            as_dict=True
        )

        if not batch:
            frappe.throw(_("Selected batch does not exist."))

        if batch.item != self.item_code:
            frappe.throw(
                _("The selected batch does not belong to this medicine.")
            )

        if batch.disabled:
            frappe.throw(_("This medicine batch is disabled."))

        if batch.expiry_date:
            if getdate(self.usage_date) > getdate(batch.expiry_date):
                frappe.throw(
                    _("The selected medicine batch has expired.")
                )

    def validate_qty(self):
        if flt(self.qty) <= 0:
            frappe.throw(
                _("Medicine quantity must be greater than zero.")
            )

    def validate_available_stock(self):
        available_qty = get_batch_qty(
            batch_no=self.batch_no,
            warehouse=self.warehouse,
            item_code=self.item_code,
            posting_date=self.usage_date,
            posting_time=nowtime()
        )

        if flt(self.qty) > flt(available_qty):
            frappe.throw(
                _(
                    "Insufficient batch stock. Available: {0}, Requested: {1}"
                ).format(
                    available_qty,
                    self.qty
                )
            )

    # -----------------------------------------
    # STOCK ENTRY CREATION
    # -----------------------------------------

    def create_stock_entry(self):
        """
        Create and submit an ERPNext Material Issue Stock Entry.
        """

        company = frappe.db.get_value(
            "Warehouse",
            self.warehouse,
            "company"
        )

        if not company:
            frappe.throw(
                _("The selected warehouse has no company assigned.")
            )

        company_doc = frappe.get_doc(
            "Company",
            company
        )

        # Get medicine-specific COGS account
        expense_account = frappe.db.get_value(
            "Item Default",
            {
                "parent": self.item_code,
                "company": company
            },
            "default_cogs_account"
        )

        if not expense_account:
            frappe.throw(
                _("Please configure a default COGS account for this medicine.")
            )

        if not company_doc.cost_center:
            frappe.throw(
                _("Please configure the default cost center for the company.")
            )

        item = frappe.get_doc(
            "Item",
            self.item_code
        )

        # Create Stock Entry document
        stock_entry = frappe.new_doc("Stock Entry")

        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.company = company
        stock_entry.posting_date = self.usage_date
        stock_entry.set_posting_time = 1
        stock_entry.posting_time = nowtime()

        stock_entry.remarks = (
            f"Medicine Usage {self.name} "
            f"for Patient Admission {self.patient_admission}"
        )

        # Add medicine item
        stock_entry.append(
            "items",
            {
                "item_code": self.item_code,
                "qty": self.qty,
                "uom": item.stock_uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": 1,

                "s_warehouse": self.warehouse,

                "batch_no": self.batch_no,
                "use_serial_batch_fields": 1,

                "expense_account": expense_account,
                "cost_center": company_doc.cost_center
            }
        )

        # Calculate stock quantity and valuation
        stock_entry.set_missing_values()

        # Insert and submit Stock Entry
        stock_entry.flags.ignore_permissions = True
        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

        # Get actual valuation from ERPNext
        issued_item = stock_entry.items[0]

        medicine_rate = flt(issued_item.basic_rate)
        medicine_amount = flt(issued_item.basic_amount)

        # Update Medicine Usage document
        self.db_set(
            {
                "stock_entry": stock_entry.name,
                "rate": medicine_rate,
                "total_medicine_charges": medicine_amount
            },
            update_modified=False
        )

        return stock_entry.name

    # -----------------------------------------
    # SUBMIT WORKFLOW
    # -----------------------------------------

    def on_submit(self):
        """
        Automatically issue medicine when Medicine Usage is submitted.
        """

        self.create_stock_entry()

        update_admission_medicine_charges(
            self.patient_admission
        )

    # -----------------------------------------
    # CANCEL WORKFLOW
    # -----------------------------------------

    def on_cancel(self):
        """
        Cancel the linked Stock Entry and restore stock.
        """

        if self.stock_entry:
            stock_entry = frappe.get_doc(
                "Stock Entry",
                self.stock_entry
            )

            stock_entry.flags.ignore_permissions = True

            if stock_entry.docstatus == 1:
                stock_entry.cancel()

            elif stock_entry.docstatus == 0:
                stock_entry.delete(ignore_permissions=True)

        # Recalculate admission charges
        update_admission_medicine_charges(
            self.patient_admission
        )