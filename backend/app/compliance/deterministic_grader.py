"""
LogRaven — Deterministic (100% Non-AI) Compliance Grader (Module 07).
Calculates weighted compliance scores across controls, policies, and mandates with 0% AI calls.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.compliance.signals import EvidenceSignal
from app.rules.evaluator import evaluate_rule
from app.rules.loader import RuleLoader, get_default_rule_loader

# Exact Qualys TotalCloud criticality weights
WEIGHTS: Dict[str, float] = {
    "CRITICAL": 10.0,
    "HIGH": 7.0,
    "MEDIUM": 4.0,
    "LOW": 1.0,
}


class DeterministicComplianceGrader:
    """
    100% Non-AI compliance evaluator replacing ai_grader.py for deterministic estate scans.
    Computes exact weighted pass/fail scores per Control, Policy, and Mandate in sub-milliseconds.
    """

    def __init__(self, loader: Optional[RuleLoader] = None):
        self.loader = loader if loader is not None else get_default_rule_loader()

    def evaluate_all_without_ai(
        self,
        provider: str,
        resources_by_service: Dict[str, List[Dict[str, Any]]],
        cloudtrail_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates collected resource configurations and CloudTrail logs against all loaded rules.
        Rolls up verdicts into weighted compliance percentages for all 29 Policies and 38 Mandates.
        """
        signals: Dict[str, EvidenceSignal] = {}
        policy_scores: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"passed": 0, "failed": 0, "w_pass": 0.0, "w_total": 0.0, "failing_cids": []}
        )
        mandate_scores: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"passed": 0, "failed": 0, "w_pass": 0.0, "w_total": 0.0, "failing_cids": []}
        )

        prov_upper = provider.upper()

        for cid, rule in self.loader.rules_by_cid.items():
            if rule.provider.upper() != prov_upper:
                continue

            passed_urns: List[str] = []
            failed_urns: List[str] = []
            log_hits: List[Dict[str, Any]] = []

            # Target Source: Log Stream vs Config State
            if rule.target_source.endswith("_log"):
                for evt in cloudtrail_events:
                    if evaluate_rule(evt, rule):
                        event_id = evt.get("eventID") or f"log-{evt.get('eventName', 'event')}"
                        failed_urns.append(str(event_id))
                        log_hits.append(evt)
            else:
                svc_resources = resources_by_service.get(rule.service.upper(), [])
                for res in svc_resources:
                    urn = res.get("urn") or res.get("native_id") or "unknown_resource"
                    if evaluate_rule(res, rule):
                        # True return from evaluate_rule indicates condition matched (VIOLATION)
                        failed_urns.append(urn)
                    else:
                        passed_urns.append(urn)

            # Control status is PASS only if 0 resources or logs violated the rule
            status = "PASS" if len(failed_urns) == 0 else "FAIL"

            signals[cid] = EvidenceSignal(
                cid=cid,
                title=rule.title,
                provider=rule.provider,
                service=rule.service,
                criticality=rule.criticality,
                status=status,
                passed_resources=passed_urns,
                failing_resources=failed_urns,
                log_alerts=log_hits,
            )

            w = WEIGHTS.get(rule.criticality.upper(), 4.0)

            # Roll up to mapped Policies
            for pol in rule.policies:
                score_dict = policy_scores[pol]
                if status == "PASS":
                    score_dict["passed"] += 1
                    score_dict["w_pass"] += w
                else:
                    score_dict["failed"] += 1
                    score_dict["failing_cids"].append(cid)
                score_dict["w_total"] += w

            # Roll up to mapped Mandates
            for man in rule.mandates:
                m_dict = mandate_scores[man]
                if status == "PASS":
                    m_dict["passed"] += 1
                    m_dict["w_pass"] += w
                else:
                    m_dict["failed"] += 1
                    m_dict["failing_cids"].append(cid)
                m_dict["w_total"] += w

        total_controls = len(signals)
        passed_controls = sum(1 for s in signals.values() if s.status == "PASS")
        failed_controls = total_controls - passed_controls

        return {
            "grading_mode": "DETERMINISTIC_NON_AI",
            "provider": prov_upper,
            "total_controls_evaluated": total_controls,
            "controls_passed": passed_controls,
            "controls_failed": failed_controls,
            "controls": {k: vars(v) for k, v in signals.items()},
            "policies": {
                k: {
                    **v,
                    "score_pct": round(100.0 * v["w_pass"] / max(1.0, v["w_total"]), 2),
                }
                for k, v in policy_scores.items()
            },
            "mandates": {
                k: {
                    **v,
                    "score_pct": round(100.0 * v["w_pass"] / max(1.0, v["w_total"]), 2),
                }
                for k, v in mandate_scores.items()
            },
        }
