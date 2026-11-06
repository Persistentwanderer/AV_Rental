"""Hire maths for nested gear lists.

No Frappe imports. Planned quantities and planned windows are inputs. Issue,
partial return, extend, and damage are events. Effective on-hire is derived.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

EVENT_ISSUE = "Issue"
EVENT_RETURN = "Partial Return"
EVENT_EXTEND = "Extend"
EVENT_DAMAGE = "Damage"
EVENT_TYPES = (EVENT_ISSUE, EVENT_RETURN, EVENT_EXTEND, EVENT_DAMAGE)

STATUS_PLANNED = "Planned"
STATUS_ISSUED = "Issued"
STATUS_PARTIAL = "Partially Returned"
STATUS_RETURNED = "Returned"


class DomainError(ValueError):
    """A hire action that would break the planned baseline or the qty rules."""


def parse_dt(value):
    """Return a naive datetime, or None when value is empty."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).strip().replace("T", " ")
    if text.endswith("Z"):
        text = text[:-1]
    if "+" in text[10:]:
        text = text.split("+", 1)[0].strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise DomainError(f"Unrecognised datetime {value!r}")


def qty(value) -> float:
    return round(float(value or 0), 4)


def subtree_names(gear_lists, root: str) -> list[str]:
    """Depth-first names for root and its descendants. Rejects cycles."""
    by_parent: dict[str | None, list[str]] = defaultdict(list)
    known: set[str] = set()
    for row in gear_lists:
        name = row["name"]
        known.add(name)
        parent = row.get("parent_gear_list") or None
        by_parent[parent].append(name)
    if root not in known:
        raise DomainError(f"Unknown gear list {root}")
    ordered: list[str] = []
    stack = [root]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            raise DomainError("Gear list cycle")
        seen.add(current)
        ordered.append(current)
        stack.extend(reversed(by_parent.get(current, [])))
    return ordered


def events_for_line(events, line_name: str) -> list[dict]:
    return [event for event in events if event.get("rental_line") == line_name]


def sum_type(events, event_type: str) -> float:
    return qty(sum(qty(event.get("qty")) for event in events if event.get("event_type") == event_type))


def issued_qty(events) -> float:
    return sum_type(events, EVENT_ISSUE)


def returned_qty(events) -> float:
    return sum_type(events, EVENT_RETURN)


def damaged_qty(events) -> float:
    return sum_type(events, EVENT_DAMAGE)


def on_hire_qty(events) -> float:
    return qty(issued_qty(events) - returned_qty(events))


def effective_expected_in(line, events):
    """Latest extension for the line, otherwise the planned return."""
    baseline = parse_dt(line.get("planned_in"))
    latest = None
    for event in events:
        if event.get("event_type") != EVENT_EXTEND:
            continue
        until = parse_dt(event.get("extended_until"))
        if until is None:
            continue
        if latest is None or until > latest:
            latest = until
    return latest or baseline


def validate_event(line, prior_events, new_event) -> dict:
    """Return a normalised event or raise DomainError. Does not mutate inputs."""
    event_type = new_event.get("event_type")
    if event_type not in EVENT_TYPES:
        raise DomainError(f"Unknown event type {event_type}")
    amount = qty(new_event.get("qty"))
    if amount <= 0:
        raise DomainError("Qty must be positive")
    reason = (new_event.get("reason") or "").strip()
    if not reason:
        raise DomainError("Reason is required")
    actor = (new_event.get("actor") or "").strip()
    if not actor:
        raise DomainError("Actor is required")
    timestamp = parse_dt(new_event.get("event_timestamp"))
    if timestamp is None:
        raise DomainError("Timestamp is required")

    line_events = events_for_line(prior_events, line["name"])
    issued = issued_qty(line_events)
    returned = returned_qty(line_events)
    damaged = damaged_qty(line_events)
    planned = qty(line["qty"])
    on_hire = qty(issued - returned)
    extended_until = None

    if event_type == EVENT_ISSUE:
        if qty(issued + amount - planned) > 0:
            raise DomainError(
                f"Cannot issue {amount:g} of {line['name']}; "
                f"planned {planned:g}, already issued {issued:g}"
            )
    elif event_type == EVENT_RETURN:
        if qty(amount - on_hire) > 0:
            raise DomainError(
                f"Cannot return {amount:g} of {line['name']}; on hire {on_hire:g}"
            )
    elif event_type == EVENT_DAMAGE:
        # Damage is an incident against issued gear. It does not take gear off hire.
        if qty(damaged + amount - issued) > 0:
            raise DomainError(
                f"Cannot record damage of {amount:g} on {line['name']}; only {issued:g} issued"
            )
    elif event_type == EVENT_EXTEND:
        if on_hire <= 0:
            raise DomainError(f"{line['name']} has nothing on hire to extend")
        if qty(amount - on_hire) > 0:
            raise DomainError(
                f"Cannot extend {amount:g} of {line['name']}; on hire {on_hire:g}"
            )
        extended_until = parse_dt(new_event.get("extended_until"))
        if extended_until is None:
            raise DomainError("Extend requires extended_until")
        current = effective_expected_in(line, line_events)
        if current is not None and extended_until <= current:
            raise DomainError("extended_until must be later than the current expected return")

    return {
        "rental_line": line["name"],
        "gear_list": line["gear_list"],
        "rental_project": line["rental_project"],
        "event_type": event_type,
        "qty": amount,
        "reason": reason,
        "actor": actor,
        "event_timestamp": timestamp,
        "extended_until": extended_until,
        "batch_id": new_event.get("batch_id"),
        "scope": new_event.get("scope") or "Line",
    }


