#!/bin/sh
set -eu

app_path=/var/www/signals
marker="$app_path/public/do-not-use-as-application"
if [ -f "$marker" ]; then
    echo "Signals source is unavailable. This PHP image is not the application." >&2
    echo "Restore framework-core into this directory; see README.md and SPIKE.md." >&2
    exit 1
fi

if [ ! -f "$app_path/artisan" ]; then
    composer create-project signals-rental/framework-core /tmp/signals-app --no-interaction
    cp -a /tmp/signals-app/. "$app_path/"
fi

cd "$app_path"
if [ ! -f .env ]; then
    cp .env.example .env
fi

php artisan signals:install --no-interaction \
    --db-host=postgres \
    --db-port=5432 \
    --db-database="${POSTGRES_DB:-signals}" \
    --db-username="${POSTGRES_USER:-signals}" \
    --db-password="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" \
    --cache-driver=redis \
    --redis-host=redis \
    --redis-port=6379 \
    --storage-driver=local \
    --broadcast-driver=log \
    --app-url="${APP_URL:-http://localhost:18080}"

exec php artisan serve --host=0.0.0.0 --port=8000
