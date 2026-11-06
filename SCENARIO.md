# Truck incident acceptance checklist

**Not executable before a legitimate Signals source is installed. No results
below are counted as runtime passes.**

Use a disposable local instance (`--demo` is optional). Create a local Sanctum
token with the documented abilities `projects:read`, `projects:write`,
`rentals:read`, and `rentals:write`; use the installed `/docs/api` to confirm
fulfilment abilities and exact payloads. Record actual JSON inputs/outputs and
redact the token.

| # | Action | Required evidence |
|---|---|---|
| 1 | Project R → root R0 → child A and child B | `GET R0/tree` has A and B at distinct child nodes |
| 2 | A line has nested included accessory | Persisted parent/accessory line relation, not merely UI indentation |
| 3 | Dispatch both A and B | Fulfilment traces exist separately in A and B |
| 4 | Partial return A, leaving damaged/missing item(s) dispositioned | Returned + outstanding/exception counts; B's manifest not touched |
| 5 | Extend only A into A1 via `POST /rentals/A/extend` | A's original ID/version/dates/lines unchanged; new A1 in new window; A1 fresh enquiry and copied lines |
| 6 | Return/close B normally | B follows its own return lifecycle; A remains separate |
| 7 | Complete/cancel R0 without descendant cascade selection | No silent complete/cancel event in A, A1, or B |

Acceptance needs every record and an explicit "PASS" backed by its actual
responses. Do not infer success from HTTP 200 alone or from these documents.
