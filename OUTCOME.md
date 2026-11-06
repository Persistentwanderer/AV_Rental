# Signals spike outcome

**Verdict: blocked at source acquisition.**

Checked 6 November 2026 (Europe/Dublin). The official installation sources were not obtainable:

| Source | Result |
|---|---|
| `https://github.com/signals-rental/framework-core.git` | GitHub returns **404**. `git ls-remote` cannot see the repository. The org exists and publishes only `.github` and `plugins`. |
| `https://github.com/signals-rental/framework.git` | GitHub returns **404**. |
| Packagist package `signals-rental/framework-core` | **Does not exist.** `composer create-project` fails with "Could not find package ... with stability stable". |

No alternate fork was treated as upstream. `framework-core/` in this branch is an empty mount. There is no Signals process and no migration history. The Postgres and Redis notes in [SPIKE.md](SPIKE.md) only show that this scaffold's infrastructure could start. `http://127.0.0.1:18080` never served Signals.

The implemented dry-hire desk is not on this branch. It is the Frappe app `av_rental` on the [`erpnext` branch](https://github.com/Persistentwanderer/AV_Rental/tree/erpnext).

No `.env` is stored here. `.env.example` only contains the placeholder `POSTGRES_PASSWORD=change-me`. The rendered Compose evidence mentions the same class of local placeholder (`local-infrastructure-only`).
