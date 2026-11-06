# Handoff — AV_Rental Signals spike

## Executive result

This spike did **not** install or run Signals itself: the framework's official
source repository and advertised Composer package are both publicly unavailable
as of the check recorded in `SPIKE.md`.

It **did** complete and prove a reusable Docker foundation on this box:
Postgres 17 with both required extensions, Redis 7, and a PHP 8.4/Node 22 image.
These infrastructure services remain healthy and running. The intended app URL
is reserved at `http://localhost:18080`; **nothing from Signals is listening
there**.

## Files for the parent

- `/workspace/av-rental-signals/README.md`: commands and configuration.
- `/workspace/av-rental-signals/SPIKE.md`: full evidence, status, and blockers.
- `/workspace/av-rental-signals/SCENARIO.md`: concrete acceptance test.
- `/workspace/av-rental-signals/compose.yaml`: eventual complete app stack.
- `/workspace/av-rental-signals/compose.infrastructure.yaml`: live infra stack.
- `/workspace/av-rental-signals/evidence/`: official docs and raw check outputs.

## What remains

1. Make the official public repository/package available, or obtain the
   authorised source from the upstream maintainer.
2. Put the source into `framework-core/`, then install using `README.md`.
3. Generate the application OpenAPI spec and run `SCENARIO.md`. As a matter of
   acceptance, demonstrate sibling B and parent R0 retaining their state after
   sibling A's partial return and A-only extension.
4. Re-evaluate whether arbitrary rental sub-groups, not only nested catalogue
   accessories, are required for Issac's “list of lists” UX.

## Git / egress

No commits or pushes were made. `gh auth status` reports no authenticated host;
use parent GitHub tools if a later push is wanted. No service outside this box
was contacted for account creation, modification, or form submission.
