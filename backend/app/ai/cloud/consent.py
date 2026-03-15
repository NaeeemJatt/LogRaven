# LogRaven — Cloud AI Consent Check
#
# PURPOSE:
#   Verifies the user has explicitly opted in to cloud AI analysis.
#   Cloud AI sends event data to Anthropic servers.
#   This must be explicitly opted in — never automatic.
#
# CONSENT CHECK:
#   In LogRaven v1 (Docker delivery), consent is controlled by:
#   - The client's own API key usage (they know their key goes to Anthropic)
#   - An opt-in toggle in the UI per investigation
#
# TODO Month 3 Week 3: Implement this file.
