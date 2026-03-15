# LogRaven — AI Analysis Router
#
# PURPOSE:
#   Single decision point for all AI analysis in LogRaven.
#   Routes to cloud AI (Claude) for v1.
#   Local AI (Ollama + LLaMA) is Phase 2 Enterprise feature.
#
# MAIN FUNCTION:
#   analyze(events_by_source, correlated_chains, user_tier) -> AnalysisResult
#     1. Apply cost ceiling via cost_limiter.enforce_ceiling()
#     2. Build prompts: one for correlated chains, one per source type
#     3. Call cloud/engine.py (Claude claude-sonnet-4-6)
#     4. On Claude failure: try cloud/openai_engine.py (GPT-4o)
#     5. Return merged AnalysisResult
#
# TODO Month 3 Week 3: Implement this file.
