#!/usr/bin/env python3
"""
Simple script to reset admin password
"""

import asyncio
import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def main():
    # Connect to database
    conn = await asyncpg.connect(
        host='consultant_postgres',
        port=5432,
        user='postgres',
        password='postgres',
        database='consultant_matching'
    )

    try:
        # Generate hash for admin123
        password_hash = pwd_context.hash("admin123")

        # Update admin password
        result = await conn.execute("""
            UPDATE users
            SET hashed_password = $1, is_active = true
            WHERE username = 'admin'
        """, password_hash)

        print(f"Updated admin password. Result: {result}")

        # Verify the user
        user = await conn.fetchrow("""
            SELECT username, is_active, hashed_password
            FROM users
            WHERE username = 'admin'
        """)

        if user:
            print(f"User: {user['username']}, Active: {user['is_active']}")
            if pwd_context.verify("admin123", user['hashed_password']):
                print("✓ Password verification successful!")
            else:
                print("✗ Password verification failed!")
        else:
            print("Admin user not found")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())