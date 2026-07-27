#!/bin/sh
set -e

# data/ and logs/ are bind-mounted from the host (docker-compose.yml), which
# replaces whatever ownership was baked into the image at build time with
# whatever the host directories happen to have - e.g. root, if someone ran
# `mkdir -p data logs` as root before first start. Fix it on every start
# instead of requiring the host directories to be pre-chowned correctly.
if [ "$(id -u)" = "0" ]; then
    chown -R bot:bot /app/data /app/logs
    exec gosu bot "$@"
fi

exec "$@"
