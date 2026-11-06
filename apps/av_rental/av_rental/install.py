"""Install desk actions and extra role permissions."""

from __future__ import annotations

import os

import frappe

SCRIPTS = (
    ("Gear List", "gear_list.js", "AV Rental Gear List"),
    ("Rental Line", "rental_line.js", "AV Rental Rental Line"),
    ("Rental Project", "rental_project.js", "AV Rental Rental Project"),
)

ROLE_PERMS = {
    "Rental Project": ("read", "write", "create", "report", "export", "print"),
    "Gear List": ("read", "write", "create", "report", "export", "print"),
    "Rental Line": ("read", "write", "create", "report", "export", "print"),
    "Rental Event": ("read", "create", "report", "export", "print"),
}


def after_install():
    ensure_client_scripts()
    ensure_permissions()


def after_migrate():
    ensure_client_scripts()
    ensure_permissions()


def ensure_client_scripts():
    base = os.path.join(os.path.dirname(__file__), "public", "js")
    for dt, filename, name in SCRIPTS:
        with open(os.path.join(base, filename), encoding="utf-8") as handle:
            script = handle.read()
        payload = {
            "doctype": "Client Script",
            "dt": dt,
            "view": "Form",
            "enabled": 1,
            "script": script,
        }
        if frappe.db.exists("Module Def", "AV Rental"):
            payload["module"] = "AV Rental"
        if frappe.db.exists("Client Script", name):
            doc = frappe.get_doc("Client Script", name)
            if doc.script != script or not doc.enabled:
                doc.script = script
                doc.enabled = 1
                doc.save(ignore_permissions=True)
            continue
        payload["name"] = name
        frappe.get_doc(payload).insert(ignore_permissions=True)


def ensure_permissions():
    for role in ("Stock User", "Sales User"):
        if not frappe.db.exists("Role", role):
            continue
        for doctype, ptypes in ROLE_PERMS.items():
            if not _has_perm(doctype, role):
                frappe.permissions.add_permission(doctype, role, 0)
            for ptype in ptypes:
                frappe.permissions.update_permission_property(doctype, role, 0, ptype, 1)


def _has_perm(doctype, role) -> bool:
    if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
        return True
    return bool(
        frappe.db.exists(
            "DocPerm",
            {"parent": doctype, "role": role, "permlevel": 0},
        )
    )
