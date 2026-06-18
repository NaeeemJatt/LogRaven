# LogRaven — Cloud AI Engine

import asyncio
import json

from app.ai import chunker
from app.ai.prompts import base_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy client — only initialised when GEMINI_API_KEY is present
_client = None

_VALID_SEVERITIES = {"critical", "high", "medium", "low", "informational"}


def _get_client():
    global _client
    if _client is not None:
        return _client
    # Use settings so .env values are found even before they reach os.environ
    from app.config import settings
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("LogRaven AI: API key not configured in .env — skipping AI analysis")
        return None
    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        return _client
    except ImportError:
        logger.warning("google-genai package not installed. Run: pip install google-genai")
        return None


async def _call_model(client, system_prompt: str, user_prompt: str) -> list[dict]:
    """Single AI call with 3-attempt exponential backoff."""
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
                logger.warning("AI returned empty response on attempt %d", attempt + 1)
                return []
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            # Some models wrap in {"findings": [...]}
            if isinstance(parsed, dict):
                for key in ("findings", "results", "data"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
            logger.warning("Unexpected AI response shape: %s", type(parsed))
            return []
        except json.JSONDecodeError as e:
            logger.warning("AI JSON parse error (attempt %d): %s", attempt + 1, e)
            return []
        except Exception as e:
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning("AI API error (attempt %d): %s — retrying in %ds", attempt + 1, e, wait)
            if attempt < 2:
                await asyncio.sleep(wait)
            else:
                logger.error("AI API failed after 3 attempts: %s", e)
                return []
    return []


def _normalize_findings(raw_findings: list[dict]) -> list[dict]:
    """Restrict model output to the expected schema and safe sizes."""
    normalized: list[dict] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue

        severity = str(item.get("severity", "informational")).lower()
        if severity not in _VALID_SEVERITIES:
            severity = "informational"

        iocs = item.get("iocs")
        if not isinstance(iocs, list):
            iocs = []
        safe_iocs = []
        for value in iocs[:25]:
            text = " ".join(str(value).split())
            if text:
                safe_iocs.append(text[:256])

        confidence = item.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        normalized.append({
            "severity": severity,
            "title": " ".join(str(item.get("title", "Untitled finding")).split())[:80],
            "description": " ".join(str(item.get("description", "")).split())[:600],
            "mitre_technique_id": item.get("mitre_technique_id"),
            "iocs": safe_iocs,
            "remediation": " ".join(str(item.get("remediation", "")).split())[:300],
            "confidence": confidence,
        })

    return normalized[:20]


async def analyze_events(
    events: list,
    log_type: str,
    prompt_builder,
    system_prompt: str,
    user_prompt: str,
) -> list[dict]:
    """
    Analyze events with the AI engine, chunking if needed.
    Returns merged, deduplicated findings list.
    """
    if not events:
        return []

    client = _get_client()
    if client is None:
        logger.warning("LogRaven AI: API key not set — skipping AI analysis")
        return []

    chunks = chunker.split_events(events)
    logger.info("LogRaven AI: analyzing %d events in %d chunk(s) for log_type=%s", len(events), len(chunks), log_type)

    all_chunk_findings: list[list] = []
    for i, chunk in enumerate(chunks):
        # Rebuild prompts with the same prompt family so chunking does not drop
        # log-type-specific instructions or prompt-injection defenses.
        chunk_system_prompt, chunk_user_prompt = prompt_builder(chunk)
        chunk_findings = _normalize_findings(await _call_model(client, chunk_system_prompt, chunk_user_prompt))
        logger.info("LogRaven AI: chunk %d/%d -> %d findings", i + 1, len(chunks), len(chunk_findings))
        all_chunk_findings.append(chunk_findings)

    merged = chunker.merge_findings(all_chunk_findings)
    logger.info("LogRaven AI: merged to %d findings after deduplication", len(merged))
    return merged


async def analyze_chains(chains: list) -> list[dict]:
    """Analyze correlated attack chains with the AI engine."""
    if not chains:
        return []

    client = _get_client()
    if client is None:
        logger.warning("LogRaven AI: API key not set — skipping correlation AI analysis")
        return []

    from app.ai.prompts.correlation_prompt import build_correlation_prompt
    system_prompt, user_prompt = build_correlation_prompt(chains)

    findings = _normalize_findings(await _call_model(client, system_prompt, user_prompt))
    logger.info("LogRaven AI: correlation analysis -> %d findings", len(findings))
    return findings
