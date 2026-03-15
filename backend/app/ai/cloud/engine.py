# LogRaven — Claude API Engine (Primary)
#
# PURPOSE:
#   Sends analysis requests to Claude claude-sonnet-4-6 via the official
#   Anthropic Python SDK. Primary AI engine for LogRaven v1.
#
# PRIVACY NOTE:
#   Before sending events, strip PII from raw_message fields:
#   - Replace internal hostnames with [HOST]
#   - Replace internal usernames with [USER] in raw_message only
#   (structured fields like username are kept for correlation)
#
# PROMPT CONSTRUCTION:
#   System prompt: SOC analyst persona from prompts/base_prompt.py
#   User message: structured JSON of events or correlated chains
#   Output format: STRICT JSON array only — no markdown, no commentary
#
# RETRY LOGIC:
#   3 attempts with exponential backoff: 2s, 4s, 8s delays
#   Retries on: rate limits (429), transient errors (500/503)
#   Does NOT retry on: auth errors (401), bad requests (400)
#
# COST TRACKING:
#   Log input_tokens + output_tokens per request to a simple log entry
#
# TODO Month 3 Week 3: Implement this file.

from anthropic import Anthropic

client = Anthropic()  # Reads ANTHROPIC_API_KEY from environment


async def analyze(events: list, log_type: str, user_tier: str) -> list:
    """
    Analyze events using Claude claude-sonnet-4-6.
    Returns list of finding dicts.
    """
    # TODO: Implement Claude API call with retry logic
    # TODO: Strip PII from raw_message before sending
    # TODO: Build prompt from prompts/ templates
    # TODO: Parse strict JSON response
    return []
