# LogRaven — Framework-agnostic AI control grader
#
# Grades a sanitized, PII-free evidence bundle against any registered framework.
# Frameworks plug in as pure data (frameworks/*.py); SOC 2 is just one of them.

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from google.genai import types

from app.compliance.frameworks.base import Framework
from app.compliance.signals import select_signals
from app.utils.logger import get_logger

logger = get_logger(__name__)

MODEL = "gemini-2.5-flash"
AI_TIMEOUT_SECONDS = 120
RETRY_DELAY_SECONDS = 5


class MappingError(Exception):
    """Raised when the AI engine returns invalid or unusable JSON for control grading."""


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
        "You respond only with valid JSON. No preamble, no markdown, no explanation outside the JSON. "
        "CRITICAL: Escape all internal double quotes inside string values (use \" or single quotes)."
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


def _clean_json_text(text: str) -> str:
    """Strip markdown fences, leading/trailing fluff, and trailing commas."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    return cleaned


def _extract_control_blocks(text: str) -> list[str]:
    """Extract individual JSON object blocks delimited by balanced braces."""
    blocks: list[str] = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                block = text[start : i + 1].strip()
                if '"control_id"' in block:
                    blocks.append(block)
                start = -1
    return blocks


def _salvage_control_block(snippet: str) -> dict[str, Any] | None:
    """Attempt tolerant parsing or regex field extraction for an individual control item."""
    cleaned = re.sub(r",\s*([\]}])", r"\1", snippet)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and data.get("control_id"):
            return data
    except Exception:
        pass

    # Regex salvage of standard fields if unescaped quotes broke json.loads
    cid_match = re.search(r'"control_id"\s*:\s*"([^"]+)"', snippet)
    if not cid_match:
        return None
    cid = cid_match.group(1).strip()

    status_match = re.search(r'"status"\s*:\s*"(PASS|FAIL|PARTIAL|SUPPRESSED)"', snippet, re.IGNORECASE)
    status = status_match.group(1).upper() if status_match else "PARTIAL"

    conf_match = re.search(r'"confidence"\s*:\s*"(HIGH|MEDIUM|LOW)"', snippet, re.IGNORECASE)
    conf = conf_match.group(1).upper() if conf_match else "LOW"

    name_match = re.search(r'"control_name"\s*:\s*"([^"]+)"', snippet)
    name = name_match.group(1).strip() if name_match else ""

    desc = ""
    desc_match = re.search(r'"ai_description"\s*:\s*"(.*?)"(?:\s*,\s*"\w+"\s*:|\s*\})', snippet, re.DOTALL)
    if desc_match:
        desc = desc_match.group(1).strip()
    else:
        desc_match_greedy = re.search(r'"ai_description"\s*:\s*"(.*)"\s*\}', snippet, re.DOTALL)
        if desc_match_greedy:
            desc = desc_match_greedy.group(1).strip()

    gaps = []
    gaps_match = re.search(r'"gaps"\s*:\s*\[(.*?)\]', snippet, re.DOTALL)
    if gaps_match:
        gaps = [re.sub(r'["\']', "", g).strip() for g in gaps_match.group(1).split(",") if g.strip()]

    refs = []
    refs_match = re.search(r'"evidence_references"\s*:\s*\[(.*?)\]', snippet, re.DOTALL)
    if refs_match:
        refs = [re.sub(r'["\']', "", r).strip() for r in refs_match.group(1).split(",") if r.strip()]

    return {
        "control_id": cid,
        "control_name": name,
        "status": status,
        "confidence": conf,
        "evidence_references": refs,
        "gaps": gaps,
        "ai_description": desc,
    }


def parse_and_validate(text: str, controls: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Parse the model JSON and guarantee exactly one normalized result per control."""
    cleaned = _clean_json_text(text)
    parsed = None

    # Attempt 1: Direct JSON load
    try:
        parsed = json.loads(cleaned)
    except Exception:
        pass

    # Attempt 2: Extract array substring between outer brackets
    if parsed is None:
        start_bracket = cleaned.find("[")
        end_bracket = cleaned.rfind("]")
        if start_bracket != -1 and end_bracket > start_bracket:
            array_candidate = cleaned[start_bracket : end_bracket + 1]
            array_candidate = re.sub(r",\s*([\]}])", r"\1", array_candidate)
            try:
                parsed = json.loads(array_candidate)
            except Exception:
                pass

    # Attempt 3: Object-level block extraction and regex repair
    if parsed is None or not isinstance(parsed, list):
        blocks = _extract_control_blocks(cleaned)
        salvaged = []
        for b in blocks:
            item = _salvage_control_block(b)
            if item:
                salvaged.append(item)
        if salvaged:
            parsed = salvaged

    if parsed is None:
        snippet = text[:500] if text else ""
        raise MappingError(f"AI engine returned invalid JSON. Raw snippet: {snippet}")

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


