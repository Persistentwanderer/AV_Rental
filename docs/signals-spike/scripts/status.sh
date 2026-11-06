#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -f .env ]; then
    set -a; . ./.env; set +a
fi
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-local-infrastructure-only}"
echo '=== containers ==='
sudo docker ps --filter 'name=^av-rental-signals-'
echo '=== PostgreSQL ==='
sudo docker compose -f compose.infrastructure.yaml exec -T postgres psql -U signals -d signals -c 'SELECT version();'
sudo docker compose -f compose.infrastructure.yaml exec -T postgres psql -U signals -d signals -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('btree_gist', 'pg_trgm') ORDER BY extname;"
echo '=== Redis ==='
sudo docker compose -f compose.infrastructure.yaml exec -T redis redis-cli ping
if [ -f framework-core/artisan ]; then
    sudo docker compose -f compose.infrastructure.yaml exec -T app php artisan signals:status
else
    echo 'Signals application: NOT INSTALLED; source is unavailable. See SPIKE.md.'
fi
