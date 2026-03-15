# LogRaven — Auth Routes
#
# PURPOSE:
#   HTTP route handlers for authentication.
#   All business logic lives in services/auth_service.py.
#   These handlers only: validate input, call service, return response.
#
# ENDPOINTS:
#   POST /auth/register — create account, return JWT token pair
#   POST /auth/login    — authenticate, return JWT token pair
#   POST /auth/refresh  — exchange refresh token for new access token
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import APIRouter

router = APIRouter()

# TODO: Implement register endpoint
# TODO: Implement login endpoint
# TODO: Implement refresh endpoint
