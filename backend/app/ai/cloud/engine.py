# LogRaven — Gemini AI Engine

import asyncio
import json
import os

from app.ai import chunker
from app.ai.prompts import base_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy client — only initialised when GEMINI_API_KEY is present
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    try:
        from google import genai
        _client = genai.Client()
        return _client
    except ImportError:
        logger.warning("google-genai package not installed. Run: pip install google-genai")
        return None


async def _call_gemini(client, system_prompt: str, user_prompt: str) -> list[dict]:
    """Single Gemini call with 3-attempt exponential backoff."""
    from google.genai import types

    for attempt in range(3):
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=8192,
                ),
            )
            text = response.text
            if not text:
                logger.warning("Gemini returned empty response on attempt %d", attempt + 1)
                return []
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            # Some models wrap in {"findings": [...]}
            if isinstance(parsed, dict):
                for key in ("findings", "results", "data"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
            logger.warning("Unexpected Gemini response shape: %s", type(parsed))
            return []
        except json.JSONDecodeError as e:
            logger.warning("Gemini JSON parse error (attempt %d): %s", attempt + 1, e)
            return []
        except Exception as e:
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning("Gemini API error (attempt %d): %s — retrying in %ds", attempt + 1, e, wait)
            if attempt < 2:
                await asyncio.sleep(wait)
            else:
                logger.error("Gemini API failed after 3 attempts: %s", e)
                return []
    return []


async def analyze_events(
    events: list,
    log_type: str,
    system_prompt: str,
    user_prompt: str,
) -> list[dict]:
    """
    Analyze events with Gemini, chunking if needed.
    Returns merged, deduplicated findings list.
    """
    if not events:
        return []

    client = _get_client()
    if client is None:
        logger.warning("LogRaven AI: GEMINI_API_KEY not set — skipping AI analysis")
        return []

    chunks = chunker.split_events(events)
    logger.info("LogRaven AI: analyzing %d events in %d chunk(s) for log_type=%s", len(events), len(chunks), log_type)

    all_chunk_findings: list[list] = []
    for i, chunk in enumerate(chunks):
        # Rebuild user prompt with this chunk's events
        chunk_user_prompt = base_prompt.build_prompt(chunk, log_type)
        chunk_findings = await _call_gemini(client, system_prompt, chunk_user_prompt)
        logger.info("LogRaven AI: chunk %d/%d -> %d findings", i + 1, len(chunks), len(chunk_findings))
        all_chunk_findings.append(chunk_findings)

    merged = chunker.merge_findings(all_chunk_findings)
    logger.info("LogRaven AI: merged to %d findings after deduplication", len(merged))
    return merged


async def analyze_chains(chains: list) -> list[dict]:
    """Analyze correlated attack chains with Gemini."""
    if not chains:
        return []

    client = _get_client()
    if client is None:
        logger.warning("LogRaven AI: GEMINI_API_KEY not set — skipping correlation AI analysis")
        return []

    from app.ai.prompts.correlation_prompt import build_correlation_prompt
    system_prompt, user_prompt = build_correlation_prompt(chains)

    findings = await _call_gemini(client, system_prompt, user_prompt)
    logger.info("LogRaven AI: correlation analysis -> %d findings", len(findings))
    return findings
