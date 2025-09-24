#!/usr/bin/env python3
"""
Create a simple admin user that will definitely work
"""

import asyncio
import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    # Connect to database
    conn = await asyncpg.connect(
        host='consultant_postgres',
        port=5432,
        user='postgres',
        password='postgres',
        database='consultant_matching'
    )

    try:
        # Delete existing admin user
        await conn.execute("DELETE FROM users WHERE username = 'admin'")
        print("Deleted existing admin user")

        # Create new admin user with simple password
        user_id = "00000000-0000-0000-0000-000000000001"
        username = "admin"
        email = "admin@test.com"
        full_name = "Administrator"
        password = "admin"  # Super simple password
        role = "admin"

        hashed_password = pwd_context.hash(password)

        await conn.execute("""
            INSERT INTO users (user_id, username, email, full_name, hashed_password, role, is_active, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, true, NOW())
        """, user_id, username, email, full_name, hashed_password, role)

        print(f"✅ Created admin user:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")

        # Verify login works
        user = await conn.fetchrow("SELECT * FROM users WHERE username = 'admin'")
        if user and pwd_context.verify(password, user['hashed_password']):
            print(f"✅ Login verification successful!")
        else:
            print(f"❌ Login verification failed!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_admin())