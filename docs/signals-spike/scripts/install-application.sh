#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a
. ./.env
set +a
./scripts/probe-source.sh
# Composer fails fast if the public package is still unavailable.
sudo docker run --rm --network host --user "$(id -u):$(id -g)" -v "$PWD/framework-core:/destination" -v "$PWD/scripts/composer.phar:/composer:ro" \
    composer:2 sh -c 'if [ -e /destination/artisan ]; then echo "Existing application kept; installation not overwritten."; else php /composer create-project signals-rental/framework-core /tmp/app --no-interaction && cp -a /tmp/app/. /destination/; fi'
./scripts/build-app-image.sh
sudo docker compose run --rm app
echo 'Infrastructure install done; configure the owner with:'
echo '  sudo docker compose run --rm app php artisan signals:setup'
