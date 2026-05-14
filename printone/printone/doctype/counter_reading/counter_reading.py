# Copyright (c) 2026, Mohanraj and contributors
# For license information, please see license.txt

import math

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, add_days


class CounterReading(Document):

    def validate(self):

        # Initialize previous consumption variables
        prev_bnw_consumption = 0
        prev_color_consumption = 0
        prev_bnw_consumption_a3 = 0
        prev_color_consumption_a3 = 0
        prev_bnw_consumption_a5 = 0
        prev_color_consumption_a5 = 0

        # Ensure reading counts are numbers
        self.bnw_count = self.bnw_count or 0
        self.color_count = self.color_count or 0
        self.current_bnw_readinga3 = self.current_bnw_readinga3 or 0
        self.current_color_readinga3 = self.current_color_readinga3 or 0
        self.current_bnw_readinga5 = self.current_bnw_readinga5 or 0
        self.current_color_readinga5 = self.current_color_readinga5 or 0

        # Validate reading date
        if not self.reading_date:
            frappe.throw("Please select a Reading Date before saving.")

        try:
            current_read_date = getdate(self.reading_date)
        except Exception:
            frappe.throw(f"Invalid Reading Date: {self.reading_date}")

        # ✅ Amended flow
        if self.amended_from:
            cancelled_doc = frappe.get_doc("Counter Reading", self.amended_from)
            cancelled_reading_date = cancelled_doc.reading_date

            previous_read_record = frappe.get_all(
                "Counter Reading",
                filters={
                    "customer": self.customer,
                    "docstatus": 1,
                    "reading_date": ["<", cancelled_reading_date],
                    "name": ["!=", self.amended_from]
                },
                fields=[
                    "reading_date", "bnw_count", "color_count",
                    "bnw_consumption", "color_consumption",
                    "current_bnw_readinga3", "current_color_readinga3",
                    "current_bnw_consumption_a3", "current_color_consumption_a3",
                    "current_bnw_readinga5", "current_color_readinga5",
                    "current_bnw_consumptiona5", "current_color_consumptiona5"
                ],
                order_by="reading_date desc",
                limit=1
            )

        else:
            # ✅ Normal flow
            previous_read_record = frappe.get_all(
                "Counter Reading",
                filters={
                    "customer": self.customer,
                    "docstatus": 1,
                    "reading_date": ["<", self.reading_date],
                    "amended_from": ["is", "not set"]
                },
                fields=[
                    "reading_date", "bnw_count", "color_count",
                    "bnw_consumption", "color_consumption",
                    "current_bnw_readinga3", "current_color_readinga3",
                    "current_bnw_consumption_a3", "current_color_consumption_a3",
                    "current_bnw_readinga5", "current_color_readinga5",
                    "current_bnw_consumptiona5", "current_color_consumptiona5"
                ],
                order_by="reading_date desc",
                limit=1
            )

        # ✅ Get previous record details
        if previous_read_record:
            prev_rec = previous_read_record[0]
            prev_date = getdate(prev_rec.reading_date)
            prev_bnw = prev_rec.bnw_count or 0
            prev_color = prev_rec.color_count or 0
            prev_bnw_consumption = prev_rec.bnw_consumption or 0
            prev_color_consumption = prev_rec.color_consumption or 0
            prev_bnw_consumption_a3 = prev_rec.current_bnw_consumption_a3 or 0
            prev_color_consumption_a3 = prev_rec.current_color_consumption_a3 or 0
            prev_bnw_consumption_a5 = prev_rec.current_bnw_consumptiona5 or 0
            prev_color_consumption_a5 = prev_rec.current_color_consumptiona5 or 0

            opening_date = add_days(prev_date, 1)

            if not self.opening_date:
                self.opening_date = opening_date

            if current_read_date < opening_date:
                frappe.throw(
                    f"Current reading date ({self.reading_date}) must be on or after opening date ({opening_date})"
                )

            days = date_diff(current_read_date, prev_date)
            if days < 25:
                frappe.throw(
                    f"At least 25 days is required, since the last reading. Currently, only {days} days have passed."
                )

        else:
            prev_date = None
            prev_bnw = 0
            prev_color = 0
            days = 0
            self.opening_date = self.reading_date

        # ✅ Validate reading counts not decreasing
        if self.bnw_count <= prev_bnw:
            frappe.throw(f"BnW reading ({self.bnw_count}) must be higher than previous ({prev_bnw})")
        if self.color_count <= prev_color:
            frappe.throw(f"Color reading ({self.color_count}) must be higher than previous ({prev_color})")

        # ✅ A4 consumption
        bnw_used = self.bnw_count - prev_bnw
        color_used = self.color_count - prev_color

        # ✅ A3 consumption
        if previous_read_record:
            prev_bnw_a3 = prev_rec.current_bnw_readinga3 or 0
            prev_color_a3 = prev_rec.current_color_readinga3 or 0
            bnw_used_a3 = (self.current_bnw_readinga3 - prev_bnw_a3) * 2
            color_used_a3 = (self.current_color_readinga3 - prev_color_a3) * 2
        else:
            bnw_used_a3 = self.current_bnw_readinga3 * 2
            color_used_a3 = self.current_color_readinga3 * 2

        bnw_used_a3 = max(0, bnw_used_a3)
        color_used_a3 = max(0, color_used_a3)

        # ✅ A5 consumption
        if previous_read_record:
            prev_bnw_a5 = prev_rec.current_bnw_readinga5 or 0
            prev_color_a5 = prev_rec.current_color_readinga5 or 0
            bnw_used_a5 = (self.current_bnw_readinga5 - prev_bnw_a5) / 2
            color_used_a5 = (self.current_color_readinga5 - prev_color_a5) / 2
        else:
            bnw_used_a5 = self.current_bnw_readinga5 / 2
            color_used_a5 = self.current_color_readinga5 / 2

        bnw_used_a5 = max(0, bnw_used_a5)
        color_used_a5 = max(0, color_used_a5)

        # ✅ Store consumption values
        self.bnw_consumption = bnw_used
        self.color_consumption = color_used
        self.current_bnw_consumption_a3 = bnw_used_a3
        self.current_color_consumption_a3 = color_used_a3
        self.current_bnw_consumptiona5 = bnw_used_a5
        self.current_color_consumptiona5 = color_used_a5

        # ✅ Store previous readings
        self.previous_bnw = prev_bnw
        self.previous_color = prev_color
        self.previous_reading_date = prev_date

        # ✅ Store previous consumption values
        self.previous_bnw_consumptiona4 = prev_bnw_consumption
        self.previous_color_consumptiona4 = prev_color_consumption
        self.previous_bnw_consumptiona3 = prev_bnw_consumption_a3
        self.previous_color_consumptiona3 = prev_color_consumption_a3
        self.previous_bnw_consumptiona5 = prev_bnw_consumption_a5
        self.previous_color_consumptiona5 = prev_color_consumption_a5

        # ✅ Fetch contract
        contract = frappe.get_doc("Printer Contract", self.contract)
        is_combined = contract.combined or 0

        # ✅ Total consumption
        total_bnw = bnw_used + bnw_used_a3 + bnw_used_a5
        total_color = color_used + color_used_a3 + color_used_a5

        if is_combined:
            # ============================================================
            # COMBINED BILLING
            # ============================================================
            free_combined = contract.combined_free_copies or 0
            combined_rate = contract.combined_excess_rate or 0

            if not previous_read_record or days >= 30:
                allowed_combined = free_combined
            else:
                prorated_combined = (free_combined / 30) * days
                allowed_combined = math.floor(prorated_combined)

            total_all = total_bnw + total_color
            combined_billable = max(0, total_all - allowed_combined)

            # Split combined billable — BnW & Color proportion
            if total_all > 0 and combined_billable > 0:
                bnw_combined_billable = int(combined_billable * (total_bnw / total_all))
                color_combined_billable = int(combined_billable) - bnw_combined_billable
            else:
                bnw_combined_billable = 0
                color_combined_billable = 0

            combined_amount = max(0, combined_billable * combined_rate)

            self.prorated_combined_free_copies = allowed_combined
            self.excess_combined_billable_consumption = int(combined_billable)
            self.excess_combined_amount = combined_amount

            # Store split for invoice
            self.bnw_combined_billable = bnw_combined_billable
            self.color_combined_billable = color_combined_billable

            # Clear normal billing fields
            self.prorated_bnw = 0
            self.prorated_color = 0
            self.bnw_billable = 0
            self.color_billable = 0
            self.a4_bnw_billable = 0
            self.a3_bnw_billable = 0
            self.a5_bnw_billable = 0
            self.a4_color_billable = 0
            self.a3_color_billable = 0
            self.a5_color_billable = 0

        else:
            # ============================================================
            # NORMAL BILLING
            # ============================================================
            free_bnw = contract.monthly_free_copies_bnw or 0
            free_color = contract.monthly_free_copies_color or 0
            bnw_rate = contract.extra_rate_bnw or 0
            color_rate = contract.extra_rate_color or 0

            if not previous_read_record or days >= 30:
                allowed_bnw_calc = free_bnw
                allowed_color_calc = free_color
                prorated_bnw = 0
                prorated_color = 0
            else:
                prorated_bnw = (free_bnw / 30) * days
                prorated_color = (free_color / 30) * days
                allowed_bnw_calc = prorated_bnw
                allowed_color_calc = prorated_color

            self.prorated_bnw = round(prorated_bnw, 3)
            self.prorated_color = round(prorated_color, 3)

            # ✅ BnW billable breakdown
            bnw_billable_total = max(0, total_bnw - allowed_bnw_calc)

            if total_bnw > 0 and bnw_billable_total > 0:
                a4_bnw_billable = int(bnw_billable_total * (bnw_used / total_bnw))
                a3_bnw_billable = int(bnw_billable_total * (bnw_used_a3 / total_bnw))
                a5_bnw_billable = int(bnw_billable_total) - a4_bnw_billable - a3_bnw_billable
            else:
                a4_bnw_billable = 0
                a3_bnw_billable = 0
                a5_bnw_billable = 0

            self.bnw_billable = int(bnw_billable_total)
            self.a4_bnw_billable = int(a4_bnw_billable)
            self.a3_bnw_billable = int(a3_bnw_billable)
            self.a5_bnw_billable = int(a5_bnw_billable)

            # ✅ Color billable breakdown
            color_billable_total = max(0, total_color - allowed_color_calc)

            if total_color > 0 and color_billable_total > 0:
                a4_color_billable = int(color_billable_total * (color_used / total_color))
                a3_color_billable = int(color_billable_total * (color_used_a3 / total_color))
                a5_color_billable = int(color_billable_total) - a4_color_billable - a3_color_billable
            else:
                a4_color_billable = 0
                a3_color_billable = 0
                a5_color_billable = 0

            self.color_billable = math.floor(color_billable_total)
            self.a4_color_billable = int(a4_color_billable)
            self.a3_color_billable = int(a3_color_billable)
            self.a5_color_billable = int(a5_color_billable)

            # Clear combined billing fields
            self.prorated_combined_free_copies = 0
            self.excess_combined_billable_consumption = 0
            self.excess_combined_amount = 0
            self.bnw_combined_billable = 0
            self.color_combined_billable = 0


    def on_submit(self):
        self.generate_invoice()


    def generate_invoice(self):

        contract_doc = frappe.get_doc("Printer Contract", self.contract)
        is_combined = contract_doc.combined or 0

        if is_combined:
            # ============================================================
            # COMBINED INVOICE
            # ============================================================

            # Avoid duplicate
            if self.combined_invoice:
                frappe.msgprint(f"Combined Invoice already created: {self.combined_invoice}")
                return

            if (self.excess_combined_billable_consumption or 0) <= 0:
                frappe.msgprint("No billable copies to invoice.")
                return

            # Recalculate split from actual consumption
            total_bnw = (self.bnw_consumption or 0) + (self.current_bnw_consumption_a3 or 0) + (self.current_bnw_consumptiona5 or 0)
            total_color = (self.color_consumption or 0) + (self.current_color_consumption_a3 or 0) + (self.current_color_consumptiona5 or 0)
            total_all = total_bnw + total_color
            combined_billable = int(self.excess_combined_billable_consumption or 0)

            if total_all > 0 and combined_billable > 0:
                bnw_qty = int(combined_billable * (total_bnw / total_all))
                color_qty = combined_billable - bnw_qty
            else:
                bnw_qty = 0
                color_qty = 0

            # BnW description split
            if total_bnw > 0 and bnw_qty > 0:
                a4_bnw_desc = int(bnw_qty * ((self.bnw_consumption or 0) / total_bnw))
                a3_bnw_desc = int(bnw_qty * ((self.current_bnw_consumption_a3 or 0) / total_bnw))
                a5_bnw_desc = bnw_qty - a4_bnw_desc - a3_bnw_desc
            else:
                a4_bnw_desc = a3_bnw_desc = a5_bnw_desc = 0

            # Color description split
            if total_color > 0 and color_qty > 0:
                a4_color_desc = int(color_qty * ((self.color_consumption or 0) / total_color))
                a3_color_desc = int(color_qty * ((self.current_color_consumption_a3 or 0) / total_color))
                a5_color_desc = color_qty - a4_color_desc - a3_color_desc
            else:
                a4_color_desc = a3_color_desc = a5_color_desc = 0

            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": self.customer,
                "posting_date": self.reading_date,
                "due_date": None,
                "items": []
            })

            invoice.custom_opening_date = self.opening_date

            if bnw_qty > 0:
                invoice.append("items", {
                    "item_code": "A4 BnW",
                    "description": (
                        f"Additional Combined Print BnW — "
                        f"A4 BnW({a4_bnw_desc}), "
                        f"A3 BnW({a3_bnw_desc}), "
                        f"A5 BnW({a5_bnw_desc})"
                    ),
                    "qty": bnw_qty,
                    "rate": contract_doc.combined_excess_rate
                })

            if color_qty > 0:
                invoice.append("items", {
                    "item_code": "A4 Color",
                    "description": (
                        f"Additional Combined Print Color — "
                        f"A4 Color({a4_color_desc}), "
                        f"A3 Color({a3_color_desc}), "
                        f"A5 Color({a5_color_desc})"
                    ),
                    "qty": color_qty,
                    "rate": contract_doc.combined_excess_rate
                })

            invoice.insert()
            invoice.save()

            self.combined_invoice = invoice.name
            self.db_update()

            frappe.msgprint(f"Combined Invoice {invoice.name} created successfully")

        else:
            # ============================================================
            # NORMAL INVOICE
            # ============================================================

            # Avoid duplicate
            if self.invoice:
                frappe.msgprint(f"Invoice already created: {self.invoice}")
                return

            if (self.bnw_billable or 0) <= 0 and (self.color_billable or 0) <= 0:
                frappe.msgprint("No billable copies to invoice.")
                return

            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": self.customer,
                "posting_date": self.reading_date,
                "due_date": None,
                "items": []
            })

            invoice.custom_opening_date = self.opening_date

            if self.bnw_billable > 0:
                invoice.append("items", {
                    "item_code": "A4 BnW",
                    "description": (
                        f"Additional Print A4 BnW({self.a4_bnw_billable}), "
                        f"A3 BnW({self.a3_bnw_billable}), "
                        f"A5 BnW({self.a5_bnw_billable})"
                    ),
                    "qty": self.bnw_billable,
                    "rate": contract_doc.extra_rate_bnw
                })

            if self.color_billable > 0:
                invoice.append("items", {
                    "item_code": "A4 Color",
                    "description": (
                        f"Additional Print A4 Color({self.a4_color_billable}), "
                        f"A3 Color({self.a3_color_billable}), "
                        f"A5 Color({self.a5_color_billable})"
                    ),
                    "qty": self.color_billable,
                    "rate": contract_doc.extra_rate_color
                })

            invoice.insert()
            invoice.save()

            self.invoice = invoice.name
            self.db_update()

            frappe.msgprint(f"Invoice {invoice.name} created successfully")