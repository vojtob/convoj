#!/usr/bin/env bash
# Spustí convoj natívne — nástroje (drawio, imagemagick, ...) musia byť
# nainštalované lokálne, prípadne nastavené cez CONVOJ_*_CMD premenné.

set -euo pipefail

# Sám seba zistím, kde som — netreba CONVOJ_HOME nikde nastavovať
CONVOJ_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$CONVOJ_HOME/src/convoj.py" "$@"
