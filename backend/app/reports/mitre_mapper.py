# LogRaven — MITRE ATT&CK Mapper
#
# PURPOSE:
#   Enriches LogRaven findings with full MITRE ATT&CK technique data.
#   Uses the official mitreattack-python library (pip install mitreattack-python)
#   maintained by MITRE themselves — always accurate, always current.
#
# LIBRARY USAGE:
#   from mitreattack.stix20 import MitreAttackData
#   _atk = MitreAttackData('enterprise-attack.json')  # loaded ONCE at startup
#
# KEY FUNCTIONS:
#   enrich(findings) -> List[Finding]
#     For each finding with mitre_technique_id:
#     calls _atk.get_object_by_attack_id(technique_id, 'attack-pattern')
#     Adds: technique_name, tactic_name, description (first 300 chars)
#
#   get_coverage_matrix(technique_ids) -> dict
#     Returns all 14 ATT&CK tactics showing which were triggered.
#     Used for the MITRE coverage visualization in the PDF report.
#
# NOTE: MitreAttackData is loaded ONCE at module import, not per request.
#       enterprise-attack.json must be bundled in the Docker image.
#       Download from: https://github.com/mitre-attack/attack-stix-data
#
# TODO Month 4 Week 1: Implement this file.

# Load ONCE at module startup — never reload per request
_atk = None  # Will be MitreAttackData('enterprise-attack.json')


def enrich(findings: list) -> list:
    """Add full ATT&CK technique data to each finding."""
    # TODO: Implement using mitreattack-python
    return findings


def get_coverage_matrix(technique_ids: list) -> dict:
    """Build ATT&CK tactic coverage matrix showing triggered techniques."""
    # TODO: Return dict of {tactic: {name, techniques: [{id, name, triggered}]}}
    return {}
