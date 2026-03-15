# LogRaven

**Watch your logs. Find the threat.**

LogRaven is a security investigation platform delivered as a licensed Docker image.
Upload log files, correlate events across sources, get a MITRE ATT&CK mapped PDF report.

## Quick Start (Development)

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY in .env
docker compose up -d
# Open http://localhost:8000
```

## For Clients
See docker-compose.client.yml and .env.example

## Docs
See MASTER_SPEC.md and lograven_master_v3.docx
