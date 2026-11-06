import frappe
from frappe.model.document import Document

from av_rental import domain
from av_rental.guards import lock_baseline, reject_delete_with_events


class GearList(Document):
    def validate(self):
        start = domain.parse_dt(self.planned_out) if self.planned_out else None
        end = domain.parse_dt(self.planned_in) if self.planned_in else None
        if start and end and end <= start:
            frappe.throw("Planned in must be after planned out")
        self._parent_in_same_project()
        self._unique_name()
        lock_baseline(self)

    def on_trash(self):
        if frappe.db.exists("Gear List", {"parent_gear_list": self.name}):
            frappe.throw("Remove child gear lists before deleting this one")
        if frappe.db.exists("Rental Line", {"gear_list": self.name}):
            frappe.throw("Remove rental lines before deleting this gear list")
        reject_delete_with_events(self, "this gear list")

    def _parent_in_same_project(self):
        parent = self.parent_gear_list
        if not parent:
            return
        if parent == self.name:
            frappe.throw("A gear list cannot be its own parent")
        parent_project = frappe.db.get_value("Gear List", parent, "rental_project")
        if parent_project and parent_project != self.rental_project:
            frappe.throw("Parent gear list must belong to the same rental project")
        seen = {self.name}
        current = parent
        while current:
            if current in seen:
                frappe.throw("Gear list parent cycle")
            seen.add(current)
            current = frappe.db.get_value("Gear List", current, "parent_gear_list")

    def _unique_name(self):
        existing = frappe.db.exists(
            "Gear List",
            {
                "rental_project": self.rental_project,
                "list_name": self.list_name,
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(f"This project already has a gear list named {self.list_name}")
