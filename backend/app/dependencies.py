# LogRaven — FastAPI Dependency Injectors
#
# PURPOSE:
#   Reusable async functions injected into route handlers by FastAPI.
#
# KEY INJECTORS:
#   get_db()           — yields async SQLAlchemy session, always closes after request
#   get_storage()      — returns correct StorageBackend based on config
#   get_current_user() — validates JWT, returns authenticated User object
#   require_pro_tier() — calls get_current_user + checks tier is pro/team
#
# USAGE in routes:
#   async def my_route(db = Depends(get_db), user = Depends(get_current_user)):
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# TODO: Implement get_db()
# TODO: Implement get_storage()
# TODO: Implement get_current_user()
# TODO: Implement require_pro_tier()
