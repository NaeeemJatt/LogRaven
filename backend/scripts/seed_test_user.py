import asyncio
from sqlalchemy import select
from app.dependencies import AsyncSessionLocal
from app.models.user import User
from app.utils.security import hash_password

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).filter(User.email == "operator@lograven.io"))
        u = res.scalar_one_or_none()
        if u:
            print("User operator@lograven.io already exists")
        else:
            new_u = User(
                email="operator@lograven.io",
                password_hash=hash_password("OldPassword123!"),
                email_verified=True,
                name="Security Operator",
                tier="pro"
            )
            db.add(new_u)
            await db.commit()
            print("Created user operator@lograven.io successfully")

if __name__ == "__main__":
    asyncio.run(main())
