# LogRaven — Cloud Asset Inventory Model (CSPM Asset)
#
# PURPOSE:
#   Aliases and re-exports the canonical CSPMAsset model from services.mod02_asset_crawler.

from __future__ import annotations

from services.mod02_asset_crawler.internal.repository.models import CSPMAsset

CspmAsset = CSPMAsset

__all__ = ["CspmAsset", "CSPMAsset"]
