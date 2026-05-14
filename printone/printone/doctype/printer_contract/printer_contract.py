# Copyright (c) 2026, Mohanraj and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PrinterContract(Document):

    def validate(self):
        if self.combined:
            self.monthly_free_copies_bnw = 0
            self.monthly_free_copies_color = 0
            self.extra_rate_bnw = 0
            self.extra_rate_color = 0
        else:
            self.combined_free_copies = 0
            self.combined_excess_rate = 0