"""Harbour Lights two-truck dry-hire story.

Pure data: the Frappe demo and the unit tests both follow `story_actions()`.
"""

from __future__ import annotations

from av_rental import domain

PROJECT_TITLE = "Harbour Lights Festival 2026"
CUSTOMER_NAME = "Harbour Lights Festival"
COMPANY_NAME = "Harbour Lights Hire"
COMPANY_ABBR = "HLH"

PLANNED_OUT = "2026-11-12 09:00:00"
PLANNED_IN = "2026-11-14 18:00:00"
EXTENDED_UNTIL = "2026-11-17 18:00:00"
STORY_ACTOR = "Administrator"
STORY_TIMESTAMP = "2026-11-13 22:15:00"

ISSUE_REASON = "Dispatch dry hire to the Harbour Lights site"
RETURN_REASON = (
    "Night 1: two washes came off the truss and returned to the warehouse early"
)
DAMAGE_REASON = (
    "One returned wash has a cracked lens and a bent yoke; quarantined for repair"
)
EXTEND_REASON = "Promoter kept Truck A for an extra load-out day"

LISTS = (
    {"list_name": "Show", "parent": None, "is_group": 1},
    {"list_name": "Truck A", "parent": "Show", "is_group": 1},
    {"list_name": "FOH", "parent": "Truck A", "is_group": 0},
    {"list_name": "Stage Left", "parent": "Truck A", "is_group": 0},
    {"list_name": "Truck B", "parent": "Show", "is_group": 1},
    {"list_name": "Stage Right", "parent": "Truck B", "is_group": 0},
)

LINES = (
    {"list_name": "FOH", "item_code": "WASH-AURA", "item_name": "Moving Head Wash", "qty": 8},
    {"list_name": "FOH", "item_code": "CONSOLE-GMA", "item_name": "Lighting Console", "qty": 1},
    {"list_name": "Stage Left", "item_code": "SPOT-ROGUE", "item_name": "Moving Head Spot", "qty": 6},
    {"list_name": "Stage Left", "item_code": "DIM-12", "item_name": "12-channel Dimmer Rack", "qty": 2},
    {"list_name": "Stage Right", "item_code": "TUBE-LED", "item_name": "Wireless LED Tube", "qty": 24},
    {"list_name": "Stage Right", "item_code": "SOCA-25", "item_name": "Socapex 12-way 25m", "qty": 4},
    {"list_name": "Stage Right", "item_code": "HAZER-TOUR", "item_name": "Touring Hazer", "qty": 1},
)

TRUCK_A_LISTS = frozenset({"Truck A", "FOH", "Stage Left"})
TRUCK_B_LISTS = frozenset({"Truck B", "Stage Right"})


def story_actions() -> list[dict]:
    """Issue both trucks, then a Truck A-only incident and extension."""
    return [
        {"action": "issue_list", "list_name": "Truck A", "reason": ISSUE_REASON},
        {"action": "issue_list", "list_name": "Truck B", "reason": ISSUE_REASON},
        {
            "action": "partial_return",
            "list_name": "Truck A",
            "line_list": "FOH",
            "item_code": "WASH-AURA",
            "qty": 2,
            "reason": RETURN_REASON,
        },
        {
            "action": "damage",
            "list_name": "Truck A",
            "line_list": "FOH",
            "item_code": "WASH-AURA",
            "qty": 1,
            "reason": DAMAGE_REASON,
        },
        {
            "action": "extend_list",
            "list_name": "Truck A",
            "extended_until": EXTENDED_UNTIL,
            "reason": EXTEND_REASON,
        },
    ]


def materialise(project: str = "festival"):
    """Build in-memory lists and lines with stable ids."""
    lists = []
    for spec in LISTS:
        lists.append(
            {
                "name": spec["list_name"],
                "list_name": spec["list_name"],
                "parent_gear_list": spec["parent"],
                "is_group": spec["is_group"],
                "list_status": domain.STATUS_PLANNED,
                "planned_out": PLANNED_OUT,
                "planned_in": PLANNED_IN,
                "rental_project": project,
            }
        )
    lines = []
    for spec in LINES:
        lines.append(
            {
                "name": f"{spec['list_name']}:{spec['item_code']}",
                "gear_list": spec["list_name"],
                "list_name": spec["list_name"],
                "rental_project": project,
                "item_code": spec["item_code"],
                "item_name": spec["item_name"],
                "qty": spec["qty"],
                "planned_out": PLANNED_OUT,
                "planned_in": PLANNED_IN,
            }
        )
    return lists, lines


def _line_index(lines):
    return {(line["list_name"], line["item_code"]): line for line in lines}