def fulfilment_status(lines, events) -> str:
    """Derived list status from the lines passed in (usually a subtree)."""
    issued = 0.0
    returned = 0.0
    events_by_line: dict[str, list] = defaultdict(list)
    for event in events:
        if event.get("rental_line"):
            events_by_line[event["rental_line"]].append(event)
    for line in lines:
        line_events = events_by_line.get(line["name"], [])
        issued += issued_qty(line_events)
        returned += returned_qty(line_events)
    issued = qty(issued)
    returned = qty(returned)
    on_hire = qty(issued - returned)
    if issued <= 0:
        return STATUS_PLANNED
    if on_hire <= 0:
        return STATUS_RETURNED
    if returned > 0:
        return STATUS_PARTIAL
    return STATUS_ISSUED


def status_updates(gear_lists, lines, events, scope_root: str) -> dict[str, str]:
    """New list_status values for scope_root and its descendants only.

    Sibling lists and ancestors outside the subtree are absent from the result.
    Planned dates are never part of the result.
    """
    scope = subtree_names(gear_lists, scope_root)
    updates = {}
    for name in scope:
        subtree = set(subtree_names(gear_lists, name))
        sub_lines = [line for line in lines if line["gear_list"] in subtree]
        updates[name] = fulfilment_status(sub_lines, events)
    return updates


def list_path(name: str, lists_by_name: dict) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    current = name
    while current and current not in seen:
        seen.add(current)
        row = lists_by_name.get(current)
        if not row:
            break
        parts.append(row.get("list_name") or current)
        current = row.get("parent_gear_list") or None
    return " / ".join(reversed(parts))


def effective_rows(gear_lists, lines, events) -> list[dict]:
    """Read-only on-hire rows. One row per rental line."""
    events_by_line: dict[str, list] = defaultdict(list)
    for event in events:
        if event.get("rental_line"):
            events_by_line[event["rental_line"]].append(event)
    lists_by_name = {row["name"]: row for row in gear_lists}
    rows = []
    for line in lines:
        line_events = events_by_line.get(line["name"], [])
        gear = lists_by_name.get(line["gear_list"], {})
        parent = gear.get("parent_gear_list")
        parent_row = lists_by_name.get(parent) if parent else None
        rows.append(
            {
                "rental_project": line.get("rental_project"),
                "gear_list": line["gear_list"],
                "gear_list_name": gear.get("list_name") or line["gear_list"],
                "list_path": list_path(line["gear_list"], lists_by_name),
                "parent_gear_list": parent,
                "parent_list_name": (parent_row or {}).get("list_name"),
                "rental_line": line["name"],
                "item_code": line.get("item_code"),
                "item_name": line.get("item_name"),
                "planned_qty": qty(line["qty"]),
                "issued_qty": issued_qty(line_events),
                "returned_qty": returned_qty(line_events),
                "damaged_qty": damaged_qty(line_events),
                "on_hire_qty": on_hire_qty(line_events),
                "planned_out": parse_dt(line.get("planned_out")),
                "planned_in": parse_dt(line.get("planned_in")),
                "effective_expected_in": effective_expected_in(line, line_events),
                "list_status": gear.get("list_status"),
            }
        )
    rows.sort(key=lambda row: (row["list_path"], row.get("item_code") or ""))
    return rows
