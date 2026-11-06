#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
sudo docker compose build app
