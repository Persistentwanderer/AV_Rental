# Signals spike report

**Checked:** Friday, 6 November 2026, Europe/Dublin (UTC+0).  
**Overall application verdict: BLOCKED, not passed.**

## Provenance and acquisition

Official guide: <https://docs.signals.rent/docs/getting-started/installation>

| Planned source | Result on this box | Works? |
|---|---|---|
| `https://github.com/signals-rental/framework-core.git` | GitHub REST and web return **404**. `git ls-remote` cannot obtain the repository. The official org is reachable but publishes only `.github` and `plugins`. No public moved repository identified using GitHub repository search. | No |
| `https://github.com/signals-rental/framework.git` | GitHub REST returns **404**. | No |
| `composer create-project signals-rental/framework-core ...` | Fails on the host and in a Composer 2.11.1 container with host networking: **Could not find package ... with stability stable**. Packagist's official package metadata and search return **404 / zero packages** under that name. | No |

An initial container Composer attempt without host networking failed DNS and
masked its own `&&`/`||` error; the probe was subsequently rerun with host
networking and correct `set -e` handling. The retained log is the definitive
probe, whose actual result is **package missing**, not network failure.
Logs: `evidence/source-probes.txt`, `evidence/composer-create-project.log`,
and `evidence/container-composer-create-project.log`.
There is no `framework-core/artisan` and no application release archive here.
Do not report this spike as a successful package installation.

## Executed platform checks — PASS

- Docker 26.1.5 and Compose 2.26.1 installed on the box; a hello-world pull/run passed.
- Docker daemon starts in this box without altering host iptables or the default bridge.
- Postgres **17.11** is healthy at **127.0.0.1:55432**.
- `pg_extension` confirms **btree_gist 1.7** and **pg_trgm 1.6** in the `signals` database.
- Redis **7** is healthy (`PONG`) inside the `av-rental-signals` network.
- `av-rental-signals-php:local` builds with **PHP 8.4.27**, `bcmath`, `redis`,
  `pdo_pgsql`, `intl`, `zip`, `pcntl`, **Node 22.23.4**, npm and Composer.
- Full `docker compose --profile application config --quiet` succeeds.

`evidence/runtime-validation.txt` is the final health check. The application
port **18080 is not active** because application acquisition failed. No database
migrations, setup owner, application UI, API token, or generated OpenAPI schema
has been exercised.

## Truck incident scenario — FAIL / documented only

Proposed model to exercise when the application source is available:

1. Create one Rental Project (`R`: Festival).
2. Create root rental `R0` (hire 12–14 November).
3. Create associated child `A` for **Truck A** and child `B` for **Truck B**.
   Confirm both are separate event streams and independent state/fulfilment
   documents, with `GET /api/v1/rentals/{root}/tree` returning a 3-node tree.
4. Add included accessories beneath a line on Truck B (for example fixture →
   clamp → power cable). Check whether this satisfies the desired operational
   sublist and whether an additional issue grouping is needed.
5. Allocate and dispatch both. Open Truck A's returns workbench at
   `/returns/{A}` and check in only the delivered subset. Add damage or missing
   dispositions to outstanding items. Do not close until all remaining manifest
   lines are returned/dispositioned.
6. Invoke Truck A's `POST /api/v1/rentals/{A}/extend` with an explicit later
   window (15–17 November). Check `GET /api/v1/rentals/{A}/tree`: new child
   `A1`, copied fresh lines, `A` unchanged including its version and dates,
   and `B` unchanged in its harvest, fulfilment and totals.
7. Check that A can remain partially returned/exception-handling while B is
   returned and closed independently. Completing/cancelling the root must not
   implicitly cascade to descendants: no descendant IDs passed means neither
   is silently rewritten.

### Documented basis (not runtime evidence)

- <https://docs.signals.rent/docs/platform/rentals>: arbitrary associated-rental
  tree, `associated`, `extend`, per-rental state/events/totals; original rental
  remains unchanged on extension; return/missing/repair/disposition handling;
  partial lines can be returned while others stay outstanding.
- <https://docs.signals.rent/docs/platform/rental-projects>: projects can contain
  associated descendants and render a depth-annotated tree.
- <https://docs.signals.rent/docs/user-guides/processing-a-return>: each rental's
  own expected manifest, returned/outstanding counts, missing/damage/swap/repair
  dispositions, and guarded per-rental close.
- <https://docs.signals.rent/docs/platform/accessories>: nested included
  accessories become real nested persisted lines.
- The API root is `/api/v1`; exact request bodies are only authoritative in that
  installed application's `/docs/api.json`. Do not guess schemas in advance.
- Extension explicitly leaves the **parent unchanged**. It creates a separate
  child with new fresh lines; it does not turn individual line items into
  independent child rental objects.

Conclusion: Signals' documented model addresses the core incident requirement
at the *rental* level, with useful nesting at the *catalogue accessory* level.
The application-level acceptance remains unproven and is deliberately a FAIL for
this spike, not a pass based on marketing or documentation.

## Blockers and next action

The only application blocker is restoring legitimate source distribution:
a public upstream release or an authorised checkout from the project maintainer.
No alternate fork has been treated as authoritative. Once present in
`framework-core/`, run the commands in `README.md`, create a local demo owner,
obtain a scoped local token, and execute `SCENARIO.md`.

Docker setup on the host also required Debian apt's documented
`Acquire::EnableSrvRecords=false` option after relay/SRV failures; the setting
is stored in `/etc/apt/apt.conf.d/99av-rental-disable-srv`.
An apt-source snapshot before that change is retained at
`/etc/apt/sources.list.d/debian.sources.av-rental-backup`.
