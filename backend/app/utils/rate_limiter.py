# LogRaven — Redis-Backed Rate Limiter
#
# PURPOSE:
#   Prevents abuse of the LogRaven API.
#   Uses Redis INCR + EXPIRE for atomic sliding window counters.
#
# LIMITS:
#   Per-user daily upload limit:
#     free: 1 investigation/day
#     pro:  50 investigations/day
#     team: 200 investigations/day
#
#   Per-IP request rate (prevents API scraping):
#     100 requests/minute per IP address
#
# FUNCTIONS:
#   check_upload_rate(user_id, tier) -> (allowed: bool, remaining: int)
#   check_api_rate(ip_address) -> (allowed: bool, remaining: int)
#
# TODO Month 1 Week 3: Implement this file.

TIER_DAILY_LIMITS = {
    "free": 1,
    "pro":  50,
    "team": 200,
}
