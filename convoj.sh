#!/usr/bin/env bash
# WSL launcher for convoj.py — equivalent to convoj.bat

set -euo pipefail

# Sám seba zistím, kde som — netreba CONVOJ_HOME nikde nastavovať
CONVOJ_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$CONVOJ_HOME/src/convoj.py" "$@"