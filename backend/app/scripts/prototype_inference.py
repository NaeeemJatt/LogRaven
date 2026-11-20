import csv
import re
from pathlib import Path
from collections import Counter

cat_dir = Path("backend/app/data/csv_catalog")

def test_inference():
    total = 0
    detailed = 0
    fallback = 0

    for fname, prov in [
        ("controls_aws.csv", "AWS"),
        ("controls_azure.csv", "AZURE"),
        ("controls_gcp.csv", "GCP"),
        ("controls_oci.csv", "OCI"),
    ]:
        path = cat_dir / fname
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))
        h_idx = next(i for i, r in enumerate(rows[:10]) if r and r[0].strip().upper() == "CID")
        header = [h.strip() for h in rows[h_idx]]
        data = [dict(zip(header, [c.strip() for c in r])) for r in rows[h_idx+1:] if len(r) == len(header) and any(c.strip() for c in r)]

        p_total = len(data)
        p_detailed = 0
        p_fallback = 0

        for r in data:
            cid = r["CID"]
            name = r.get("CONTROL NAME", "")
            svc = r.get("SERVICE", "")
            nl = name.lower()

            # Detection logic prototype
            matched = False

            # AWS CloudTrail specific
            if prov == "AWS" and cid in ["18", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40"]:
                matched = True
            elif "port 22" in nl or "ssh" in nl:
                matched = True
            elif "port 3389" in nl or "rdp" in nl:
                matched = True
            elif "0.0.0.0/0" in nl or "internet" in nl or "open to the world" in nl:
                matched = True
            elif "admin privileges" in nl or "*:*" in nl or "all actions" in nl:
                matched = True
            elif "mfa" in nl or "multi-factor" in nl:
                matched = True
            elif "customer managed key" in nl or "cmk" in nl or "csek" in nl or "cmek" in nl:
                matched = True
            elif "encrypted" in nl or "encryption" in nl or "encrypt" in nl:
                matched = True
            elif "rotated" in nl or "rotation" in nl or "unused" in nl:
                matched = True
            elif "publicly accessible" in nl or "public access" in nl or "publicly visible" in nl:
                matched = True
            elif "versioning" in nl:
                matched = True
            elif "logging" in nl or "audit" in nl or "flow log" in nl or "diagnostic" in nl:
                matched = True
            elif "password policy" in nl or "uppercase" in nl or "lowercase" in nl or "symbol" in nl or "numeric" in nl or "minimum password" in nl:
                matched = True
            elif "https" in nl or "ssl" in nl or "tls" in nl or "secure transfer" in nl or "deny http" in nl:
                matched = True
            elif "backup" in nl or "snapshot" in nl or "retention" in nl:
                matched = True
            elif "multi-az" in nl or "deletion protection" in nl or "auto minor version" in nl or "auto repair" in nl or "auto upgrade" in nl:
                matched = True
            elif "soft delete" in nl or "purge protection" in nl:
                matched = True
            elif "imds" in nl or "metadata" in nl or "serial port" in nl or "secure boot" in nl:
                matched = True
            elif "firewall" in nl or "network policy" in nl or "private cluster" in nl or "authorized networks" in nl:
                matched = True
            elif "defender" in nl or "security center" in nl or "threat" in nl or "alert" in nl or "event rule" in nl:
                matched = True
            elif "database flag" in nl or "log_connections" in nl or "log_disconnections" in nl or "log_duration" in nl:
                matched = True
            elif "tracing" in nl or "monitoring" in nl or "metrics" in nl:
                matched = True
            elif "client cert" in nl or "client certificate" in nl or "http 2.0" in nl or "ftps" in nl or "remote debugging" in nl:
                matched = True
            elif "uniform bucket" in nl or "object lock" in nl or "pre-authenticated" in nl or "emit object events" in nl:
                matched = True
            elif "default security group" in nl or "default security list" in nl or "stateless" in nl:
                matched = True
            elif "service account" in nl or "root login" in nl or "oslogin" in nl or "legacy authorization" in nl or "dashboard" in nl:
                matched = True

            if matched:
                p_detailed += 1
            else:
                p_fallback += 1

        print(f"[{prov}] Total: {p_total}, Detailed: {p_detailed} ({p_detailed/p_total*100:.1f}%), Fallback: {p_fallback}")
        total += p_total
        detailed += p_detailed
        fallback += p_fallback

    print(f"\nOVERALL: Total: {total}, Detailed: {detailed} ({detailed/total*100:.1f}%), Fallback: {fallback}")

test_inference()
