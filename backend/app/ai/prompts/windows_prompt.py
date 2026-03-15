# LogRaven — Windows Event Log AI Prompt
#
# PURPOSE:
#   Log-type-specific additions to the base prompt for Windows Event Logs.
#   Imported by base_prompt.py build_prompt() when log_type="windows_event"
#
# WINDOWS-SPECIFIC INSTRUCTIONS:
#   - Pay special attention to EventID 4625/4624 authentication chains
#   - Flag any EventID 4688 (process creation) with suspicious parent/child relationships
#   - EventID 4648 across multiple hostnames indicates lateral movement
#   - Scheduled task creation (4698/4702) is a common persistence technique
#
# TODO Month 3 Week 3: Implement this file.

WINDOWS_ADDITIONS = """
Windows Event Log specific instructions:
- Authentication chains (4625->4624) indicate successful brute force
- 4648 with multiple target hostnames = lateral movement (T1021)
- 4688 with unusual parent processes = process injection or LOLBin abuse
- 4698/4702 = scheduled task persistence (T1053.005)
"""
