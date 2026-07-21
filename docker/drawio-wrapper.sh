#!/bin/bash
# Headless spustenie drawio v kontajneri.
# drawio je Electron aplikácia — potrebuje X server (xvfb) a ako root nesmie
# použiť Chromium sandbox (--no-sandbox).
#
# V kontajneri nebeží dbus, takže Chromium sype neškodné ERROR hlášky
# (Failed to connect to the bus...). Filtrujeme ich zo stderr, aby bolo
# vidno skutočné chyby.

xvfb-run -a /opt/drawio/drawio \
    --no-sandbox --disable-gpu --disable-dev-shm-usage \
    "$@" 2> >(grep -vE 'dbus/(bus|object_proxy)\.cc|Failed to connect to the bus|Failed to call method' >&2)

exit $?
