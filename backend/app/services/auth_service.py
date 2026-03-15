# LogRaven — Auth Service
#
# PURPOSE:
#   Business logic for user authentication.
#   Route handlers call these functions — no DB access in routes.
#
# FUNCTIONS:
#   register_user(email, password, db) -> TokenResponse
#     - Validate email format (EmailStr handles this)
#     - Check email not already registered (raise 400 if taken)
#     - Hash password with bcrypt (cost factor 12)
#     - Create User record
#     - Generate JWT token pair
#     - Log registration to audit_log
#     - Return TokenResponse
#
#   login_user(email, password, db) -> TokenResponse
#     - Fetch user by email (raise 401 if not found)
#     - Verify password hash (raise 401 if wrong)
#     - Generate JWT token pair
#     - Log login to audit_log
#     - Return TokenResponse
#
#   refresh_token(refresh_token: str, db) -> dict
#     - Decode refresh token (raise 401 if invalid/expired)
#     - Fetch user (raise 401 if not found)
#     - Generate new access token
#     - Return {"access_token": ..., "token_type": "bearer"}
#
# TODO Month 1 Week 1: Implement this file.
