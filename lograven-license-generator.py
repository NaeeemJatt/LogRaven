#!/usr/bin/env python3
"""
LogRaven License Generator
--------------------------
Run this script on YOUR machine only.
NEVER include this file in the Docker image.

Usage:
    1. Ask client to run the fingerprint command below and send you the output.
    2. Run: python lograven-license-generator.py <client_id> <fingerprint> <expiry>
    3. Send the generated LICENSE_KEY to the client.

Client fingerprint command (client runs this):
    python -c "import hashlib,uuid,os; m=hex(uuid.getnode()); h=os.uname().nodename; print(hashlib.sha256(f'{m}:{h}'.encode()).hexdigest()[:32])"
"""

import hmac
import hashlib
import base64
import sys
from datetime import date, timedelta

# CRITICAL: Must match the SECRET_SALT in app/license.py inside the Docker image
SECRET_SALT = "lograven-salt-embedded-in-binary-2026"


def generate_license(client_id: str, fingerprint: str, expiry: str) -> str:
    """Generate a hardware-bound LogRaven license key."""
    msg = f"{client_id}:{fingerprint}:{expiry}"
    sig = hmac.new(SECRET_SALT.encode(), msg.encode(), hashlib.sha256).hexdigest()
    payload = base64.b64encode(f"{client_id}:{expiry}".encode()).decode()
    return f"{payload}.{sig}"


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python lograven-license-generator.py <client_id> <fingerprint> <expiry YYYY-MM-DD>")
        print("Example: python lograven-license-generator.py acme-corp abc123def456 2027-03-15")
        sys.exit(1)

    client_id   = sys.argv[1]
    fingerprint = sys.argv[2]
    expiry      = sys.argv[3]

    key = generate_license(client_id, fingerprint, expiry)
    print(f"\nLogRaven License Key for {client_id}:")
    print(f"  {key}")
    print(f"\nExpiry: {expiry}")
    print(f"Client: {client_id}")
    print(f"\nSend this LICENSE_KEY value to the client for their .env file.")
