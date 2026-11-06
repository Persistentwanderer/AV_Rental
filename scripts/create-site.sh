#!/usr/bin/env bash
# Create the local site and install ERPNext, then av_rental.
# Safe to re-run: an existing site is left in place and av_rental is installed if missing.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

DB_PASSWORD="${DB_PASSWORD:-change-me}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-change-me}"
SITE_NAME="${SITE_NAME:-avrental.localhost}"
HTTP_PUBLISH_PORT="${HTTP_PUBLISH_PORT:-18080}"

echo "Waiting for the backend to accept connections on port 8000..."
ready=0
for _ in $(seq 1 60); do
  if docker compose exec -T backend \
    /home/frappe/frappe-bench/env/bin/python -c \
    "import socket; socket.create_connection(('127.0.0.1', 8000), 2).close()" \
    >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 5
done
if [[ "$ready" -ne 1 ]]; then
  echo "Backend did not open port 8000. Check: docker compose ps && docker compose logs backend" >&2
  exit 1
fi

if docker compose exec -T backend bench --site "$SITE_NAME" list-apps >/tmp/av-rental-apps.txt 2>/dev/null; then
  echo "Site ${SITE_NAME} already exists."
else
  echo "Creating site ${SITE_NAME}. ERPNext fixtures usually take several minutes."
  docker compose exec -T backend bench new-site "$SITE_NAME" \
    --mariadb-user-host-login-scope='%' \
    --db-root-password "$DB_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --install-app erpnext
fi

if ! grep -q '^av_rental' /tmp/av-rental-apps.txt 2>/dev/null \
  && ! docker compose exec -T backend bench --site "$SITE_NAME" list-apps | grep -q '^av_rental'; then
  echo "Installing av_rental."
  docker compose exec -T backend bench --site "$SITE_NAME" install-app av_rental
fi

docker compose exec -T backend bench use "$SITE_NAME"
docker compose exec -T backend bench --site "$SITE_NAME" set-config host_name "http://127.0.0.1:${HTTP_PUBLISH_PORT}"
docker compose exec -T backend bench --site "$SITE_NAME" enable-scheduler || true

echo
echo "Desk: http://127.0.0.1:${HTTP_PUBLISH_PORT}"
echo "Site: ${SITE_NAME}"
echo "User: Administrator"
echo "Password: the ADMIN_PASSWORD in .env (placeholder is change-me)."
echo "Next: ./scripts/run-demo.sh"
