# Copyright (c) 2026, Mohanraj and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff


class CounterReading(Document):

    def validate(self):

        prev_bnw_consumption = 0
        prev_color_consumption = 0
        prev_bnw_consumption_a4 = 0
        prev_color_consumption_a4 = 0


        # Ensure reading counts are numbers
        self.bnw_count = self.bnw_count or 0
        self.color_count = self.color_count or 0


        # Validate current reading date exists
        if not self.reading_date:
            frappe.throw("Please select a Reading Date before saving.")

        # get the current reading date
        try:
            current_read_date = getdate(self.reading_date)
        
        except Exception:
            frappe.throw(f"Invalid Reading Date: {self.reading_date}")

        # Fetch the latest previous printer reading record for this customer
        # Exclude the current document to avoid false positives
        filters = {"customer": self.customer}
        if not self.is_new():
            filters["name"] = ["!=", self.name]

        previous_read_record = frappe.get_all(
            "Counter Reading",
            filters=filters,
            fields=["reading_date", "bnw_count", "color_count","bnw_consumption","color_consumption"],
            order_by="reading_date desc",
            limit=1
        )

        # get previous record details
        if previous_read_record:
            prev_rec = previous_read_record[0]
            prev_date = getdate(prev_rec.reading_date)
            prev_bnw = prev_rec.bnw_count or 0
            prev_color = prev_rec.color_count or 0
            prev_bnw_consumption = prev_rec.bnw_consumption or 0
            prev_color_consumption = prev_rec.color_consumption or 0
            # prev_bnw_consumption_a4 = prev_rec.previous_bnw_consumptiona4 or 0
            # prev_color_consumption_a4 = prev_rec.previous_color_consumptiona4 or 0


            # Ensure current date is strictly after previous
            if current_read_date <= getdate(self.previous_reading_date):#self.prev_date:
                frappe.throw(
                    f"Current printer reading date ({self.reading_date}) must be later than previous reading date ({prev_date})"
                )

            # Minimum 25-day interval check
            #days = (current_read_date - prev_date).days
            days = date_diff(current_read_date, getdate(self.previous_reading_date)) 
            if days < 25:
                frappe.throw(
                    f"At least 25 days is required, since the last reading. Currently, only {days} days have passed."
                )

        else:
            # First reading entry, no previous reading
            prev_date = None
            prev_bnw = 0
            prev_color = 0
            days = 0

        # Ensure counts do not decrease
        if self.bnw_count <= prev_bnw:
            frappe.throw(f"Bnw reading count {self.bnw_count} should be higher than previous {prev_bnw}")
        if self.color_count <= prev_color:
            frappe.throw(f"Color reading count {self.color_count} should be higher than previous {prev_color}")

        # Calculate used copies
        bnw_used = self.bnw_count - prev_bnw
        color_used = self.color_count - prev_color

        if previous_read_record:
            #check for 10% increase or decrease in count
            prev_bnw_90_percent = prev_bnw_consumption * 0.90
            prev_bnw_110_percent = prev_bnw_consumption * 1.10

            prev_color_90_percent = prev_color_consumption * 0.90
            prev_color_110_percent = prev_color_consumption * 1.10

            if bnw_used < prev_bnw_90_percent:
                frappe.throw(f"BnW Consumption is too low. It should not be less than 90% of previous consumption.")
            elif bnw_used > prev_bnw_110_percent:
                frappe.throw(f"BnW Consumption is too high. It should not exceed 110% of previous consumption.")

            if color_used < prev_color_90_percent:
                frappe.throw("Color Consumption is too low. It should not be less than 90% of previous consumption.")
            elif color_used > prev_color_110_percent:
                frappe.throw("Color Consumption is too high. It should not exceed 110% of previous consumption.")


        # Fetch contract free copies
        contract = frappe.get_doc("Printer Contract", self.contract)
        free_bnw = contract.monthly_free_copies_bnw or 0
        free_color = contract.monthly_free_copies_color or 0

        # Determine allowed copies (full month or prorated)
        if not previous_read_record:
            allowed_bnw = free_bnw
            allowed_color = free_color
            prorated_bnw = 0
            prorated_color = 0

        # Less than 30 or greater than 30 days    
        else:
            prorated_bnw = (free_bnw / 30) * days
            prorated_color = (free_color / 30) * days
            allowed_bnw = prorated_bnw
            allowed_color = prorated_color

        # Save previous readings and consumption
        self.previous_bnw = prev_bnw
        self.previous_color = prev_color
        self.previous_reading_date = prev_date
        self.bnw_consumption = bnw_used
        self.color_consumption = color_used
        self.previous_bnw_consumptiona4 = prev_bnw_consumption
        self.previous_color_consumptiona4 = prev_color_consumption
        self.prorated_bnw = prorated_bnw
        self.prorated_color = prorated_color

        # Calculate billable copies
        self.bnw_billable = int(max(0, bnw_used - allowed_bnw))
        self.color_billable = int(max(0, color_used - allowed_color))

        # Calculate billable amounts
        bnw_rate = contract.extra_rate_bnw or 0
        color_rate = contract.extra_rate_color or 0
        self.bnw_amount = self.bnw_billable * bnw_rate
        self.color_amount = self.color_billable * color_rate

    def on_submit(self):
        self.generate_invoice()

    def generate_invoice(self):
        import frappe

        # Avoid duplicate invoice creation
        if self.invoice:
            frappe.msgprint(f"Invoice already created: {self.invoice}")
            return
        
        #Skip if nothing billable
        if self.bnw_billable <= 0 and self.color_billable <= 0:
            frappe.msgprint("No billable copies to invoice.")
            return
        
        #Get current contract for rates
        contract_doc = frappe.get_doc("Printer Contract", self.contract)
        
        #Create Sales Invoice
        invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": self.customer,
        "posting_date": self.reading_date,
        "due_date": self.reading_date,
        "items": []
          })
        
        # Add BnW item in invoice
        if self.bnw_billable > 0:
            invoice.append("items", {
            "item_code": "A4 Bnw",
            "description": f"Additional Print A4 BnW({self.bnw_billable}), A3 BnW(0)",
            "qty": self.bnw_billable,
            "rate": contract_doc.extra_rate_bnw
        })
        
        #Add Color item in invoice
        if self.color_billable > 0:
            invoice.append("items", {
            "item_code": "A4 Color",
            "description": f"Additional Print A4 Color({self.color_billable}), A3 Color(0)",
            "qty": self.color_billable,
            "rate": contract_doc.extra_rate_color
        })
            
        # Insert and submit invoice  
        invoice.insert()
        invoice.save()

        self.invoice = invoice.name
        self.db_update()
        
        frappe.msgprint(f"Invoice {invoice.name} created successfully")

         #Link invoice safely (important)
            # frappe.db.set_value(self.doctype, self.name, "invoice", invoice.name)