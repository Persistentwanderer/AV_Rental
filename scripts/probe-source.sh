#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
{
    echo "Signals source probes; authoritative public endpoints"
    for repository in framework-core framework; do
        url="https://api.github.com/repos/signals-rental/$repository"
        echo "=== $url ==="
        curl -sS -w '\nHTTP %{http_code}\n' "$url" || true
    done
    echo '=== https://repo.packagist.org/p2/signals-rental/framework-core.json ==='
    curl -sS -w '\nHTTP %{http_code}\n' https://repo.packagist.org/p2/signals-rental/framework-core.json || true
} > evidence/source-probes.txt 2>&1
cat evidence/source-probes.txt
echo 'Registry lookup is intentionally nonfatal; inspect the HTTP result above.'
