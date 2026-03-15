# LogRaven — Auth Helper Functions
#
# PURPOSE:
#   JWT creation and validation helpers used by auth routes and dependencies.
#   These wrap the functions in utils/security.py with auth-specific logic.
#
# FUNCTIONS:
#   create_token_pair(user_id, tier) -> TokenResponse
#   verify_token_or_raise(token: str) -> dict (decoded claims)
#
# TODO Month 1 Week 1: Implement this file.
