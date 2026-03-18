# LogRaven — MITRE ATT&CK Mapper

import os

from app.utils.logger import get_logger

logger = get_logger(__name__)

_atk_data = None
_load_attempted = False

_STIX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "enterprise-attack.json"
)


def _get_atk():
    global _atk_data, _load_attempted
    if _load_attempted:
        return _atk_data
    _load_attempted = True

    if not os.path.exists(_STIX_PATH):
        logger.info(
            "LogRaven MITRE: enterprise-attack.json not found at %s — "
            "enrichment will be skipped. See README for download instructions.",
            _STIX_PATH,
        )
        return None

    try:
        from mitreattack.stix20 import MitreAttackData
        _atk_data = MitreAttackData(_STIX_PATH)
        logger.info("LogRaven MITRE: ATT&CK data loaded from %s", _STIX_PATH)
    except ImportError:
        logger.warning(
            "mitreattack-python not installed — run: pip install mitreattack-python"
        )
    except Exception as e:
        logger.warning("LogRaven MITRE: failed to load ATT&CK data: %s", e)

    return _atk_data


def enrich_finding(finding: dict) -> dict:
    """Add MITRE technique name and tactic to a finding dict. Returns finding unchanged if not enrichable."""
    atk = _get_atk()
    technique_id = finding.get("mitre_technique_id")
    if atk is None or not technique_id:
        return finding

    try:
        obj = atk.get_object_by_attack_id(technique_id, "attack-pattern")
        if obj:
            finding = dict(finding)  # don't mutate the original
            finding["mitre_technique_name"] = obj.name
            finding["mitre_tactic"] = (
                obj.kill_chain_phases[0].phase_name
                if obj.kill_chain_phases
                else "unknown"
            )
    except Exception as e:
        logger.debug("MITRE lookup failed for %s: %s", technique_id, e)

    return finding


def enrich_all(findings: list[dict]) -> list[dict]:
    """Enrich a list of finding dicts with MITRE ATT&CK data."""
    return [enrich_finding(f) for f in findings]


def get_coverage_matrix(technique_ids: list[str]) -> dict:
    """
    Build an ATT&CK tactic coverage dict showing which techniques were triggered.
    Returns {tactic_name: [technique_id, ...]} for triggered techniques.
    """
    atk = _get_atk()
    if atk is None:
        return {}

    matrix: dict[str, list[str]] = {}
    for tid in technique_ids:
        if not tid:
            continue
        try:
            obj = atk.get_object_by_attack_id(tid, "attack-pattern")
            if obj and obj.kill_chain_phases:
                tactic = obj.kill_chain_phases[0].phase_name
                matrix.setdefault(tactic, []).append(tid)
        except Exception:
            pass
    return matrix
