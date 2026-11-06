"""Stop planned baselines from being rewritten once hire events exist."""

from __future__ import annotations

import frappe

from av_rental import domain

_MOMENTS = {"planned_start", "planned_end", "planned_out", "planned_in"}
_NUMBERS = {"qty"}

LOCKED_FIELDS = {
    "Rental Project": ["customer", "company", "planned_start", "planned_end", "warehouse"],
    "Gear List": ["parent_gear_list", "rental_project", "planned_out", "planned_in", "warehouse"],
    "Rental Line": ["gear_list", "rental_project", "item_code", "qty", "planned_out", "planned_in", "warehouse"],
}


def _norm(field: str, value):
    if field in _MOMENTS:
        return domain.parse_dt(value) if value else None
    if field in _NUMBERS:
        return domain.qty(value)
    if value in (None, ""):
        return None
    return value


def has_events(doc) -> bool:
    if doc.doctype == "Rental Project":
        return bool(frappe.db.exists("Rental Event", {"rental_project": doc.name}))
    if doc.doctype == "Rental Line":
        return bool(frappe.db.exists("Rental Event", {"rental_line": doc.name}))
    project = doc.rental_project
    gear_lists = frappe.get_all(
        "Gear List",
        filters={"rental_project": project},
        fields=["name", "parent_gear_list"],
    )
    try:
        names = domain.subtree_names(gear_lists, doc.name)
    except domain.DomainError:
        names = [doc.name]
    return bool(frappe.db.exists("Rental Event", {"gear_list": ["in", names]}))


def lock_baseline(doc):
    """Reject edits to the planned identity after any hire event exists."""
    if doc.is_new():
        return
    before = doc.get_doc_before_save()
    if not before:
        return
    changed = []
    for field in LOCKED_FIELDS[doc.doctype]:
        if _norm(field, before.get(field)) != _norm(field, doc.get(field)):
            changed.append(field)
    if not changed:
        return
    if has_events(doc):
        frappe.throw(
            "The planned baseline stays as recorded. "
            f"Changed: {', '.join(changed)}. "
            "Issue, return, extend, and damage are Rental Events.",
            frappe.ValidationError,
        )


def reject_delete_with_events(doc, label: str):
    if has_events(doc):
        frappe.throw(f"Cannot delete {label} because hire events already record its history")
