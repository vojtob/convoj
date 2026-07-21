#!/usr/bin/env bash
# Spustí convoj v Docker kontajneri (image "convoj", prebiješ cez CONVOJ_IMAGE).
# Predpoklad: docker build -t convoj . už prebehol.

set -euo pipefail

# Nájdi koreň projektu na hoste (rovnaké markery ako convoj.py),
# aby sa mountoval celý projekt a nie len aktuálny podadresár.
root="$PWD"
while [[ "$root" != "/" ]]; do
    if [[ -d "$root/.git" || -d "$root/build" || -d "$root/docs" || -d "$root/src_doc" ]]; then
        break
    fi
    root="$(dirname "$root")"
done
[[ "$root" == "/" ]] && root="$PWD"
rel="${PWD#"$root"}"   # podcesta pod koreňom (prázdna, ak stojíme v koreni)

# Pri rootless Dockeri / Docker Desktop sa UID mapujú inak — --user by
# stratil práva na mount. Tam beží kontajner ako root a výstupy aj tak
# patria prihlásenému užívateľovi.
user_args=(--user "$(id -u):$(id -g)")
if docker info --format '{{.SecurityOptions}}' 2>/dev/null | grep -q rootless; then
    user_args=()
fi

exec docker run --rm \
    "${user_args[@]}" \
    -v "$root:/work" \
    -w "/work$rel" \
    "${CONVOJ_IMAGE:-convoj}" "$@"
