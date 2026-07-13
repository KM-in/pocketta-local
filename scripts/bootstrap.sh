#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ "${1:-}" == "--clean" ]]; then
  rm -rf .venv frontend/node_modules
fi

./scripts/create_venv.sh
.venv/bin/python -m pip install -r backend/requirements-dev.txt
(cd frontend && npm ci)

echo "Project-local dependencies are ready."
