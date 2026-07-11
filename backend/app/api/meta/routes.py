# LogRaven — Public platform metadata
#
# GET /api/v1/meta/stats — real platform numbers for the public landing page
# (detection rule count, parser formats, distinct MITRE techniques). Public by
# design: exposes only aggregate capability counts, nothing tenant-specific.

from fastapi import APIRouter

router = APIRouter()

_stats_cache: dict | None = None


def _compute_stats() -> dict:
    from app.parsers.registry import PARSER_REGISTRY
    from app.rules.loader import get_rules

    rules = get_rules()
    techniques = {r.mitre_technique_id for r in rules if r.mitre_technique_id}
    # Distinct parser implementations (registry maps some keys to a shared class).
    parser_classes = {cls for cls in PARSER_REGISTRY.values()}
    return {
        "detection_rules": len(rules),
        "log_formats": len(PARSER_REGISTRY),
        "parser_engines": len(parser_classes),
        "mitre_techniques": len(techniques),
    }


@router.get("/stats")
async def platform_stats() -> dict:
    """Aggregate platform capability counts (cached for the process lifetime)."""
    global _stats_cache
    if _stats_cache is None:
        _stats_cache = _compute_stats()
    return _stats_cache
