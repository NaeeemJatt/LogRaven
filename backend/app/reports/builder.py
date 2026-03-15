# LogRaven — Report Builder
#
# PURPOSE:
#   Assembles the final LogRaven report from all analysis outputs.
#   This is the last step before PDF generation.
#
# MAIN FUNCTION:
#   build_report(investigation, correlated_findings, single_source_findings, db) -> Report
#
# ALGORITHM:
#   1. Merge correlated and single-source findings into one list
#   2. Deduplicate: same (severity + source_ip + mitre_id) = same finding
#      On collision: keep finding with higher confidence score
#   3. Call mitre_mapper.enrich(findings) to add full technique names
#   4. Sort by severity (critical first), then confidence
#   5. Generate executive summary (plain English, 2-3 sentences)
#   6. Count severity distribution for SeverityChart
#   7. Create Report and Finding records in database
#   8. Return Report object
#
# TODO Month 4 Week 1: Implement this file.
