from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# 10 years - this is a self-signed cert Telegram is told to trust directly
# (uploaded via setWebhook's `certificate` param), not one validated
# against a CA, so there's no browser/OS trust-store rotation to keep up
# with. Regenerating it would just mean re-uploading via the next
# set_webhook call (main.py does this on every startup anyway), so the long
# lifetime is only about not bothering to regenerate, not a security
# tradeoff.
_VALID_DAYS = 3650


def ensure_self_signed_cert(cert_path: Path, privkey_path: Path, host: str) -> None:
    """Generate a self-signed TLS cert/key pair for `host` at `cert_path`/
    `privkey_path` if they don't already exist - the "no reverse proxy
    needed" webhook pattern the Bot API supports directly (see
    Config.use_webhook): the aiohttp server in main.py terminates TLS with
    this key, and the matching public cert is handed to Telegram via
    `certificate=` on set_webhook so it trusts it without a CA chain.

    Persisted under DATA_DIR (a bind-mounted volume - see docker-compose.yml)
    so a container recreation (e.g. a Watchtower update) doesn't silently
    swap in a new cert - main.py's set_webhook call would still re-upload
    the same one every startup either way, but there's no reason to
    regenerate what's still valid.
    """
    if cert_path.is_file() and privkey_path.is_file():
        return

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    privkey_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating a self-signed webhook certificate for %r at %s", host, cert_path)
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-sha256",
            "-days",
            str(_VALID_DAYS),
            "-nodes",
            "-keyout",
            str(privkey_path),
            "-out",
            str(cert_path),
            "-subj",
            f"/CN={host}",
            "-addext",
            f"subjectAltName=DNS:{host}",
        ],
        check=True,
        capture_output=True,
    )
