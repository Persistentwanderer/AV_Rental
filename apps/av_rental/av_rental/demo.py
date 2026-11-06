"""Seed the Harbour Lights festival and prove Truck B is untouched by Truck A's incident.

Run inside a site:

    bench --site avrental.localhost execute av_rental.demo.run
"""

from __future__ import annotations

import json

import frappe

from av_rental.api import (
    extend_gear_list,
    issue_gear_list,
    partial_return,
    record_damage,
)
from av_rental.festival import (
    COMPANY_ABBR,
    COMPANY_NAME,
    CUSTOMER_NAME,
    LINES,
    LISTS,
    PLANNED_IN,
    PLANNED_OUT,
    PROJECT_TITLE,
    evaluate,
    story_actions,
)


def run():
    frappe.set_user("Administrator")
    master = _ensure_master()
    frappe.db.commit()
    project, gear_ids, line_ids = _ensure_structure(master)
    frappe.db.commit()

    frozen = None
    if not frappe.db.exists("Rental Event", {"rental_project": project}):
        frozen = _apply_story(project, gear_ids, line_ids)
    checks = _verify(project, gear_ids, line_ids, frozen)
    failed = [check for check in checks if not check["ok"]]
    payload = {"ok": not failed, "project": project, "checks": checks}
    print(json.dumps(payload, indent=2, default=str))
    if failed:
        frappe.db.rollback()
        frappe.throw(
            "Festival demo failed: " + "; ".join(check["name"] for check in failed),
            frappe.ValidationError,
        )
    frappe.db.commit()
    return payload


def _ensure_master():
    _ensure_warehouse_types()
    _ensure_uom()
    company = _ensure_company()
    warehouse = _ensure_warehouse(company)
    customer = _ensure_customer()
    item_group = _ensure_item_group()
    for spec in LINES:
        _ensure_item(spec["item_code"], spec["item_name"], item_group)
    return {"company": company, "warehouse": warehouse, "customer": customer}


def _ensure_uom():
    if frappe.db.exists("UOM", "Nos"):
        return
    frappe.get_doc(
        {
            "doctype": "UOM",
            "uom_name": "Nos",
            "must_be_whole_number": 1,
        }
    ).insert(ignore_permissions=True)


def _ensure_warehouse_types():
    """ERPNext's company setup links a Goods In Transit warehouse to this type.

    A fresh `bench new-site` does not seed it; the setup wizard normally would.
    """
    if not frappe.db.exists("DocType", "Warehouse Type"):
        return
    if frappe.db.exists("Warehouse Type", "Transit"):
        return
    frappe.get_doc(
        {
            "doctype": "Warehouse Type",
            "name": "Transit",
            "description": "Goods moving between warehouses",
        }
    ).insert(ignore_permissions=True)


