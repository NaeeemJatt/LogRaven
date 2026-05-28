# LogRaven — SOC 2 Gemini Control Mapper

from __future__ import annotations

import asyncio
import json
from typing import Any

from google.genai import types

from app.compliance.constants import SOC2_CONTROLS, SOC2_CONTROL_IDS
from app.utils.logger import get_logger

logger = get_logger(__name__)

MODEL = "gemini-2.5-flash"
GEMINI_TIMEOUT_SECONDS = 120
RETRY_DELAY_SECONDS = 5

SOC2_SYSTEM_PROMPT = """You are a SOC 2 compliance auditor with 15 years of experience.
You assess security controls against AICPA Trust Service Criteria.
You receive anonymized statistical evidence from an AWS environment.
You assess each control as PASS, FAIL, or PARTIAL based solely on the evidence provided.
PASS means the evidence clearly demonstrates the control is operating effectively.
PARTIAL means the evidence shows partial implementation with identified gaps.
FAIL means the evidence clearly shows the control is not implemented or is failing.
You respond only with valid JSON. No preamble, no markdown, no explanation outside the JSON structure."""


class MappingError(Exception):
    """Raised when Gemini returns invalid or unusable JSON for control mapping."""


def _build_user_prompt(sanitized_evidence: dict[str, Any]) -> str:
    controls_block = json.dumps(SOC2_CONTROLS, indent=2)
    evidence_block = json.dumps(sanitized_evidence, indent=2)
    return f"""Assess the following anonymized AWS evidence against each SOC 2 control listed below.

CONTROLS TO ASSESS (return one result per control, all 11 required):
{controls_block}

EVIDENCE:
{evidence_block}

Return a JSON array with exactly 11 objects. Each object must have:
- control_id (string, e.g. "CC6.1")
- control_name (string, full control name)
- status ("PASS" | "FAIL" | "PARTIAL")
- confidence ("HIGH" | "MEDIUM" | "LOW")
- evidence_references (array of strings citing specific evidence data points)
- gaps (array of strings; empty if PASS)
- ai_description (2-3 sentence professional audit report prose)
"""


def _get_client():
    from app.config import settings

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise MappingError("GEMINI_API_KEY is not configured")
    from google import genai

    return genai.Client(api_key=api_key)


def _normalize_control_result(item: dict[str, Any], fallback: dict[str, str]) -> dict[str, Any]:
    status = str(item.get("status", "PARTIAL")).upper()
    if status not in {"PASS", "FAIL", "PARTIAL"}:
        status = "PARTIAL"

    confidence = str(item.get("confidence", "LOW")).upper()
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        confidence = "LOW"

    evidence_refs = item.get("evidence_references")
    if not isinstance(evidence_refs, list):
        evidence_refs = []
    evidence_refs = [str(ref) for ref in evidence_refs if ref]

    gaps = item.get("gaps")
    if not isinstance(gaps, list):
        gaps = []
    gaps = [str(gap) for gap in gaps if gap]

    description = str(item.get("ai_description") or "").strip()
    if not description:
        description = (
            f"Assessment for {fallback['control_id']} could not be fully determined from available evidence."
        )

    return {
        "control_id": fallback["control_id"],
        "control_name": str(item.get("control_name") or fallback["control_name"]),
        "status": status,
        "confidence": confidence,
        "evidence_references": evidence_refs,
        "gaps": gaps,
        "ai_description": description,
    }


def _parse_and_validate_response(text: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = text[:500] if text else ""
        raise MappingError(f"Gemini returned invalid JSON: {exc}. Raw snippet: {snippet}") from exc

    if isinstance(parsed, dict):
        for key in ("controls", "results", "data"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break

    if not isinstance(parsed, list):
        raise MappingError(f"Expected JSON array of controls, got {type(parsed).__name__}")

    by_id = {
        str(item.get("control_id")): item
        for item in parsed
        if isinstance(item, dict) and item.get("control_id")
    }

    results: list[dict[str, Any]] = []
    for control in SOC2_CONTROLS:
        raw = by_id.get(control["control_id"])
        if raw is None:
            results.append(
                _normalize_control_result(
                    {
                        "status": "PARTIAL",
                        "confidence": "LOW",
                        "evidence_references": [],
                        "gaps": ["Control not returned by model"],
                        "ai_description": (
                            f"{control['control_name']} was not assessed by the model; manual review required."
                        ),
                    },
                    control,
                )
            )
        else:
            results.append(_normalize_control_result(raw, control))

    if len(results) != len(SOC2_CONTROLS):
        raise MappingError(f"Expected {len(SOC2_CONTROLS)} controls, got {len(results)}")

    return results


async def _call_gemini(client: Any, user_prompt: str) -> str:
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SOC2_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192,
            ),
        ),
        timeout=GEMINI_TIMEOUT_SECONDS,
    )

    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        output_tokens = getattr(usage, "candidates_token_count", None)
        if prompt_tokens is not None or output_tokens is not None:
            logger.info(
                "Gemini SOC2 mapping tokens: prompt=%s output=%s",
                prompt_tokens,
                output_tokens,
            )

    text = response.text
    if not text:
        raise MappingError("Gemini returned an empty response")
    return text


async def map_to_soc2_controls(sanitized_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Map sanitized AWS evidence to SOC 2 CC6/CC7 controls using Gemini.

    Returns a list of 11 control assessment dicts.
    """
    client = _get_client()
    user_prompt = _build_user_prompt(sanitized_evidence)

    for attempt in range(2):
        try:
            text = await _call_gemini(client, user_prompt)
            results = _parse_and_validate_response(text)
            logger.info("SOC2 mapping complete: %d controls assessed", len(results))
            return results
        except asyncio.TimeoutError as exc:
            if attempt == 0:
                logger.warning("Gemini SOC2 mapping timed out — retrying in %ds", RETRY_DELAY_SECONDS)
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise MappingError("Gemini SOC2 mapping timed out after retry") from exc
        except MappingError:
            raise
        except Exception as exc:
            if attempt == 0 and "timeout" in str(exc).lower():
                logger.warning("Gemini SOC2 mapping error — retrying in %ds: %s", RETRY_DELAY_SECONDS, exc)
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise MappingError(f"Gemini SOC2 mapping failed: {exc}") from exc

    raise MappingError("Gemini SOC2 mapping failed after retry")


def get_overall_compliance_score(control_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute aggregate pass/fail/partial counts and conservative compliance score.

    PARTIAL counts as 0 toward score_percent (conservative).
    """
    pass_count = sum(1 for item in control_results if item.get("status") == "PASS")
    fail_count = sum(1 for item in control_results if item.get("status") == "FAIL")
    partial_count = sum(1 for item in control_results if item.get("status") == "PARTIAL")
    total = len(control_results) or len(SOC2_CONTROL_IDS)
    score_percent = round((pass_count / total) * 100.0, 2) if total else 0.0

    return {
        "pass_count": pass_count,
        "fail_count": fail_count,
        "partial_count": partial_count,
        "score_percent": score_percent,
    }
