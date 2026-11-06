# AV Rental — Signals local Docker spike

**Status: application installation blocked; laboratory infrastructure is running.**
This is a real Docker infrastructure/PHP-runtime scaffold, not a simulated Signals
application. The public source described by Signals' official installation guide
is presently unavailable. See [SPIKE.md](SPIKE.md) for the exact outcome.

## What is here

- `compose.yaml`: intended complete development stack (Postgres 17, Redis 7,
  PHP 8.4/Node 22 app, queue worker and scheduler).
- `compose.infrastructure.yaml`: the Postgres/Redis subset currently running;
  matching the running Compose project lets the helpers inspect it reliably.
- `docker/`: image and entrypoint for the non-interactive `signals:install`.
- `scripts/`: repeatable source probes, infrastructure startup, installation,
  and health checks.
- `evidence/`: official documentation snapshots and source/runtime probe output.
- `framework-core/`: reserved empty application mount, not Signals source.

## Start now on the box

```sh
cd /workspace/av-rental-signals
./scripts/up-infra.sh
./scripts/status.sh
```

Infrastructure currently listens on:

| Service | URL / address |
|---|---|
| PostgreSQL 17 | `postgresql://signals@127.0.0.1:55432/signals` |
| Redis 7 | Internal Compose service `redis:6379`; intentionally no host port |
| Signals application | Would be `http://localhost:18080`; **not currently listening** |

The database password is local development material, kept in the ignored `.env`
(`POSTGRES_PASSWORD=change-me` on this box). Change it before any real use.
Don't expose the development server or this database to an untrusted network.

`up-infra.sh` starts a Docker daemon suited to this particular box if needed.
The daemon deliberately does not change host iptables or the host bridge.
Compose's image build uses host networking for its build-time apt downloads;
ordinary containers and the persistent data remain isolated in Docker named volumes.

## When the official application source is restored

```sh
cd /workspace/av-rental-signals
./scripts/up-infra.sh
./scripts/install-application.sh
sudo docker compose --profile application up -d app worker scheduler
curl -I http://localhost:18080
sudo docker compose exec -T app php artisan signals:status
```

`install-application.sh` uses the documented official
`composer create-project signals-rental/framework-core` command and the
non-interactive installer. It is expected to fail today, with
`Could not find package signals-rental/framework-core with stability stable.`
It is not fixed in this scaffold because that would require an unverified fork
or a private source unknown to this spike.

The first owner still needs to be created. **Choose new secrets locally**, then
run this official non-interactive form (documented but not executable here
against Signals source):

```sh
sudo docker compose run --rm app php artisan signals:setup --no-interaction --blank --force \
  --company-name='AV Rental Spike' \
  --company-email='spike@example.invalid' \
  --warehouse-name='Main Warehouse' \
  --admin-name='Local Administrator' \
  --admin-email='admin@example.invalid' \
  --admin-password='<choose-a-new-local-password>'
```

Check the choices with `php artisan signals:setup --help` after installation.
Use `--demo` instead of `--blank` only in a disposable demo database.

## Documentation-only feature result

- **Nested project/operation structure:** promising documented support through
  arbitrary associated-rental descendants, with nested per-item included
  accessories. Named custom rental sections are flat. This does not yet prove
  every "arbitrary gear list of lists" case.
- **Two-truck incident:** documented independent children and partial returns
  support a credible design, but the **executed spike is a FAIL / unverified**
  because there is no deployed Signals application on which to run it.
- `SPIKE.md` defines a test that will assert no rewrite of the parent or healthy
  truck once source access is restored.

No GitHub push was made: `gh` is not authenticated. Everything remains locally
on the box in this directory.
