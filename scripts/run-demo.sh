#!/usr/bin/env bash
# Seed Harbour Lights Festival 2026 and check the two-truck incident.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

SITE_NAME="${SITE_NAME:-avrental.localhost}"
docker compose exec -T backend bench --site "$SITE_NAME" execute av_rental.demo.run