def _lists_in(gear_lists, root_name: str):
    return set(domain.subtree_names(gear_lists, root_name))


def _append(events, line, event_type, amount, reason, scope, batch, extended_until=None):
    prior = events
    event = domain.validate_event(
        line,
        prior,
        {
            "event_type": event_type,
            "qty": amount,
            "reason": reason,
            "actor": STORY_ACTOR,
            "event_timestamp": STORY_TIMESTAMP,
            "extended_until": extended_until,
            "batch_id": batch,
            "scope": scope,
        },
    )
    event["list_name"] = line["list_name"]
    event["item_code"] = line["item_code"]
    events.append(event)
    return event


def play():
    """Run the story against the pure model. Planned fields are not written."""
    gear_lists, lines = materialise()
    by_key = _line_index(lines)
    events: list[dict] = []
    status = {row["name"]: domain.STATUS_PLANNED for row in gear_lists}
    batches = []

    def apply_status(root_name: str):
        status.update(domain.status_updates(gear_lists, lines, events, root_name))

    for index, action in enumerate(story_actions(), start=1):
        batch = f"story-{index}"
        batches.append(batch)
        kind = action["action"]
        root = action["list_name"]
        if kind == "issue_list":
            for line in lines:
                if line["gear_list"] not in _lists_in(gear_lists, root):
                    continue
                outstanding = domain.qty(
                    domain.qty(line["qty"]) - domain.issued_qty(domain.events_for_line(events, line["name"]))
                )
                if outstanding <= 0:
                    continue
                _append(events, line, domain.EVENT_ISSUE, outstanding, action["reason"], "Gear List", batch)
            apply_status(root)
        elif kind == "partial_return":
            line = by_key[(action["line_list"], action["item_code"])]
            if line["gear_list"] not in _lists_in(gear_lists, root):
                raise domain.DomainError("Return target is outside the gear list")
            _append(
                events,
                line,
                domain.EVENT_RETURN,
                action["qty"],
                action["reason"],
                "Gear List",
                batch,
            )
            apply_status(root)
        elif kind == "damage":
            line = by_key[(action["line_list"], action["item_code"])]
            if line["gear_list"] not in _lists_in(gear_lists, root):
                raise domain.DomainError("Damage target is outside the gear list")
            _append(
                events,
                line,
                domain.EVENT_DAMAGE,
                action["qty"],
                action["reason"],
                "Gear List",
                batch,
            )
            apply_status(root)
        elif kind == "extend_list":
            for line in lines:
                if line["gear_list"] not in _lists_in(gear_lists, root):
                    continue
                on_hire = domain.on_hire_qty(domain.events_for_line(events, line["name"]))
                if on_hire <= 0:
                    continue
                _append(
                    events,
                    line,
                    domain.EVENT_EXTEND,
                    on_hire,
                    action["reason"],
                    "Gear List",
                    batch,
                    extended_until=action["extended_until"],
                )
            apply_status(root)
        else:
            raise domain.DomainError(f"Unknown story action {kind}")

    rows = domain.effective_rows(gear_lists, lines, events)
    return {
        "gear_lists": gear_lists,
        "lines": lines,
        "events": events,
        "status": status,
        "rows": rows,
        "batches": batches,
    }


def _close(left, right) -> bool:
    return abs(float(left) - float(right)) < 1e-6


def _same_moment(left, right) -> bool:
    return domain.parse_dt(left) == domain.parse_dt(right)


