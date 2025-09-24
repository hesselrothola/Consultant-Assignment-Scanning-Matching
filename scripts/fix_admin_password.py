#!/usr/bin/env python3
"""
Script to reset the admin password to 'admin123'
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth import get_password_hash, verify_password
from app.repo import DatabaseRepository

async def reset_admin_password():
    """Reset admin password to admin123."""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@consultant_postgres:5432/consultant_matching")

    db = DatabaseRepository(db_url)
    await db.init()

    try:
        # First check current admin user
        user = await db.get_user_by_username("admin")
        if not user:
            print("Admin user not found!")
            return

        print(f"Found admin user: {user['username']} (ID: {user['user_id']})")
        print(f"Current active status: {user['is_active']}")

        # Test current password
        test_pass = "admin123"
        current_hash = user['hashed_password']

        # Verify if admin123 already works
        if verify_password(test_pass, current_hash):
            print("✓ Password 'admin123' already works!")
        else:
            print("✗ Password 'admin123' does NOT work with current hash")
            print("Resetting password to 'admin123'...")

            # Generate new hash
            new_hash = get_password_hash(test_pass)

            # Update password in database
            query = """
                UPDATE users
                SET hashed_password = $1, is_active = true
                WHERE username = 'admin'
                RETURNING user_id, username
            """
            result = await db.pool.fetchrow(query, new_hash)

            if result:
                print(f"✓ Password reset successful for user: {result['username']}")

                # Verify the update
                updated_user = await db.get_user_by_username("admin")
                if verify_password(test_pass, updated_user['hashed_password']):
                    print("✓ Verification successful! You can now login with admin/admin123")
                else:
                    print("✗ Verification failed! Something went wrong")
            else:
                print("✗ Failed to update password")

        # Ensure user is active
        if not user['is_active']:
            print("Activating admin user...")
            await db.pool.execute(
                "UPDATE users SET is_active = true WHERE username = 'admin'"
            )
            print("✓ Admin user activated")

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(reset_admin_password())