def evaluate_framework_deterministically(
    framework: Framework, all_signals: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Deterministic rule-based fallback based strictly on collected telemetry signals.
    Guarantees the audit completes with accurate evidence references and scores
    even if the AI API is rate-limited, times out, or fails to return valid JSON.
    """
    results: list[dict[str, Any]] = []

    for control in framework.controls:
        if not control.automatable or not control.signals:
            results.append(
                {
                    "control_id": control.control_id,
                    "control_name": control.name,
                    "status": "PARTIAL",
                    "confidence": "LOW",
                    "evidence_references": [],
                    "gaps": [control.guidance or "Manual policy documentation and procedural audit required."],
                    "ai_description": (
                        f"{control.name} requires organizational policy documentation and manual administrative review."
                    ),
                }
            )
            continue

        refs: list[str] = []
        gaps: list[str] = []
        signal_statuses: list[str] = []

        for sig_key in control.signals:
            val = all_signals.get(sig_key)
            if val is None:
                refs.append(f"{sig_key} = null")
                signal_statuses.append("PARTIAL")
                gaps.append(f"Telemetry for {sig_key} is unavailable")
                continue

            refs.append(f"{sig_key} = {val}")

            if isinstance(val, bool):
                if val:
                    signal_statuses.append("PASS")
                else:
                    signal_statuses.append("FAIL")
                    gaps.append(control.guidance or f"{sig_key} is disabled")
            elif isinstance(val, (int, float)):
                if "rate" in sig_key or "enforcement" in sig_key:
                    if val >= 100.0:
                        signal_statuses.append("PASS")
                    elif val >= 70.0:
                        signal_statuses.append("PARTIAL")
                        gaps.append(f"{sig_key} ({val:.1f}%) is below 100% full coverage")
                    else:
                        signal_statuses.append("FAIL")
                        gaps.append(f"{sig_key} ({val:.1f}%) fails minimum threshold")
                elif sig_key in (
                    "guardduty_high_severity_findings",
                    "open_security_groups",
                    "access_analyzer_external_findings",
                ):
                    if val == 0:
                        signal_statuses.append("PASS")
                    else:
                        signal_statuses.append("FAIL")
                        gaps.append(f"{val} findings detected for {sig_key}")
                elif sig_key == "iam_password_min_length":
                    if val >= 14:
                        signal_statuses.append("PASS")
                    elif val >= 8:
                        signal_statuses.append("PARTIAL")
                        gaps.append(f"Password minimum length ({val}) is less than recommended 14")
                    else:
                        signal_statuses.append("FAIL")
                        gaps.append(f"Password minimum length ({val}) is insufficient")
                elif sig_key == "cloudwatch_log_retention_days":
                    if val >= 365:
                        signal_statuses.append("PASS")
                    elif val >= 90:
                        signal_statuses.append("PARTIAL")
                        gaps.append(f"Log retention ({val} days) is less than 365 days")
                    else:
                        signal_statuses.append("FAIL")
                        gaps.append(f"Log retention ({val} days) is insufficient")
                else:
                    signal_statuses.append("PASS" if val > 0 else "PARTIAL")
            else:
                signal_statuses.append("PARTIAL")

        if all(s == "PASS" for s in signal_statuses):
            overall_status = "PASS"
            confidence = "HIGH"
            desc = f"Evidence verifies {control.name} is fully operating in accordance with compliance baseline."
            gaps = []
        elif any(s == "FAIL" for s in signal_statuses):
            overall_status = "FAIL"
            confidence = "HIGH"
            desc = f"Telemetry reveals non-compliance for {control.name}. Gaps require remediation."
        else:
            overall_status = "PARTIAL"
            confidence = "MEDIUM"
            desc = f"Partial compliance observed for {control.name}; further evidence or remediation required."

        results.append(
            {
                "control_id": control.control_id,
                "control_name": control.name,
                "status": overall_status,
                "confidence": confidence,
                "evidence_references": refs,
                "gaps": gaps,
                "ai_description": desc,
            }
        )

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
    client = None
    try:
        client = _get_client()
    except Exception as exc:
        logger.warning(
            "AI client initialization failed for %s (%s). Using deterministic signal evaluation.",
            framework.id,
            exc,
        )

    results: list[dict[str, Any]] | None = None
    if client is not None:
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
                logger.error(
                    "AI grading for %s timed out after retry; falling back to deterministic evaluation: %s",
                    framework.id,
                    exc,
                )
                break
            except MappingError as exc:
                if attempt == 0:
                    logger.warning(
                        "AI grading returned invalid data for %s (attempt 0): %s — retrying in %ds",
                        framework.id,
                        exc,
                        RETRY_DELAY_SECONDS,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                logger.error(
                    "AI grading for %s failed to parse after retry: %s; falling back to deterministic evaluation.",
                    framework.id,
                    exc,
                )
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 0 and "timeout" in str(exc).lower():
                    logger.warning("AI grading error for %s — retrying: %s", framework.id, exc)
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                logger.error(
                    "AI grading error for %s: %s; falling back to deterministic evaluation.",
                    framework.id,
                    exc,
                )
                break

    if results is None:
        logger.info("Evaluating framework %s using deterministic signal engine", framework.id)
        results = evaluate_framework_deterministically(framework, all_signals)

    # Annotate with category + remediation guidance + actionable guide from catalog.
    from app.compliance.remediation import get_remediation_guide

    for result in results:
        control = framework.get_control(result["control_id"])
        if control is not None:
            result["category"] = control.category
            result["automatable"] = control.automatable
            if result["status"] != "PASS":
                if control.guidance:
                    result["remediation"] = control.guidance
                guide = get_remediation_guide(
                    control_id=control.control_id,
                    signals=control.signals,
                    control_name=control.name,
                    guidance=control.guidance,
                )
                result["remediation_guide"] = guide.model_dump()
    logger.info("Compliance grading complete for %s: %d controls assessed", framework.id, len(results))
    return results


def score_results(results: list[dict[str, Any]], total: int | None = None) -> dict[str, Any]:
    """Aggregate counts + conservative score (PARTIAL counts as 0, SUPPRESSED adjusted)."""
    pass_count = sum(1 for r in results if r.get("status") == "PASS")
    suppressed_count = sum(1 for r in results if r.get("status") == "SUPPRESSED")
    fail_count = sum(1 for r in results if r.get("status") == "FAIL")
    partial_count = sum(1 for r in results if r.get("status") == "PARTIAL")
    denom = total or len(results)
    raw_score_percent = round((pass_count / denom) * 100.0, 2) if denom else 0.0
    effective_denom = max(denom - suppressed_count, 1)
    score_percent = round((pass_count / effective_denom) * 100.0, 2) if effective_denom else 0.0
    return {
        "pass_count": pass_count,
        "suppressed_count": suppressed_count,
        "fail_count": fail_count,
        "partial_count": partial_count,
        "raw_score_percent": raw_score_percent,
        "score_percent": score_percent,
    }
