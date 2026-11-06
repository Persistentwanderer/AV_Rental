import frappe
from frappe.model.document import Document

from av_rental import domain
from av_rental.guards import lock_baseline, reject_delete_with_events


class RentalProject(Document):
    def validate(self):
        start = domain.parse_dt(self.planned_start) if self.planned_start else None
        end = domain.parse_dt(self.planned_end) if self.planned_end else None
        if start and end and end <= start:
            frappe.throw("Planned end must be after planned start")
        lock_baseline(self)

    def on_trash(self):
        reject_delete_with_events(self, "this rental project")
