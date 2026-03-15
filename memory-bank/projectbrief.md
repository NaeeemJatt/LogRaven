# LogRaven — Project Brief

## What It Is
LogRaven is a security investigation platform delivered as a
licensed Docker image. Users upload 1+ log files into a named
investigation. LogRaven parses them, correlates events across
sources, runs AI analysis using Claude, maps findings to MITRE
ATT&CK, and generates a PDF report named lograven-report-{uuid}.pdf.
Under 3 minutes per investigation.

## Brand
Name:     LogRaven
Domain:   lograven.io
Tagline:  Watch your logs. Find the threat.
Docker:   lograven:v1.0
Project:  lograven/

## Delivery Model
Docker image. Client runs on their own machine.
Logs never leave client premises.
Client provides their own ANTHROPIC_API_KEY.
Revenue: per-deployment license fees.

## Target Customer
Freelance pentesters, SOC analysts, DFIR consultants, MSSPs.
NOT SMB IT admins.

## Core Feature
Multi-file correlation: upload endpoint + firewall + CloudTrail together.
Same entity (IP/user/host) across sources in same 5-minute window = correlated finding.
Single file always works. More files = better correlation.

## Phase 1 Log Types
Windows Endpoint (EVTX via pyevtx-rs)
Linux Syslog / auth.log
AWS CloudTrail JSON
Nginx / Apache access logs
