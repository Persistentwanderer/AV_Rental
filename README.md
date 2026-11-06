# AV Rental — Signals scaffold

**Status: source acquisition blocked. Signals is not installed.**

This branch is the Signals Rental Framework path: a Docker Compose wrapper, the
source probes, and the two-truck acceptance checklist. It is not a running
Signals application. Official source was not obtainable on 6 November 2026.
See [SPIKE.md](SPIKE.md) and [OUTCOME.md](OUTCOME.md).

The hire desk that was actually built is the custom Frappe app on the
[`erpnext` branch](https://github.com/Persistentwanderer/AV_Rental/tree/erpnext).
This branch does not contain that app.

## What is here

- `compose.yaml`: Postgres 17, Redis 7, and the PHP 8.4 / Node 22 app, worker, and scheduler. The app service is behind the `application` profile and does not start until `framework-core` exists.
- `compose.infrastructure.yaml`: Postgres and Redis only.
- `docker/`: image and entrypoint for a non-interactive `signals:install`.
- `scripts/`: source probe, infrastructure startup, install, and health check.
- `evidence/`: probe output from the spike.
- `framework-core/`: empty mount. It is not Signals source.
- `SCENARIO.md`: acceptance checklist to run after a real install.
- `HANDOFF.md`: what the spike finished and what is still blocked.

No `.env` is committed. `.env.example` contains only `POSTGRES_PASSWORD=change-me`.

## Check that source is still missing

```sh
./scripts/probe-source.sh
```

As of the spike, these all fail:

| Source | Result |
|---|---|
| `https://github.com/signals-rental/framework-core.git` | GitHub **404** |
| `https://github.com/signals-rental/framework.git` | GitHub **404** |
| Packagist `signals-rental/framework-core` | Package **does not exist** |

`./scripts/install-application.sh` runs the documented `composer create-project signals-rental/framework-core` command. It is expected to fail today with `Could not find package signals-rental/framework-core with stability stable.` The script is not pointed at an unverified fork.

## Infrastructure only

Postgres and Redis can start without the application:

```sh
cp .env.example .env
./scripts/up-infra.sh
./scripts/status.sh
```

| Service | Address |
|---|---|
| PostgreSQL 17 | `postgresql://signals@127.0.0.1:55432/signals` |
| Redis 7 | Compose service `redis:6379` only. No host port. |
| Signals | Would be `http://127.0.0.1:18080`. **Nothing is listening** until source exists. |

Change `POSTGRES_PASSWORD` in the untracked `.env` before any shared use. Do not publish this database.

## When official source exists

```sh
cp .env.example .env
./scripts/up-infra.sh
./scripts/install-application.sh
docker compose --profile application up -d app worker scheduler
curl -I http://127.0.0.1:18080
docker compose exec -T app php artisan signals:status
```

Create the first owner with new local secrets. This form is documented and is not runnable until `framework-core/artisan` exists:

```sh
docker compose run --rm app php artisan signals:setup --no-interaction --blank --force \
  --company-name='AV Rental Spike' \
  --company-email='spike@example.invalid' \
  --warehouse-name='Main Warehouse' \
  --admin-name='Local Administrator' \
  --admin-email='admin@example.invalid' \
  --admin-password='<choose-a-new-local-password>'
```

Confirm the flags with `php artisan signals:setup --help` after install. Then run [SCENARIO.md](SCENARIO.md). Acceptance is a partial return and an extension on one child rental while the sibling and the parent keep their own dates and state. Do not treat HTTP 200 alone as a pass.

No alternate fork is treated as upstream. Until `framework-core` is a legitimate checkout, this branch stays a scaffold.
