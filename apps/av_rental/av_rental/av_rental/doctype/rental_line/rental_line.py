import frappe
from frappe.model.document import Document

from av_rental import domain
from av_rental.guards import lock_baseline, reject_delete_with_events


class RentalLine(Document):
    def validate(self):
        if not self.gear_list:
            frappe.throw("Gear List is required")
        gear = frappe.db.get_value(
            "Gear List",
            self.gear_list,
            ["rental_project", "planned_out", "planned_in", "warehouse"],
            as_dict=True,
        )
        if not gear:
            frappe.throw("Gear List was not found")
        if self.rental_project and self.rental_project != gear.rental_project:
            frappe.throw("Rental Line must stay on the gear list's project")
        self.rental_project = gear.rental_project
        if not self.planned_out:
            self.planned_out = gear.planned_out
        if not self.planned_in:
            self.planned_in = gear.planned_in
        if not self.warehouse:
            self.warehouse = gear.warehouse
        if self.item_code:
            item = frappe.db.get_value("Item", self.item_code, ["item_name", "stock_uom"], as_dict=True)
            if item:
                self.item_name = item.item_name
                if not self.uom:
                    self.uom = item.stock_uom
        if domain.qty(self.qty) <= 0:
            frappe.throw("Qty must be positive")
        start = domain.parse_dt(self.planned_out) if self.planned_out else None
        end = domain.parse_dt(self.planned_in) if self.planned_in else None
        if start and end and end <= start:
            frappe.throw("Planned in must be after planned out")
        lock_baseline(self)

    def on_trash(self):
        reject_delete_with_events(self, "this rental line")
