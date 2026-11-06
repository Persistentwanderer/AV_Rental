# Signals spike outcome

**Verdict: blocked at source acquisition. ERPNext with the custom app `av_rental` is the chosen base.**

The notes in this directory are the failed Signals Rental Framework spike, kept as evidence. They are not a running Signals install and they are not the application in this repository.

Checked 6 November 2026 (Europe/Dublin). The official installation sources were not obtainable:

| Source | Result |
|---|---|
| `https://github.com/signals-rental/framework-core.git` | GitHub returns **404**. `git ls-remote` cannot see the repository. The org exists and publishes only `.github` and `plugins`. |
| `https://github.com/signals-rental/framework.git` | GitHub returns **404**. |
| Packagist package `signals-rental/framework-core` | **Does not exist.** `composer create-project` fails with "Could not find package ... with stability stable". |

No alternate fork was treated as upstream. There is no `framework-core` application tree, no migrations, and no Signals process. The laboratory Postgres and Redis checks in [SPIKE.md](SPIKE.md) only prove that the unused PHP scaffold's infrastructure could start. The intended Signals URL `http://localhost:18080` never served the product.

Do not wait on Signals for this MVP. The hire model that *is* implemented lives in the custom Frappe app `av_rental` on the official ERPNext image from [frappe/frappe_docker](https://github.com/frappe/frappe_docker). Partial returns and extensions are append-only `Rental Event` rows. They do not rewrite the project or a sibling gear list. See the repository root [README](../../README.md) and [docs/architecture.md](../architecture.md).

## What was copied

Useful spike files are here: `SPIKE.md`, `SCENARIO.md`, `HANDOFF.md`, the Compose/PHP scaffold, the probe scripts, and the text evidence under `evidence/`. The empty `framework-core/` directory is the mount that never received source.

No `.env` was copied. `.env.example` only contains the placeholder `POSTGRES_PASSWORD=change-me` from the spike and is not a credential for the ERPNext stack. The rendered Compose evidence mentions the same class of local placeholder (`local-infrastructure-only`).
