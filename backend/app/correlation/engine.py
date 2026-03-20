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
#   events_by_file: dict of {source_type: List[NormalizedEvent]}
#
#   ALGORITHM:
#     1. entity_extractor.extract_all(events_by_file)
#        -> {entity_value: List[EntityOccurrence]}
#     2. Filter: keep entities appearing in 2+ different source_type files
#     3. For each qualifying entity:
#        chain_builder.build_chain(entity, occurrences, time_window=300)
#        -> List[CorrelatedChain]
#     4. Score each chain:
#        - 2 source types: High
#        - 3+ source types: Critical (regardless of individual event severity)
#     5. Return sorted List[CorrelatedChain] by score descending
#
# SINGLE FILE BEHAVIOR:
#   If events_by_file has only one key, return [] immediately.
#   Single file investigations run without correlation — no error.
#
# TODO Month 3 Week 1: Implement this file.

from app.parsers.normalizer import NormalizedEvent


def analyze(investigation_id: str, events_by_file: dict) -> list:
    """
    Run LogRaven correlation analysis across multiple log source files.
    Returns list of CorrelatedChain objects. Empty list if only one file.
    """
    if len(events_by_file) < 2:
        return []

    # TODO: Implement correlation algorithm
    return []


# Alias used by process_investigation.py
correlate = analyze
