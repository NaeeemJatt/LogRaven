# LogRaven — License Validation
#
# PURPOSE:
#   Called at FastAPI startup event BEFORE anything else initializes.
#   Validates the LICENSE_KEY environment variable against machine fingerprint.
#   Raises SystemExit with clear message if license is invalid or expired.
#   The SECRET_SALT is hardcoded here — it is embedded in the obfuscated Docker
#   image and cannot be read by the client from the running container.
#
# MACHINE FINGERPRINT:
#   SHA256 hash of (MAC address + hostname) — unique per machine.
#   Client runs this to get their fingerprint:
#   python -c "import hashlib,uuid,os; m=hex(uuid.getnode()); h=os.uname().nodename; print(hashlib.sha256(f'{m}:{h}'.encode()).hexdigest()[:32])"
#
# LICENSE KEY FORMAT:
#   base64(client_id:expiry) + "." + HMAC(client_id:fingerprint:expiry)
#
# TODO Month 4 Week 3: Implement this file.

import hashlib
import uuid
import hmac
import base64
import os
from datetime import date

# CRITICAL: Must match lograven-license-generator.py SECRET_SALT
# Never change this value after deployment — existing licenses will break
SECRET_SALT = "lograven-salt-embedded-in-binary-2026"


def get_machine_fingerprint() -> str:
    """Generate a unique fingerprint for the current machine."""
    mac = hex(uuid.getnode())
    hostname = os.uname().nodename
    return hashlib.sha256(f"{mac}:{hostname}".encode()).hexdigest()[:32]


def validate_license(license_key: str, bypass_dev: bool = False) -> bool:
    """
    Validate the LogRaven license key.
    Called at startup — raises SystemExit if invalid.
    """
    if bypass_dev and os.getenv("DEBUG") == "True":
        return True  # Allow dev bypass only when DEBUG=True

    # TODO Month 4 Week 3: Implement full HMAC validation
    # For now in development: accept any non-empty key
    if not license_key:
        raise SystemExit("[LogRaven] No LICENSE_KEY set. Contact vendor.")
    return True
