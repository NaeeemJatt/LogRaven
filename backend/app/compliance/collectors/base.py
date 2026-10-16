# LogRaven — Base Cloud Collector Interface
#
# Defines the contract that all cloud providers (AWS, GCP, Azure) must implement
# for evidence collection, pre-flight credential verification, and topology extraction.

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class BaseCloudCollector(ABC):
    """Abstract collector for multi-cloud compliance evidence."""

    @abstractmethod
    def verify_credentials(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Verify cloud connectivity and permissions.
        
        Returns {"healthy": bool, "error": str | None, "account_id": str | None}.
        """
        ...

    @abstractmethod
    def collect_evidence(
        self,
        credentials: dict[str, Any],
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Collect normalized cloud evidence across storage, IAM, logging, and network.
        
        Returns raw evidence dictionary ready for sanitization and signal synthesis.
        """
        ...
