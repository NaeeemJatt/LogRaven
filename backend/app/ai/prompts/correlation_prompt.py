# LogRaven — Correlation AI Prompt
#
# PURPOSE:
#   The most important LogRaven prompt file.
#   Used when Claude analyzes correlated event chains (multi-source findings).
#   Produces qualitatively richer findings than single-source analysis.
#
# KEY DIFFERENCE FROM STANDARD PROMPTS:
#   Standard prompts: analyze individual events in isolation
#   Correlation prompt: analyze connected chains spanning multiple sources
#
# PROMPT INSTRUCTION:
#   "These events share a common entity (IP/username/hostname) across
#    multiple log sources. They are not isolated events.
#    Identify the SINGLE ATT&CK technique that explains ALL of them together.
#    Describe the attack timeline in plain English from first to last event.
#    Assign severity based on combined evidence, not individual event severity."
#
# EXAMPLE OUTPUT:
#   A chain of powershell.exe spawn + firewall block + CloudTrail AssumeRole
#   gets a precise lateral movement technique ID (T1021.006 or T1078.004)
#   and a narrative: "Attacker spawned PowerShell on endpoint at 14:02:08,
#   attempted outbound connection blocked by firewall at 14:02:11, then
#   successfully assumed an IAM role via CloudTrail at 14:02:15,
#   suggesting credential theft and cloud pivot."
#
# TODO Month 3 Week 1: Implement this file.


def build_correlation_prompt(chains: list) -> str:
    """
    Build a prompt for analyzing correlated event chains.
    chains: List[CorrelatedChain] from correlation/chain_builder.py
    """
    # TODO: Serialize chains to JSON and build structured prompt
    return ""
