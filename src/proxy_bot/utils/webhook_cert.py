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


def is_self_signed(cert_path: Path) -> bool:
    """Whether the cert at `cert_path` is self-signed (issuer == subject) -
    used by main.py's set_webhook call to decide whether `certificate=`
    needs pinning: required for a self-signed cert (Telegram has no CA
    chain to validate it against otherwise), actively wrong for a real
    CA-issued one (pins Telegram to one exact file instead of letting it
    validate the chain normally, defeating the point of using a CA cert -
    and leaves delivery to break silently whenever that pinned file expires,
    rather than just working across a renewal like a CA-validated cert
    would).

    Not tracked via a config flag or "did ensure_self_signed_cert just
    generate this" - either approach goes stale the moment an operator
    swaps in a real cert without updating a knob, or restarts a process
    that's carried the *same* self-signed file across several boots (which
    ensure_self_signed_cert's own persistence deliberately does). Reading
    the file's own issuer/subject is the one signal that can't drift out of
    sync with what's actually on disk.
    """
    result = subprocess.run(
        ["openssl", "x509", "-in", str(cert_path), "-noout", "-issuer", "-subject"],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.splitlines()
    issuer = next((line.removeprefix("issuer=") for line in lines if line.startswith("issuer=")), None)
    subject = next((line.removeprefix("subject=") for line in lines if line.startswith("subject=")), None)
    return issuer is not None and issuer == subject
