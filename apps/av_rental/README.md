# av_rental

Frappe app that adds nested dry-hire gear lists and append-only hire events on top of ERPNext. It does not fork ERPNext.

Install and the two-truck demo are documented in the repository root [README](../../README.md). The pure hire rules live in `av_rental/domain.py` and can be tested without a site:

```sh
python3 -m unittest discover -s tests -v
```
