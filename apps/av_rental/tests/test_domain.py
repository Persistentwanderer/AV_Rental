"""Domain tests for the two-truck hire story. No Frappe runtime required."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from av_rental import domain
from av_rental.festival import (
    EXTENDED_UNTIL,
    PLANNED_IN,
    PLANNED_OUT,
    TRUCK_B_LISTS,
    evaluate,
    materialise,
    play,
)


class FestivalStoryTest(unittest.TestCase):
    def test_two_truck_story_matches_the_hire_invariants(self):
        result = play()
        snapshot = {
            "rows": [
                {
                    **row,
                    "list_name": row["gear_list_name"],
                }
                for row in result["rows"]
            ],
            "statuses": result["status"],
            "planned": {
                row["list_name"]: {"planned_out": row["planned_out"], "planned_in": row["planned_in"]}
                for row in result["gear_lists"]
            },
            "events": result["events"],
            "project": {
                "project_title": "Harbour Lights Festival 2026",
                "customer": "Harbour Lights Festival",
                "project_status": "Confirmed",
                "planned_start": PLANNED_OUT,
                "planned_end": PLANNED_IN,
            },
        }
        checks = evaluate(snapshot)
        failed = [check for check in checks if not check["ok"]]
        self.assertFalse(failed, failed)

    def test_incident_status_map_does_not_name_truck_b_or_the_show(self):
        gear_lists, lines = materialise()
        played = play()
        updates = domain.status_updates(gear_lists, lines, played["events"], "Truck A")
        self.assertEqual(set(updates), {"Truck A", "FOH", "Stage Left"})
        self.assertTrue(TRUCK_B_LISTS.isdisjoint(updates))
        self.assertNotIn("Show", updates)
        self.assertTrue(all(isinstance(value, str) for value in updates.values()))

    def test_flat_list_partial_return_leaves_a_sibling_list_alone(self):
        lists = [
            {
                "name": "only",
                "list_name": "Only",
                "parent_gear_list": None,
                "planned_out": PLANNED_OUT,
                "planned_in": PLANNED_IN,
                "list_status": "Planned",
            },
            {
                "name": "other",
                "list_name": "Other",
                "parent_gear_list": None,
                "planned_out": PLANNED_OUT,
                "planned_in": PLANNED_IN,
                "list_status": "Planned",
            },
        ]
        lines = [
            {
                "name": "only-line",
                "gear_list": "only",
                "rental_project": "p",
                "item_code": "PAR",
                "item_name": "PAR can",
                "qty": 4,
                "planned_out": PLANNED_OUT,
                "planned_in": PLANNED_IN,
            },
            {
                "name": "other-line",
                "gear_list": "other",
                "rental_project": "p",
                "item_code": "CABLE",
                "item_name": "Power cable",
                "qty": 10,
                "planned_out": PLANNED_OUT,
                "planned_in": PLANNED_IN,
            },
        ]
        base = {
            "reason": "Call",
            "actor": "sam",
            "event_timestamp": "2026-11-12 12:00:00",
        }
        events = []
        events.append(domain.validate_event(lines[0], events, {**base, "event_type": "Issue", "qty": 4}))
        events.append(domain.validate_event(lines[1], events, {**base, "event_type": "Issue", "qty": 10}))
        events.append(
            domain.validate_event(lines[0], events, {**base, "event_type": "Partial Return", "qty": 1})
        )
        updates = domain.status_updates(lists, lines, events, "only")
        self.assertEqual(set(updates), {"only"})
        self.assertEqual(updates["only"], "Partially Returned")
        rows = {row["rental_line"]: row for row in domain.effective_rows(lists, lines, events)}
        self.assertEqual(rows["only-line"]["on_hire_qty"], 3)
        self.assertEqual(rows["other-line"]["on_hire_qty"], 10)
        self.assertEqual(rows["other-line"]["planned_in"].strftime("%Y-%m-%d %H:%M:%S"), PLANNED_IN)

    def test_qty_rules(self):
        line = {
            "name": "line",
            "gear_list": "list",
            "rental_project": "p",
            "qty": 2,
            "planned_in": PLANNED_IN,
            "planned_out": PLANNED_OUT,
        }
        base = {"reason": "Because", "actor": "sam", "event_timestamp": "2026-11-12 12:00:00"}
        issued = domain.validate_event(line, [], {**base, "event_type": "Issue", "qty": 2})
        with self.assertRaises(domain.DomainError):
            domain.validate_event(line, [issued], {**base, "event_type": "Issue", "qty": 1})
        with self.assertRaises(domain.DomainError):
            domain.validate_event(line, [issued], {**base, "event_type": "Partial Return", "qty": 3})
        with self.assertRaises(domain.DomainError):
            domain.validate_event(
                line,
                [issued],
                {**base, "event_type": "Extend", "qty": 2, "extended_until": PLANNED_IN},
            )
        extended = domain.validate_event(
            line,
            [issued],
            {**base, "event_type": "Extend", "qty": 2, "extended_until": EXTENDED_UNTIL},
        )
        self.assertEqual(
            domain.effective_expected_in(line, [issued, extended]).strftime("%Y-%m-%d %H:%M:%S"),
            EXTENDED_UNTIL,
        )
        damaged = domain.validate_event(line, [issued], {**base, "event_type": "Damage", "qty": 1})
        self.assertEqual(domain.on_hire_qty([issued, damaged]), 2)

    def test_subtree_rejects_cycles_and_unknown_roots(self):
        lists = [
            {"name": "a", "parent_gear_list": "b"},
            {"name": "b", "parent_gear_list": "a"},
        ]
        with self.assertRaises(domain.DomainError):
            domain.subtree_names(lists, "a")
        with self.assertRaises(domain.DomainError):
            domain.subtree_names(lists, "missing")


if __name__ == "__main__":
    unittest.main()
