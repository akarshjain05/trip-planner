import asyncio
import sys
import os

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def main():
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User '{email}' not found. Creating a new admin user with password 'admin123'...")
            user = User(
                email=email,
                hashed_password=hash_password("admin123"),
                full_name="Admin User",
                is_admin=True
            )
            db.add(user)
            await db.commit()
            print(f"Success: Created new admin user {email}. You can log in with password: admin123")
        else:
            user.is_admin = True
            await db.commit()
            print(f"Success: Granted admin privileges to existing user {email}.")

if __name__ == "__main__":
    asyncio.run(main())
