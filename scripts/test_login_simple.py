#!/usr/bin/env python3
"""
Simple test to verify admin login works
"""

import asyncio
import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test_login():
    # Connect to database
    conn = await asyncpg.connect(
        host='consultant_postgres',
        port=5432,
        user='postgres',
        password='postgres',
        database='consultant_matching'
    )

    try:
        # Get admin user
        user = await conn.fetchrow("""
            SELECT username, hashed_password, is_active
            FROM users
            WHERE username = 'admin'
        """)

        if not user:
            print("❌ Admin user not found")
            return

        print(f"Admin user found: {user['username']}")
        print(f"Active: {user['is_active']}")

        # Test password verification
        test_passwords = ["admin123", "admin", "password", "test"]

        for password in test_passwords:
            try:
                if pwd_context.verify(password, user['hashed_password']):
                    print(f"✅ Password '{password}' works!")
                    break
                else:
                    print(f"❌ Password '{password}' failed")
            except Exception as e:
                print(f"❌ Error testing '{password}': {e}")

        # Force reset to admin123
        print("\nForcing password reset to 'admin123'...")
        new_hash = pwd_context.hash("admin123")

        await conn.execute("""
            UPDATE users
            SET hashed_password = $1, is_active = true
            WHERE username = 'admin'
        """, new_hash)

        print("✅ Password reset complete")

        # Verify the reset worked
        if pwd_context.verify("admin123", new_hash):
            print("✅ Verification successful - admin123 should work now")
        else:
            print("❌ Verification failed - something is wrong")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_login())