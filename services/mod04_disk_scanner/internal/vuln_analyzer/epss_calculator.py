"""Exploit Prediction Scoring System (EPSS) Probability Calculator and Enricher."""

from typing import Dict, Optional

# Sample known high-probability EPSS scores
DEFAULT_EPSS_SCORES: Dict[str, float] = {
    "CVE-2021-44228": 0.9754,  # Log4Shell
    "CVE-2022-0778": 0.9421,   # OpenSSL DoS
    "CVE-2024-21626": 0.8912,  # runc container breakout
    "CVE-2024-3094": 0.9635,   # XZ backdoor
    "CVE-2023-38606": 0.7410,
}


class EPSSCalculator:
    """Calculates and enriches vulnerabilities with EPSS exploit likelihood scores."""

    def __init__(self, overrides: Optional[Dict[str, float]] = None):
        self._scores = dict(DEFAULT_EPSS_SCORES)
        if overrides:
            self._scores.update(overrides)

    def get_score(self, cve_id: str) -> float:
        """Returns the EPSS probability score (0.0 to 1.0) for a CVE."""
        if not cve_id:
            return 0.0
        clean = cve_id.strip().upper()
        return self._scores.get(clean, 0.015)  # Default base baseline probability

    def set_score(self, cve_id: str, score: float):
        """Sets EPSS score."""
        self._scores[cve_id.strip().upper()] = min(1.0, max(0.0, float(score)))

