#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! sudo docker info >/dev/null 2>&1; then
    sudo nohup dockerd --iptables=false --ip6tables=false --bridge=none \
        > evidence/dockerd.log 2>&1 &
    echo 'Starting the box Docker daemon ...'
fi
attempt=0
until sudo docker info >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    [ "$attempt" -le 30 ] || { cat evidence/dockerd.log; exit 1; }
    sleep 1
done
if [ ! -s .env ]; then
    cp .env.example .env
fi
set -a
. ./.env
set +a
if ! sudo docker ps --format '{{.Names}}' | grep -qx 'av-rental-signals-postgres-1'; then
    sudo docker compose -f compose.infrastructure.yaml down --remove-orphans
fi
sudo docker compose -f compose.infrastructure.yaml up -d postgres redis
./scripts/status.sh
