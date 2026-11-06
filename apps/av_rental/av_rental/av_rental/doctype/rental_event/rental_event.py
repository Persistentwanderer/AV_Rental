import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from av_rental import domain


class RentalEvent(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Rental Events are append-only and cannot be edited")
        if not self.actor:
            self.actor = frappe.session.user
        if not self.event_timestamp:
            self.event_timestamp = now_datetime()
        if not self.batch_id:
            self.batch_id = frappe.generate_hash(length=16)
        if not self.scope:
            self.scope = "Line"
        if not self.rental_line:
            frappe.throw("A hire event names the rental line it changes")
        line = frappe.db.get_value(
            "Rental Line",
            self.rental_line,
            ["name", "gear_list", "rental_project", "item_code", "qty", "planned_out", "planned_in"],
            as_dict=True,
        )
        if not line:
            frappe.throw("Rental Line was not found")
        prior = frappe.get_all(
            "Rental Event",
            filters={"rental_line": self.rental_line, "name": ["!=", self.name]},
            fields=["rental_line", "event_type", "qty", "extended_until"],
        )
        try:
            normalised = domain.validate_event(
                line,
                prior,
                {
                    "event_type": self.event_type,
                    "qty": self.qty,
                    "reason": self.reason,
                    "actor": self.actor,
                    "event_timestamp": self.event_timestamp,
                    "extended_until": self.extended_until,
                    "batch_id": self.batch_id,
                    "scope": self.scope,
                },
            )
        except domain.DomainError as exc:
            frappe.throw(str(exc), frappe.ValidationError)
        self.gear_list = normalised["gear_list"]
        self.rental_project = normalised["rental_project"]
        self.qty = normalised["qty"]
        self.extended_until = normalised["extended_until"]
        when = ""
        if normalised["extended_until"]:
            when = " until " + normalised["extended_until"].strftime("%Y-%m-%d %H:%M")
        self.subject = f"{self.event_type} {self.qty:g} {line.item_code}{when}"

    def before_save(self):
        if not self.is_new():
            frappe.throw("Rental Events are append-only and cannot be edited")

    def on_update(self):
        if not self.flags.in_insert:
            frappe.throw("Rental Events are append-only and cannot be edited")

    def on_trash(self):
        frappe.throw("Rental Events cannot be deleted")

    def after_insert(self):
        # Owning list only. Callers that acted on a parent list refresh that subtree themselves.
        from av_rental.api import refresh_statuses

        if self.rental_project and self.gear_list:
            refresh_statuses(self.rental_project, [self.gear_list])
