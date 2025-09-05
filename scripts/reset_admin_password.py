#!/usr/bin/env python3
"""Reset admin password to admin123."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import get_password_hash
from app.repo import DatabaseRepository
import asyncpg


async def reset_admin_password():
    """Reset the admin password to admin123."""
    
    # Get database connection from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/consultant_matching")
    
    # Create connection
    conn = await asyncpg.connect(database_url)
    
    try:
        # Generate new password hash
        new_hash = get_password_hash("admin123")
        print(f"Generated hash: {new_hash}")
        
        # Update admin password
        result = await conn.execute(
            """
            UPDATE users 
            SET hashed_password = $1,
                password_changed_at = NOW(),
                updated_at = NOW()
            WHERE username = 'admin'
            """,
            new_hash
        )
        
        # Check if user exists, if not create it
        if result == "UPDATE 0":
            print("Admin user not found, creating...")
            await conn.execute(
                """
                INSERT INTO users (username, email, full_name, hashed_password, role)
                VALUES ('admin', 'admin@example.com', 'Administrator', $1, 'admin')
                """,
                new_hash
            )
            print("Admin user created")
        else:
            print("Admin password updated successfully")
            
        # Verify the password works
        user = await conn.fetchrow(
            "SELECT hashed_password FROM users WHERE username = 'admin'"
        )
        if user:
            from app.auth import verify_password
            if verify_password("admin123", user['hashed_password']):
                print("✓ Password verification successful!")
            else:
                print("✗ Password verification failed!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(reset_admin_password())