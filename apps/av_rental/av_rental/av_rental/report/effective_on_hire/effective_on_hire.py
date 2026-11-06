import frappe

from av_rental.api import effective_on_hire


def execute(filters=None):
    filters = filters or {}
    project = filters.get("rental_project")
    if not project:
        frappe.msgprint("Choose a Rental Project")
        return [], []
    gear_list = filters.get("gear_list") or None
    payload = effective_on_hire(project, gear_list)
    return payload["columns"], payload["rows"]