def _ensure_company():
    existing = frappe.db.get_value("Company", {"abbr": COMPANY_ABBR}, "name") or frappe.db.exists(
        "Company", COMPANY_NAME
    )
    if existing:
        return existing
    payload = {
        "doctype": "Company",
        "company_name": COMPANY_NAME,
        "abbr": COMPANY_ABBR,
        "default_currency": "EUR",
        "country": "Ireland",
    }
    meta = frappe.get_meta("Company")
    if meta.has_field("create_chart_of_accounts_based_on"):
        payload["create_chart_of_accounts_based_on"] = "Standard Template"
    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_warehouse(company):
    existing = frappe.db.get_value(
        "Warehouse", {"company": company, "warehouse_name": "Stores", "is_group": 0}, "name"
    )
    if existing:
        return existing
    parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
    doc = frappe.get_doc(
        {
            "doctype": "Warehouse",
            "warehouse_name": "Dry Hire",
            "company": company,
            "parent_warehouse": parent,
            "is_group": 0,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_root(doctype, name, group_field="is_group"):
    if frappe.db.exists(doctype, name):
        return
    payload = {"doctype": doctype, group_field: 1}
    # These trees are named by a title field, not by the document name alone.
    title_field = {
        "Territory": "territory_name",
        "Customer Group": "customer_group_name",
        "Item Group": "item_group_name",
    }[doctype]
    payload[title_field] = name
    frappe.get_doc(payload).insert(ignore_permissions=True)


def _ensure_customer():
    if frappe.db.exists("Customer", CUSTOMER_NAME):
        return CUSTOMER_NAME
    _ensure_root("Customer Group", "All Customer Groups")
    if not frappe.db.exists("Customer Group", "Commercial"):
        frappe.get_doc(
            {
                "doctype": "Customer Group",
                "customer_group_name": "Commercial",
                "parent_customer_group": "All Customer Groups",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
    _ensure_root("Territory", "All Territories")
    if not frappe.db.exists("Territory", "Ireland"):
        frappe.get_doc(
            {
                "doctype": "Territory",
                "territory_name": "Ireland",
                "parent_territory": "All Territories",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
    doc = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": CUSTOMER_NAME,
            "customer_type": "Company",
            "customer_group": "Commercial",
            "territory": "Ireland",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_item_group():
    if frappe.db.exists("Item Group", "AV Lighting"):
        return "AV Lighting"
    _ensure_root("Item Group", "All Item Groups")
    doc = frappe.get_doc(
        {
            "doctype": "Item Group",
            "item_group_name": "AV Lighting",
            "parent_item_group": "All Item Groups",
            "is_group": 0,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_item(item_code, item_name, item_group):
    if frappe.db.exists("Item", item_code):
        return item_code
    payload = {
        "doctype": "Item",
        "item_code": item_code,
        "item_name": item_name,
        "item_group": item_group,
        "stock_uom": "Nos",
        "is_stock_item": 1,
    }
    meta = frappe.get_meta("Item")
    if meta.has_field("is_sales_item"):
        payload["is_sales_item"] = 1
    if meta.has_field("include_item_in_manufacturing"):
        payload["include_item_in_manufacturing"] = 0
    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_structure(master):
    project = frappe.db.get_value("Rental Project", {"project_title": PROJECT_TITLE}, "name")
    if not project:
        project = frappe.get_doc(
            {
                "doctype": "Rental Project",
                "project_title": PROJECT_TITLE,
                "customer": master["customer"],
                "company": master["company"],
                "project_status": "Confirmed",
                "planned_start": PLANNED_OUT,
                "planned_end": PLANNED_IN,
                "warehouse": master["warehouse"],
                "notes": "Lighting dry hire. Two trucks, nested lists, one shared project.",
            }
        ).insert(ignore_permissions=True).name

    gear_ids = {}
    for spec in LISTS:
        name = frappe.db.get_value(
            "Gear List",
            {"rental_project": project, "list_name": spec["list_name"]},
            "name",
        )
        if not name:
            parent = gear_ids.get(spec["parent"]) if spec["parent"] else None
            name = frappe.get_doc(
                {
                    "doctype": "Gear List",
                    "list_name": spec["list_name"],
                    "rental_project": project,
                    "parent_gear_list": parent,
                    "is_group": spec["is_group"],
                    "planned_out": PLANNED_OUT,
                    "planned_in": PLANNED_IN,
                    "warehouse": master["warehouse"],
                }
            ).insert(ignore_permissions=True).name
        gear_ids[spec["list_name"]] = name

    line_ids = {}
    for spec in LINES:
        gear = gear_ids[spec["list_name"]]
        name = frappe.db.get_value(
            "Rental Line",
            {"gear_list": gear, "item_code": spec["item_code"]},
            "name",
        )
        if not name:
            name = frappe.get_doc(
                {
                    "doctype": "Rental Line",
                    "gear_list": gear,
                    "rental_project": project,
                    "item_code": spec["item_code"],
                    "qty": spec["qty"],
                    "warehouse": master["warehouse"],
                    "planned_out": PLANNED_OUT,
                    "planned_in": PLANNED_IN,
                }
            ).insert(ignore_permissions=True).name
        line_ids[(spec["list_name"], spec["item_code"])] = name
    return project, gear_ids, line_ids


def _modified(doctype, name):
    return str(frappe.db.get_value(doctype, name, "modified"))


def _apply_story(project, gear_ids, line_ids):
    """Issue both trucks, then change only Truck A. Return modified stamps taken in between."""
    actions = story_actions()
    issues = [action for action in actions if action["action"] == "issue_list"]
    incident = [action for action in actions if action["action"] != "issue_list"]
    for action in issues:
        _run_action(action, gear_ids, line_ids)
    frozen = {
        "project": _modified("Rental Project", project),
        "gear_lists": {
            list_name: _modified("Gear List", gear_ids[list_name])
            for list_name in ("Show", "Truck B", "Stage Right", "Stage Left")
        },
        "lines": {key: _modified("Rental Line", name) for key, name in line_ids.items()},
    }
    for action in incident:
        _run_action(action, gear_ids, line_ids)
    return frozen


def _run_action(action, gear_ids, line_ids):
    kind = action["action"]
    gear_list = gear_ids[action["list_name"]]
    if kind == "issue_list":
        issue_gear_list(gear_list, action["reason"])
    elif kind == "partial_return":
        partial_return(
            [{"rental_line": line_ids[(action["line_list"], action["item_code"])], "qty": action["qty"]}],
            action["reason"],
            gear_list=gear_list,
        )
    elif kind == "damage":
        record_damage(
            [{"rental_line": line_ids[(action["line_list"], action["item_code"])], "qty": action["qty"]}],
            action["reason"],
            gear_list=gear_list,
        )
    elif kind == "extend_list":
        extend_gear_list(gear_list, action["extended_until"], action["reason"])
    else:
        frappe.throw(f"Unknown story action {kind}")


def _verify(project, gear_ids, line_ids, frozen):
    project_doc = frappe.db.get_value(
        "Rental Project",
        project,
        ["project_title", "customer", "project_status", "planned_start", "planned_end"],
        as_dict=True,
    )
    customer_name = frappe.db.get_value("Customer", project_doc.customer, "customer_name")
    statuses = {}
    planned = {}
    for list_name, name in gear_ids.items():
        row = frappe.db.get_value(
            "Gear List",
            name,
            ["list_status", "planned_out", "planned_in"],
            as_dict=True,
        )
        statuses[list_name] = row.list_status
        planned[list_name] = {"planned_out": row.planned_out, "planned_in": row.planned_in}

    from av_rental.api import effective_on_hire

    view = effective_on_hire(project)
    rows = []
    name_to_list = {name: list_name for list_name, name in gear_ids.items()}
    line_meta = {}
    for (list_name, item_code), name in line_ids.items():
        line_meta[name] = {"list_name": list_name, "item_code": item_code}
    for row in view["rows"]:
        meta = line_meta[row["rental_line"]]
        rows.append({**row, "list_name": meta["list_name"], "item_code": meta["item_code"]})

    events = []
    for event in frappe.get_all(
        "Rental Event",
        filters={"rental_project": project},
        fields=[
            "rental_line",
            "gear_list",
            "event_type",
            "qty",
            "reason",
            "actor",
            "event_timestamp",
            "extended_until",
        ],
    ):
        meta = line_meta[event.rental_line]
        events.append(
            {
                "list_name": meta["list_name"],
                "item_code": meta["item_code"],
                "gear_list_name": name_to_list.get(event.gear_list),
                "event_type": event.event_type,
                "qty": event.qty,
                "reason": event.reason,
                "actor": event.actor,
                "event_timestamp": event.event_timestamp,
                "extended_until": event.extended_until,
            }
        )

    checks = evaluate(
        {
            "rows": rows,
            "statuses": statuses,
            "planned": planned,
            "events": events,
            "project": {
                "project_title": project_doc.project_title,
                "customer": project_doc.customer,
                "customer_name": customer_name,
                "project_status": project_doc.project_status,
                "planned_start": project_doc.planned_start,
                "planned_end": project_doc.planned_end,
            },
        }
    )
    if frozen:
        checks.append(
            {
                "name": "project document was not saved by the incident",
                "ok": _modified("Rental Project", project) == frozen["project"],
                "detail": "",
            }
        )
        for list_name, stamp in frozen["gear_lists"].items():
            checks.append(
                {
                    "name": f"{list_name} document was not saved by the incident",
                    "ok": _modified("Gear List", gear_ids[list_name]) == stamp,
                    "detail": "",
                }
            )
        for key, stamp in frozen["lines"].items():
            checks.append(
                {
                    "name": f"line {key[0]} {key[1]} was not rewritten",
                    "ok": _modified("Rental Line", line_ids[key]) == stamp,
                    "detail": "",
                }
            )
    return checks
