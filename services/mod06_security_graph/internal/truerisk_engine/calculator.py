"""TrueRisk Composite Prioritization Engine (PRD-MOD-06, FR-MOD6-01, TC-MOD6-003).

Computes the 5-variable TrueRisk prioritization formula:
R_score = min(100.0, 0.25*S_IOM + 0.25*E_reach + 0.20*I_blast + 0.15*D_sens + 0.15*T_active)
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


# Domain weights
WEIGHT_S_IOM = 0.25     # Static misconfiguration / CVE severity
WEIGHT_E_REACH = 0.25   # Effective network exposure
WEIGHT_I_BLAST = 0.20   # Identity blast radius
WEIGHT_D_SENS = 0.15    # Data sensitivity (DSPM / Crown Jewel)
WEIGHT_T_ACTIVE = 0.15  # Active threat activity / IOA telemetry

# Severity lookups
SEVERITY_SCORES: Dict[str, float] = {
    "CRITICAL": 100.0,
    "HIGH": 75.0,
    "MEDIUM": 40.0,
    "LOW": 15.0,
    "INFORMATIONAL": 0.0,
    "CLEAN": 0.0,
}

EXPOSURE_SCORES: Dict[str, float] = {
    "DIRECT_INTERNET": 100.0,
    "PUBLIC_INGRESS": 100.0,
    "LOAD_BALANCER_PROXY": 60.0,
    "INTERNAL_VPC": 25.0,
    "ISOLATED": 0.0,
}

IDENTITY_SCORES: Dict[str, float] = {
    "ADMIN": 100.0,
    "ROOT": 100.0,
    "ADMINISTRATOR_ACCESS": 100.0,
    "BROAD_RW": 60.0,
    "SCOPED": 20.0,
    "NONE": 0.0,
}

DATA_SENSITIVITY_SCORES: Dict[str, float] = {
    "PII_PCI_HIPAA": 100.0,
    "CROWN_JEWEL": 100.0,
    "SENSITIVE": 100.0,
    "BUSINESS_DATA": 30.0,
    "INTERNAL": 30.0,
    "NONE": 0.0,
    "EMPTY": 0.0,
}

THREAT_ACTIVITY_SCORES: Dict[str, float] = {
    "ACTIVE_IOA": 100.0,
    "ACTIVE_EXPLOIT": 100.0,
    "BRUTE_FORCE": 100.0,
    "NONE": 0.0,
}


@dataclass
class TrueRiskInputs:
    s_iom: float = 0.0      # 0 to 100
    e_reach: float = 0.0    # 0 to 100
    i_blast: float = 0.0    # 0 to 100
    d_sens: float = 0.0     # 0 to 100
    t_active: float = 0.0   # 0 to 100


class TrueRiskCalculator:
    """Calculates TrueRisk score and risk categorization from multi-domain context."""

    @classmethod
    def compute_score(cls, inputs: TrueRiskInputs) -> float:
        """Evaluates the composite TrueRisk formula (PRD-MOD-06).
        
        R_score = min(100.0, (0.25*S_iom + 0.25*E_reach + 0.20*I_blast + 0.15*D_sens + 0.15*T_active))
        """
        raw = (
            WEIGHT_S_IOM * inputs.s_iom +
            WEIGHT_E_REACH * inputs.e_reach +
            WEIGHT_I_BLAST * inputs.i_blast +
            WEIGHT_D_SENS * inputs.d_sens +
            WEIGHT_T_ACTIVE * inputs.t_active
        )
        return min(100.0, max(0.0, raw))

    @classmethod
    def evaluate(
        cls,
        misconfig_severity: str = "CLEAN",
        network_exposure: str = "ISOLATED",
        identity_role: str = "NONE",
        data_classification: str = "NONE",
        threat_status: str = "NONE",
        custom_s_iom: Optional[float] = None,
        custom_e_reach: Optional[float] = None,
        custom_i_blast: Optional[float] = None,
        custom_d_sens: Optional[float] = None,
        custom_t_active: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Maps categorical classifications to scores and computes TrueRisk details."""
        s_iom = custom_s_iom if custom_s_iom is not None else SEVERITY_SCORES.get(misconfig_severity.upper(), 0.0)
        e_reach = custom_e_reach if custom_e_reach is not None else EXPOSURE_SCORES.get(network_exposure.upper(), 0.0)
        i_blast = custom_i_blast if custom_i_blast is not None else IDENTITY_SCORES.get(identity_role.upper(), 0.0)
        d_sens = custom_d_sens if custom_d_sens is not None else DATA_SENSITIVITY_SCORES.get(data_classification.upper(), 0.0)
        t_active = custom_t_active if custom_t_active is not None else THREAT_ACTIVITY_SCORES.get(threat_status.upper(), 0.0)

        inputs = TrueRiskInputs(
            s_iom=s_iom,
            e_reach=e_reach,
            i_blast=i_blast,
            d_sens=d_sens,
            t_active=t_active,
        )

        score_exact = cls.compute_score(inputs)
        score_rounded = round(score_exact)

        if score_rounded >= 85:
            risk_tier = "CRITICAL"
        elif score_rounded >= 65:
            risk_tier = "HIGH"
        elif score_rounded >= 30:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        return {
            "score_exact": score_exact,
            "truerisk_score": score_rounded,
            "risk_tier": risk_tier,
            "breakdown": {
                "s_iom": {"raw": s_iom, "weighted": round(WEIGHT_S_IOM * s_iom, 2)},
                "e_reach": {"raw": e_reach, "weighted": round(WEIGHT_E_REACH * e_reach, 2)},
                "i_blast": {"raw": i_blast, "weighted": round(WEIGHT_I_BLAST * i_blast, 2)},
                "d_sens": {"raw": d_sens, "weighted": round(WEIGHT_D_SENS * d_sens, 2)},
                "t_active": {"raw": t_active, "weighted": round(WEIGHT_T_ACTIVE * t_active, 2)},
            },
        }
