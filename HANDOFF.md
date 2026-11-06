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

## Files in this branch

- `README.md`: commands and configuration.
- `SPIKE.md`: full evidence, status, and blockers.
- `SCENARIO.md`: concrete acceptance test.
- `compose.yaml`: eventual complete app stack.
- `compose.infrastructure.yaml`: Postgres and Redis only.
- `evidence/`: probe output from the spike.

The original handoff referred to a local directory `/workspace/av-rental-signals`. Those files are the repository root of this `signals` branch. The implemented hire desk is on the `erpnext` branch, not here.

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

The spike itself made no commits. This branch is the preserved scaffold.
No service outside the original box was contacted for account creation,
modification, or form submission.