def evaluate(snapshot: dict) -> list[dict]:
    """Checks that one truck can move without rewriting the other.

    snapshot:
      rows: effective rows with list_name + item_code
      statuses: {list_name: list_status}
      planned: {list_name: {planned_out, planned_in}} and optionally
               {(list_name, item_code): {planned_out, planned_in}} under line_planned
      events: denormalised events with list_name, item_code, event_type, qty,
              reason, actor, event_timestamp, extended_until
      project: {project_status, planned_start, planned_end, customer, project_title}
    """
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    rows = {(row["list_name"], row["item_code"]): row for row in snapshot["rows"]}
    statuses = snapshot["statuses"]
    planned = snapshot["planned"]
    events = snapshot["events"]
    project = snapshot.get("project") or {}

    wash = rows[("FOH", "WASH-AURA")]
    check("wash on hire is issued minus the partial return", _close(wash["on_hire_qty"], 6), wash["on_hire_qty"])
    check("wash return qty is 2", _close(wash["returned_qty"], 2))
    check("wash damage qty is 1 and does not reduce on hire", _close(wash["damaged_qty"], 1))
    check("wash planned return is unchanged", _same_moment(wash["planned_in"], PLANNED_IN))
    check("wash effective return is the Truck A extension", _same_moment(wash["effective_expected_in"], EXTENDED_UNTIL))

    console = rows[("FOH", "CONSOLE-GMA")]
    check("console stayed fully on hire", _close(console["on_hire_qty"], 1) and _close(console["returned_qty"], 0))
    check("console effective return moved with Truck A", _same_moment(console["effective_expected_in"], EXTENDED_UNTIL))
    check("console planned return is unchanged", _same_moment(console["planned_in"], PLANNED_IN))

    spot = rows[("Stage Left", "SPOT-ROGUE")]
    check("stage left spots extended with Truck A", _same_moment(spot["effective_expected_in"], EXTENDED_UNTIL))
    check("stage left spots were not returned", _close(spot["returned_qty"], 0) and _close(spot["on_hire_qty"], 6))

    tube = rows[("Stage Right", "TUBE-LED")]
    check("truck B tubes still fully on hire", _close(tube["on_hire_qty"], 24) and _close(tube["returned_qty"], 0))
    check("truck B tubes were not damaged", _close(tube["damaged_qty"], 0))
    check("truck B tubes keep the planned return", _same_moment(tube["effective_expected_in"], PLANNED_IN))
    check("truck B tubes planned window unchanged", _same_moment(tube["planned_out"], PLANNED_OUT) and _same_moment(tube["planned_in"], PLANNED_IN))

    for list_name in TRUCK_B_LISTS | TRUCK_A_LISTS | {"Show"}:
        window = planned[list_name]
        check(
            f"{list_name} planned window unchanged",
            _same_moment(window["planned_out"], PLANNED_OUT) and _same_moment(window["planned_in"], PLANNED_IN),
        )

    check("Show status was not rewritten", statuses.get("Show") == domain.STATUS_PLANNED, statuses.get("Show"))
    check("Truck A status is partially returned", statuses.get("Truck A") == domain.STATUS_PARTIAL, statuses.get("Truck A"))
    check("FOH status is partially returned", statuses.get("FOH") == domain.STATUS_PARTIAL, statuses.get("FOH"))
    check("Stage Left stays issued", statuses.get("Stage Left") == domain.STATUS_ISSUED, statuses.get("Stage Left"))
    check("Truck B status stays issued", statuses.get("Truck B") == domain.STATUS_ISSUED, statuses.get("Truck B"))
    check("Stage Right status stays issued", statuses.get("Stage Right") == domain.STATUS_ISSUED, statuses.get("Stage Right"))

    check("every event has actor, timestamp, qty, and reason", all(
        event.get("actor") and event.get("event_timestamp") and event.get("reason") and float(event.get("qty") or 0) > 0
        for event in events
    ))
    incident_types = {domain.EVENT_RETURN, domain.EVENT_EXTEND, domain.EVENT_DAMAGE}
    leaked = [
        event for event in events
        if event["event_type"] in incident_types and event["list_name"] not in {"FOH", "Stage Left"}
    ]
    check("incident events stay on Truck A lines", not leaked, leaked)
    truck_b_events = [event for event in events if event["list_name"] in {"Stage Right"}]
    check(
        "Truck B lines only have issue events",
        truck_b_events and all(event["event_type"] == domain.EVENT_ISSUE for event in truck_b_events),
    )
    check("seven issue events", sum(1 for event in events if event["event_type"] == domain.EVENT_ISSUE) == 7)
    check("one partial return", sum(1 for event in events if event["event_type"] == domain.EVENT_RETURN) == 1)
    check("one damage event", sum(1 for event in events if event["event_type"] == domain.EVENT_DAMAGE) == 1)
    check(
        "four Truck A extensions",
        sum(1 for event in events if event["event_type"] == domain.EVENT_EXTEND) == 4,
    )
    extends = [event for event in events if event["event_type"] == domain.EVENT_EXTEND]
    check(
        "extensions carry the new expected return",
        all(_same_moment(event.get("extended_until"), EXTENDED_UNTIL) for event in extends),
    )

    if project:
        check("project title stable", project.get("project_title") == PROJECT_TITLE)
        check("project customer stable", project.get("customer") == CUSTOMER_NAME or project.get("customer_name") == CUSTOMER_NAME)
        check("project status not rewritten by events", project.get("project_status") == "Confirmed", project.get("project_status"))
        check(
            "project planned window unchanged",
            _same_moment(project.get("planned_start"), PLANNED_OUT) and _same_moment(project.get("planned_end"), PLANNED_IN),
        )

    return checks
