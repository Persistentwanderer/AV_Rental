# AV Rental

A locally hosted dry-hire desk for AV and lighting. A project is either one gear list or a list of lists (a festival, two trucks, FOH and Stage Left inside Truck A). Partial returns, damage, and extensions are events on the lines they touch. They do not rewrite the job, and they do not move the other truck's dates.

This is a portfolio project. It sits on ERPNext as the Frappe app `av_rental`. ERPNext is not forked. Crew scheduling, transport routing, a client portal, barcode hardware, RFID, and automated invoicing are out of scope.

## The problem

Rental desks such as Rentman and Locasyst are built around a show that then breaks into trucks, rooms, and zones. The awkward part is the second week of the hire: one truck comes home early with a broken wash, and the promoter keeps the other half of that truck for an extra day. The rest of the job is unchanged.

Putting that nested hire in one editable sales order means every incident rewrites the order. The original plan and the trail of who changed which quantity disappear.

## Why Signals was abandoned

The first choice was [Signals Rental Framework](https://docs.signals.rent/docs/getting-started/installation). On 6 November 2026 that source was not obtainable:

- `github.com/signals-rental/framework-core` returns 404
- `github.com/signals-rental/framework` returns 404
- Packagist package `signals-rental/framework-core` does not exist

The spike's own notes, probe logs, and the empty `framework-core` mount are in [docs/signals-spike/](docs/signals-spike/OUTCOME.md). Nothing from Signals was installed. ERPNext plus `av_rental` is the base that was actually built. The Signals Compose scaffold, kept for the day source exists, is on the [`signals` branch](https://github.com/Persistentwanderer/AV_Rental/tree/signals).

## Why ERPNext and a custom app

ERPNext already has Customer, Company, Item, Warehouse, UOM, and a place to record serial numbers. The hire-specific behaviour is a small app:

| DocType | What it holds |
|---|---|
| **Rental Project** | Customer, dates, status. The job's identity. |
| **Gear List** | A named tree node. Parent is optional. |
| **Rental Line** | Item and quantity, with a planned out/in that stays the baseline. |
| **Rental Event** | Append-only Issue, Partial Return, Extend, or Damage: qty, when, why, who. |
| **Effective On Hire** | Read-only report. Still out, given the plan plus the events. |

An extension does not edit `planned_in`. It adds an Extend event. The effective return date is the latest extension, otherwise the planned date. Damage is an incident; it does not take gear off hire. On-hire quantity is issued minus partial returns.

Acting on Truck A refreshes Truck A and its children only. Truck B and the project document are not saved. The model and the Compose layout are written up in [docs/architecture.md](docs/architecture.md).

## Run it

Docker with Compose v2, and about 4 GB of free memory. The first boot pulls `frappe/erpnext:v16.54.0` (about 1 GB compressed) and site creation installs ERPNext fixtures, which often takes several minutes after the containers are up.

```sh
cp .env.example .env
docker compose up -d --build
./scripts/create-site.sh
./scripts/run-demo.sh
```

`.env.example` contains only local placeholders (`change-me`). Copy it to `.env` and change the passwords before any shared use. `.env` is gitignored. The MariaDB root password is stored on first initialisation; changing `.env` later does not rotate it.

| What | Where |
|---|---|
| Desk | http://127.0.0.1:18080 |
| Site name | `avrental.localhost` |
| User | `Administrator` |
| Password | `ADMIN_PASSWORD` in `.env` |

Port **18080** is bound on loopback so it does not take the usual 8080. Inside the container, nginx still listens on 8080, which is the frappe_docker default. MariaDB and Redis are not published to the host.

The image is the official `frappe/erpnext:v16.54.0` image with `apps/av_rental` installed into the bench. `compose.yaml` follows the current frappe_docker services (configurator, backend, frontend, websocket, workers, scheduler, MariaDB 11.8, Redis 8.6). It is not a copy of the ERPNext source.

`./scripts/create-site.sh` is safe to re-run. `./scripts/run-demo.sh` seeds the festival the first time and only re-checks it after that. A failed check rolls the events back so the script can be run again.

Log in, open the **AV Rental** workspace, and open **Harbour Lights Festival 2026**. **Effective On Hire** is the computed view. Gear List forms have Hire actions: Issue outstanding, Partial return, Record damage, Extend list. The same actions exist on a Rental Line. Rental Event rows are the trail; the form does not offer a way to rewrite them.

To free memory after the demo, the workers are optional:

```sh
docker compose stop queue-short queue-long scheduler
```

## Two-truck demo

Harbour Lights Festival 2026, planned 12–14 November 2026, customer Harbour Lights Festival, company Harbour Lights Hire.

```text
Show
├── Truck A
│   ├── FOH            Moving Head Wash × 8, Lighting Console × 1
│   └── Stage Left     Moving Head Spot × 6, 12-channel Dimmer Rack × 2
└── Truck B
    └── Stage Right    Wireless LED Tube × 24, Socapex 12-way 25m × 4, Touring Hazer × 1
```

`av_rental.demo.run` (what `./scripts/run-demo.sh` calls):

1. Issues Truck A and Truck B in full.
2. Records a partial return of 2 washes from FOH, scoped to Truck A.
3. Records damage on 1 of those washes. Damage does not reduce the on-hire count.
4. Extends every line still out under Truck A through 17 November 18:00.
5. Asserts Truck B's planned dates and list status stay at the issued plan, Show's status stays Planned, the project document is not saved by the incident, and every change is a Rental Event with actor, time, quantity, and reason.

Truck A ends **Partially Returned** (6 washes still out, plus the rest of that truck). Those lines show an effective return of 17 November. Their planned return is still 14 November. Truck B stays **Issued** with an effective return of 14 November and only Issue events.

The same assertions run without Docker:

```sh
./scripts/verify-domain.sh
```

That executes `apps/av_rental/tests/test_domain.py` against the pure rules in `av_rental/domain.py`. It does not need MariaDB or ERPNext.

## What was verified

`docker compose --env-file .env.example config --quiet` succeeds. The image build from `frappe/erpnext:v16.54.0` succeeds, and `./scripts/create-site.sh` installs ERPNext and `av_rental`. `./scripts/run-demo.sh` then records the Harbour Lights story and passes every check, including "Truck B was not saved by the incident". Running it again only re-checks; it does not add a second set of events. The desk login at http://127.0.0.1:18080 returns HTTP 200.

A fresh `bench new-site` does not run the ERPNext setup wizard, so the demo creates the few records that wizard would have created: the `Nos` UOM, the `Transit` warehouse type, and the root territory, customer group, and item group.

`docker compose up` only starts processes. Site creation is the slow step and needs a normal Docker bridge so the backend can reach MariaDB and Redis. Plan on about 4 GB of free memory and several minutes for the first ERPNext install. The domain tests do not need any of that.

## Layout

```text
apps/av_rental/          Frappe app (DocTypes, API, demo, domain tests)
compose.yaml             ERPNext + av_rental
Dockerfile               official ERPNext image plus this app
scripts/create-site.sh   bench new-site, install erpnext, install av_rental
scripts/run-demo.sh      two-truck story
scripts/verify-domain.sh hire rules with no site
docs/architecture.md     events, nesting, Compose
docs/signals-spike/      why Signals stopped, with the original probes
```

## License

The `av_rental` app is MIT. ERPNext and Frappe keep their own licenses; this repo does not vendor them.
