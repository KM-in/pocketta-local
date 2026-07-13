#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -d .venv ]]; then
  echo "A .venv directory already exists. Remove it intentionally before recreating it."
  exit 0
fi

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "Python 3.11 is required but was not found." >&2
  echo "Install the Python 3.11 runtime first, then rerun ./scripts/create_venv.sh." >&2
  exit 1
fi

python3.11 -m venv .venv

venv_version="$(.venv/bin/python --version 2>&1)"
case "$venv_version" in
  "Python 3.11."*) ;;
  *)
    echo "Refusing to use unexpected environment interpreter: $venv_version" >&2
    exit 1
    ;;
esac

echo "Created .venv with $venv_version"
echo "Activate it with: source .venv/bin/activate"
