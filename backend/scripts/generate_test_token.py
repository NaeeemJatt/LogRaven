import asyncio
import sys
from sqlalchemy import select
from app.dependencies import AsyncSessionLocal
from app.models.user import User
from app.utils.security import create_password_reset_token

async def get_token(email: str = "operator@lograven.io") -> str:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).filter(User.email == email))
        user = res.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {email} not found")
        token = create_password_reset_token(str(user.id), user.password_hash)
        return token

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "operator@lograven.io"
    token = asyncio.run(get_token(email))
    print(token)
