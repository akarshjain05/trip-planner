import asyncio
import sys
import os

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User

async def main():
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"Error: User with email '{email}' not found.")
            sys.exit(1)
            
        user.is_admin = True
        await db.commit()
        print(f"Success: Granted admin privileges to {email}.")

if __name__ == "__main__":
    asyncio.run(main())
