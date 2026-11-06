#!/usr/bin/env bash
# Hire-rule tests. No Docker and no ERPNext site required.
set -euo pipefail
cd "$(dirname "$0")/../apps/av_rental"
python3 -m unittest discover -s tests -v
