"""Desk and HTTP actions. Each action appends Rental Event rows."""

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import now_datetime

from av_rental import domain

EVENT_COLUMNS = [
    "name",
    "rental_project",
    "gear_list",
    "rental_line",
    "event_type",
    "scope",
    "qty",
    "event_timestamp",
    "reason",
    "actor",
    "extended_until",
    "batch_id",
]

LINE_COLUMNS = [
    "name",
    "gear_list",
    "rental_project",
    "item_code",
    "item_name",
    "qty",
    "planned_out",
    "planned_in",
]

LIST_COLUMNS = [
    "name",
    "list_name",
    "parent_gear_list",
    "rental_project",
    "list_status",
    "planned_out",
    "planned_in",
    "is_group",
]

REPORT_COLUMNS = [
    {"label": "List Path", "fieldname": "list_path", "fieldtype": "Data", "width": 220},
    {"label": "Gear List", "fieldname": "gear_list_name", "fieldtype": "Data", "width": 140},
    {"label": "Parent List", "fieldname": "parent_gear_list", "fieldtype": "Link", "options": "Gear List", "width": 140},
    {"label": "Line", "fieldname": "rental_line", "fieldtype": "Link", "options": "Rental Line", "width": 150},
    {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
    {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
    {"label": "Planned Qty", "fieldname": "planned_qty", "fieldtype": "Float", "width": 110},
    {"label": "Issued", "fieldname": "issued_qty", "fieldtype": "Float", "width": 90},
    {"label": "Returned", "fieldname": "returned_qty", "fieldtype": "Float", "width": 90},
    {"label": "Damaged", "fieldname": "damaged_qty", "fieldtype": "Float", "width": 90},
    {"label": "On Hire", "fieldname": "on_hire_qty", "fieldtype": "Float", "width": 90},
    {"label": "Planned Out", "fieldname": "planned_out", "fieldtype": "Datetime", "width": 170},
    {"label": "Planned In", "fieldname": "planned_in", "fieldtype": "Datetime", "width": 170},
    {"label": "Effective Expected In", "fieldname": "effective_expected_in", "fieldtype": "Datetime", "width": 180},
]


def has_app_permission() -> bool:
    return bool(frappe.has_permission("Rental Project", "read"))


def _require_event_create():
    if not frappe.has_permission("Rental Event", "create"):
        frappe.throw("Not permitted to record hire events", frappe.PermissionError)


def _as_list(value):
    if isinstance(value, str):
        value = frappe.parse_json(value)
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, (list, tuple)) or not value:
        frappe.throw("Pass at least one line as {rental_line, qty}")
    return list(value)


def _snapshot(project: str):
    if not project or not frappe.db.exists("Rental Project", project):
        frappe.throw(f"Rental Project {project} was not found")
    if not frappe.has_permission("Rental Project", "read", project):
        frappe.throw("Not permitted to read this rental project", frappe.PermissionError)
    gear_lists = frappe.get_all("Gear List", filters={"rental_project": project}, fields=LIST_COLUMNS)
    lines = frappe.get_all("Rental Line", filters={"rental_project": project}, fields=LINE_COLUMNS)
    events = frappe.get_all(
        "Rental Event",
        filters={"rental_project": project},
        fields=EVENT_COLUMNS,
        order_by="event_timestamp asc, creation asc",
    )
    return gear_lists, lines, events


def _project_of_list(gear_list: str) -> str:
    project = frappe.db.get_value("Gear List", gear_list, "rental_project")
    if not project:
        frappe.throw(f"Gear List {gear_list} was not found")
    return project


def _raise_domain(exc: domain.DomainError):
    frappe.throw(str(exc), frappe.ValidationError)


def _stamp_public(value):
    if value is None:
        return None
    parsed = domain.parse_dt(value)
    if parsed is None:
        return None
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


@frappe.whitelist()
def effective_on_hire(rental_project: str, gear_list: str | None = None):
    """Computed on-hire rows for a project, optionally one gear-list subtree."""
    gear_lists, lines, events = _snapshot(rental_project)
    if gear_list:
        allowed = set(domain.subtree_names(gear_lists, gear_list))
        lines = [line for line in lines if line["gear_list"] in allowed]
    rows = []
    for row in domain.effective_rows(gear_lists, lines, events):
        public = dict(row)
        for key in ("planned_out", "planned_in", "effective_expected_in"):
            public[key] = _stamp_public(public.get(key))
        rows.append(public)
    return {"columns": REPORT_COLUMNS, "rows": rows}


def refresh_statuses(project: str, roots: list[str]) -> dict[str, str]:
    """Recompute list_status for each root subtree. Does not save any other list."""
    gear_lists, lines, events = _snapshot(project)
    current = {row["name"]: row.get("list_status") for row in gear_lists}
    merged: dict[str, str] = {}
    for root in roots:
        if not root:
            continue
        merged.update(domain.status_updates(gear_lists, lines, events, root))
    changed = {}
    for name, status in merged.items():
        if current.get(name) != status:
            frappe.db.set_value("Gear List", name, "list_status", status)
            changed[name] = status
    return changed


def _insert_events(planned: list[dict]) -> list[str]:
    names = []
    for event in planned:
        payload = {
            "doctype": "Rental Event",
            "rental_project": event["rental_project"],
            "gear_list": event["gear_list"],
            "rental_line": event["rental_line"],
            "event_type": event["event_type"],
            "scope": event.get("scope") or "Line",
            "qty": event["qty"],
            "event_timestamp": event["event_timestamp"],
            "reason": event["reason"],
            "actor": event["actor"],
            "batch_id": event.get("batch_id"),
        }
        if event.get("extended_until"):
            payload["extended_until"] = event["extended_until"]
        doc = frappe.get_doc(payload)
        doc.insert()
        names.append(doc.name)
    return names


def _apply(project: str, specs: list[dict], event_type: str, reason: str, scope: str, roots: list[str], extended_until=None):
    _require_event_create()
    if not (reason or "").strip():
        frappe.throw("Reason is required")
    gear_lists, lines, events = _snapshot(project)
    lines_by_name = {line["name"]: line for line in lines}
    memory = list(events)
    batch_id = frappe.generate_hash(length=16)
    actor = frappe.session.user
    timestamp = now_datetime()
    planned = []
    allowed_lists = None
    if roots and scope == "Gear List" and len(roots) == 1:
        allowed_lists = set(domain.subtree_names(gear_lists, roots[0]))
    for spec in specs:
        line_name = spec.get("rental_line")
        line = lines_by_name.get(line_name)
        if not line:
            frappe.throw(f"Rental Line {line_name} is not on this project")
        if allowed_lists is not None and line["gear_list"] not in allowed_lists:
            frappe.throw(f"Rental Line {line_name} is outside gear list {roots[0]}")
        try:
            normalised = domain.validate_event(
                line,
                memory,
                {
                    "event_type": event_type,
                    "qty": spec.get("qty"),
                    "reason": reason,
                    "actor": actor,
                    "event_timestamp": timestamp,
                    "extended_until": extended_until,
                    "batch_id": batch_id,
                    "scope": scope,
                },
            )
        except domain.DomainError as exc:
            _raise_domain(exc)
        memory.append(normalised)
        planned.append(normalised)
    if not planned:
        frappe.throw("Nothing to record. Check issued and on-hire quantities.")
    names = _insert_events(planned)
    if not roots:
        roots = sorted({event["gear_list"] for event in planned})
    changed = refresh_statuses(project, roots)
    return {"batch_id": batch_id, "events": names, "statuses": changed}


def _specs_from_lines(lines):
    specs = []
    for row in _as_list(lines):
        if isinstance(row, str):
            row = frappe.parse_json(row)
        specs.append({"rental_line": row.get("rental_line"), "qty": row.get("qty")})
    return specs


def _outstanding_specs(gear_lists, lines, events, root: str):
    allowed = set(domain.subtree_names(gear_lists, root))
    by_line = defaultdict(list)
    for event in events:
        if event.get("rental_line"):
            by_line[event["rental_line"]].append(event)
    specs = []
    for line in lines:
        if line["gear_list"] not in allowed:
            continue
        outstanding = domain.qty(domain.qty(line["qty"]) - domain.issued_qty(by_line.get(line["name"], [])))
        if outstanding > 0:
            specs.append({"rental_line": line["name"], "qty": outstanding})
    return specs


def _on_hire_specs(gear_lists, lines, events, root: str):
    allowed = set(domain.subtree_names(gear_lists, root))
    by_line = defaultdict(list)
    for event in events:
        if event.get("rental_line"):
            by_line[event["rental_line"]].append(event)
    specs = []
    for line in lines:
        if line["gear_list"] not in allowed:
            continue
        on_hire = domain.on_hire_qty(by_line.get(line["name"], []))
        if on_hire > 0:
            specs.append({"rental_line": line["name"], "qty": on_hire})
    return specs


@frappe.whitelist()
def issue_gear_list(gear_list: str, reason: str):
    """Issue every still-unissued quantity on this list and its child lists."""
    project = _project_of_list(gear_list)
    gear_lists, lines, events = _snapshot(project)
    try:
        specs = _outstanding_specs(gear_lists, lines, events, gear_list)
    except domain.DomainError as exc:
        _raise_domain(exc)
    return _apply(project, specs, domain.EVENT_ISSUE, reason, "Gear List", [gear_list])


@frappe.whitelist()
def issue_lines(lines, reason: str, gear_list: str | None = None):
    """Issue explicit quantities. Pass gear_list to keep the action inside that subtree."""
    specs = _specs_from_lines(lines)
    project = _project_for_specs(specs, gear_list)
    scope = "Gear List" if gear_list else "Line"
    roots = [gear_list] if gear_list else []
    return _apply(project, specs, domain.EVENT_ISSUE, reason, scope, roots)


@frappe.whitelist()
def partial_return(lines, reason: str, gear_list: str | None = None):
    """Return part of what is on hire. Sibling lists are not candidates when gear_list is set."""
    specs = _specs_from_lines(lines)
    project = _project_for_specs(specs, gear_list)
    scope = "Gear List" if gear_list else "Line"
    roots = [gear_list] if gear_list else []
    return _apply(project, specs, domain.EVENT_RETURN, reason, scope, roots)


@frappe.whitelist()
def record_damage(lines, reason: str, gear_list: str | None = None):
    """Record a damage incident against explicit lines. Damage does not take gear off hire."""
    specs = _specs_from_lines(lines)
    project = _project_for_specs(specs, gear_list)
    scope = "Gear List" if gear_list else "Line"
    roots = [gear_list] if gear_list else []
    return _apply(project, specs, domain.EVENT_DAMAGE, reason, scope, roots)


@frappe.whitelist()
def extend_gear_list(gear_list: str, extended_until: str, reason: str):
    """Extend every on-hire line in this list and its children. The planned window stays."""
    project = _project_of_list(gear_list)
    gear_lists, lines, events = _snapshot(project)
    try:
        specs = _on_hire_specs(gear_lists, lines, events, gear_list)
    except domain.DomainError as exc:
        _raise_domain(exc)
    return _apply(
        project,
        specs,
        domain.EVENT_EXTEND,
        reason,
        "Gear List",
        [gear_list],
        extended_until=extended_until,
    )


@frappe.whitelist()
def extend_lines(lines, extended_until: str, reason: str, gear_list: str | None = None):
    specs = _specs_from_lines(lines)
    project = _project_for_specs(specs, gear_list)
    scope = "Gear List" if gear_list else "Line"
    roots = [gear_list] if gear_list else []
    return _apply(project, specs, domain.EVENT_EXTEND, reason, scope, roots, extended_until=extended_until)


def _project_for_specs(specs, gear_list: str | None) -> str:
    if gear_list:
        return _project_of_list(gear_list)
    first = specs[0]["rental_line"]
    project = frappe.db.get_value("Rental Line", first, "rental_project")
    if not project:
        frappe.throw(f"Rental Line {first} was not found")
    return project


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def rental_line_link_query(doctype, txt, searchfield, start, page_len, filters):
    """Link search limited to a gear list subtree, so a truck dialog cannot pick its sibling."""
    filters = filters or {}
    gear_list = filters.get("gear_list")
    if not gear_list:
        return []
    project = _project_of_list(gear_list)
    gear_lists, _lines, _events = _snapshot(project)
    try:
        names = domain.subtree_names(gear_lists, gear_list)
    except domain.DomainError:
        return []
    return frappe.db.sql(
        """
        select name, item_code, item_name
        from `tabRental Line`
        where gear_list in %(names)s
          and (
            name like %(txt)s
            or item_code like %(txt)s
            or ifnull(item_name, '') like %(txt)s
          )
        order by item_code asc
        limit %(page_len)s offset %(start)s
        """,
        {
            "names": tuple(names),
            "txt": f"%{txt}%",
            "page_len": page_len,
            "start": start,
        },
    )
