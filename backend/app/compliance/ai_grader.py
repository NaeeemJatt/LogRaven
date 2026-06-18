# LogRaven — Framework-agnostic AI control grader
#
# Grades a sanitized, PII-free evidence bundle against any registered framework.
# Reuses the AI client + result-normalization primitives from soc2_mapper so the
# existing SOC 2 path and its tests are untouched, while new frameworks plug in
# as pure data (frameworks/*.py).

from __future__ import annotations

import asyncio
import json
from typing import Any

from google.genai import types

from app.compliance.frameworks.base import Framework
from app.compliance.signals import select_signals
from app.compliance.soc2_mapper import (
    AI_TIMEOUT_SECONDS,
    MODEL,
    RETRY_DELAY_SECONDS,
    MappingError,
    _get_client,
    _normalize_control_result,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _system_prompt(framework: Framework) -> str:
    return (
        f"You are a compliance auditor with 15 years of experience assessing the "
        f"{framework.name} ({framework.version}) framework. "
        "You receive anonymized statistical evidence collected from an AWS environment. "
        "Assess each control as PASS, FAIL, or PARTIAL based solely on the evidence provided. "
        "PASS means the evidence clearly demonstrates the control is operating effectively. "
        "PARTIAL means partial implementation with identified gaps. "
        "FAIL means the control is not implemented or is failing. "
        "When evidence for a control is unavailable (null), assess PARTIAL and note that "
        "manual evidence is required rather than failing it. "
        "You respond only with valid JSON. No preamble, no markdown, no explanation outside the JSON."
    )


def _build_user_prompt(framework: Framework, all_signals: dict[str, Any]) -> str:
    controls_block = []
    for control in framework.controls:
        controls_block.append(
            {
                "control_id": control.control_id,
                "control_name": control.name,
                "category": control.category,
                "relevant_evidence": select_signals(all_signals, control.signals),
                "manual_control": not control.automatable,
            }
        )
    controls_json = json.dumps(controls_block, indent=2, default=str)
    count = len(framework.controls)
    return f"""Assess the following anonymized AWS evidence against each {framework.name} control listed below.

CONTROLS TO ASSESS (return exactly one result per control, all {count} required):
{controls_json}

Return a JSON array with exactly {count} objects. Each object must have:
- control_id (string, matching the control_id above)
- control_name (string, full control name)
- status ("PASS" | "FAIL" | "PARTIAL")
- confidence ("HIGH" | "MEDIUM" | "LOW")
- evidence_references (array of strings citing the specific evidence data points used)
- gaps (array of strings; empty if PASS)
- ai_description (2-3 sentence professional audit prose)
"""


def parse_and_validate(text: str, controls: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Parse the model JSON and guarantee exactly one normalized result per control."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = text[:500] if text else ""
        raise MappingError(f"AI engine returned invalid JSON: {exc}. Raw snippet: {snippet}") from exc

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
    for control in controls:
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

    if len(results) != len(controls):
        raise MappingError(f"Expected {len(controls)} controls, got {len(results)}")
    return results


async def _call_model(client: Any, system_prompt: str, user_prompt: str) -> str:
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192,
            ),
        ),
        timeout=AI_TIMEOUT_SECONDS,
    )
    text = response.text
    if not text:
        raise MappingError("AI engine returned an empty response")
    return text


async def grade_framework(framework: Framework, all_signals: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Grade a single framework against the normalized signals.

    Returns one normalized result dict per control, annotated with category and
    remediation guidance (used by the PDF, the UI, and the remediation workflow).
    """
    client = _get_client()
    system_prompt = _system_prompt(framework)
    user_prompt = _build_user_prompt(framework, all_signals)
    controls = [c.as_prompt_dict() for c in framework.controls]

    for attempt in range(2):
        try:
            text = await _call_model(client, system_prompt, user_prompt)
            results = parse_and_validate(text, controls)
            break
        except asyncio.TimeoutError as exc:
            if attempt == 0:
                logger.warning("AI grading timed out for %s — retrying in %ds", framework.id, RETRY_DELAY_SECONDS)
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise MappingError(f"AI grading for {framework.id} timed out after retry") from exc
        except MappingError:
            raise
        except Exception as exc:  # noqa: BLE001
            if attempt == 0 and "timeout" in str(exc).lower():
                logger.warning("AI grading error for %s — retrying: %s", framework.id, exc)
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            raise MappingError(f"AI grading for {framework.id} failed: {exc}") from exc
    else:  # pragma: no cover
        raise MappingError(f"AI grading for {framework.id} failed after retry")

    # Annotate with category + remediation guidance from the framework definition.
    for result in results:
        control = framework.get_control(result["control_id"])
        if control is not None:
            result["category"] = control.category
            result["automatable"] = control.automatable
            if result["status"] != "PASS" and control.guidance:
                result["remediation"] = control.guidance
    logger.info("AI grading complete for %s: %d controls assessed", framework.id, len(results))
    return results


def score_results(results: list[dict[str, Any]], total: int | None = None) -> dict[str, Any]:
    """Aggregate counts + conservative score (PARTIAL counts as 0)."""
    pass_count = sum(1 for r in results if r.get("status") == "PASS")
    fail_count = sum(1 for r in results if r.get("status") == "FAIL")
    partial_count = sum(1 for r in results if r.get("status") == "PARTIAL")
    denom = total or len(results)
    score_percent = round((pass_count / denom) * 100.0, 2) if denom else 0.0
    return {
        "pass_count": pass_count,
        "fail_count": fail_count,
        "partial_count": partial_count,
        "score_percent": score_percent,
    }
