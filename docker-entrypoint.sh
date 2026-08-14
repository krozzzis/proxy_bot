#!/bin/sh
set -e

# data/ and logs/ are bind-mounted from the host (docker-compose.yml), which
# replaces whatever ownership was baked into the image at build time with
# whatever the host directories happen to have - e.g. root, if someone ran
# `mkdir -p data logs` as root before first start. Fix it on every start
# instead of requiring the host directories to be pre-chowned correctly.
if [ "$(id -u)" = "0" ]; then
    # Optional: an operator-supplied real TLS cert/key for webhook mode
    # (see Config.use_webhook), bind-mounted in from wherever that
    # operator's own ACME setup keeps it - e.g. a separate Caddy instance's
    # certificate storage. Typically root-owned 0600 (Caddy's own default)
    # and unreadable by the "bot" user this entrypoint drops to below, so
    # it's copied in here - while still root - rather than bind-mounted
    # directly at WEBHOOK_CERT_PATH/WEBHOOK_PRIVKEY_PATH. Re-copied fresh on
    # every container start, so a renewed cert on the source side is picked
    # up on the bot's next restart - there's no in-process hot-reload (see
    # utils/webhook_cert.py). No-op (and no error) if unset - most
    # deployments use the self-signed cert utils/webhook_cert.py generates
    # on first start instead.
    if [ -n "$EXTERNAL_WEBHOOK_CERT" ] && [ -f "$EXTERNAL_WEBHOOK_CERT" ]; then
        cp "$EXTERNAL_WEBHOOK_CERT" "${WEBHOOK_CERT_PATH:-/app/data/webhook_cert.pem}"
        cp "$EXTERNAL_WEBHOOK_KEY" "${WEBHOOK_PRIVKEY_PATH:-/app/data/webhook_privkey.pem}"
    fi
    chown -R bot:bot /app/data /app/logs
    exec gosu bot "$@"
fi

exec "$@"
