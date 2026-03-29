# LogRaven — Correlation Engine
#
# PURPOSE:
#   The core LogRaven feature. Finds connections between events
#   across multiple log source files by matching shared entities
#   within time windows.
#
# MAIN FUNCTION:
#   analyze(investigation_id, events_by_file) -> List[CorrelatedChain]
#
#   events_by_file: dict of {filename: List[NormalizedEvent]}
#
#   Keys MUST be unique per uploaded file (filename is the correct choice).
#   Do NOT key by source_type — multiple files of the same type (e.g. two
#   .evtx uploads) would collapse into a single bucket, making the 2-source
#   check always fail and producing zero chains.
#
#   ALGORITHM:
#     1. entity_extractor.extract_all(events_by_file)
#        -> {entity_value: List[EntityOccurrence]}
#        (EntityOccurrence.source_type == the filename key)
#     2. Filter: keep entities appearing in 2+ different file keys
#     3. For each qualifying entity:
#        chain_builder.build_chain(entity, occurrences, time_window=300)
#        -> List[CorrelatedChain]
#     4. Score each chain:
#        - 2 source files: High
#        - 3+ source files: Critical (regardless of individual event severity)
#     5. Return sorted List[CorrelatedChain] by score descending
#
# SINGLE FILE BEHAVIOR:
#   If events_by_file has only one key, return [] immediately.
#   Single file investigations run without correlation — no error.

from app.utils.logger import get_logger

logger = get_logger("lograven.correlation")


def analyze(investigation_id: str, events_by_file: dict) -> list:
    """
    Run LogRaven correlation analysis across multiple log source files.
    Returns list of CorrelatedChain objects sorted by score descending.
    Returns an empty list if fewer than two source files are present.
    """
    if len(events_by_file) < 2:
        return []

    from app.correlation.entity_extractor import extract_all
    from app.correlation.chain_builder import build_chain

    # Step 1: extract all entities across every source file
    occurrences_map = extract_all(events_by_file)
    logger.info(
        "correlation [%s]: %d distinct entities extracted from %d source files",
        investigation_id[:8],
        len(occurrences_map),
        len(events_by_file),
    )

    # Step 2: keep only entities that appear in 2+ distinct source files
    qualifying: dict[str, list] = {
        entity: occs
        for entity, occs in occurrences_map.items()
        if len({occ.source_type for occ in occs}) >= 2
    }
    logger.info(
        "correlation [%s]: %d entities qualify (present in 2+ source files)",
        investigation_id[:8],
        len(qualifying),
    )

    # Step 3: build time-windowed chains for each qualifying entity
    # Use a 30-day window for cross-file correlation — attack sample files
    # may be recorded on different days yet still represent the same campaign.
    all_chains: list = []
    for entity_value, occurrences in qualifying.items():
        chains = build_chain(entity_value, occurrences, time_window=30 * 24 * 3600)
        all_chains.extend(chains)

    # Step 4: sort by score descending (critical chains first)
    all_chains.sort(key=lambda c: c.score, reverse=True)

    logger.info(
        "correlation [%s]: %d chains produced (high=%d  critical=%d)",
        investigation_id[:8],
        len(all_chains),
        sum(1 for c in all_chains if c.severity_elevation == "high"),
        sum(1 for c in all_chains if c.severity_elevation == "critical"),
    )

    return all_chains


# Alias used by process_investigation.py
correlate = analyze
