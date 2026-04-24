#!/usr/bin/env python3
"""CLI script to create an admin user."""
import asyncio
import getpass
import sys

sys.path.insert(0, ".")


async def main():
    from sqlalchemy import select

    from app.admin.auth import hash_password
    from app.db.session import async_session_factory
    from app.models.admin_user import AdminUser

    print("╔══════════════════════════════╗")
    print("║  GoldVault — Create Admin    ║")
    print("╚══════════════════════════════╝\n")

    username = input("Username: ").strip()
    if not username:
        print("Error: username cannot be empty")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if len(password) < 8:
        print("Error: password must be at least 8 characters")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: passwords do not match")
        sys.exit(1)

    email = input("Email (optional): ").strip() or None
    is_super = input("Superadmin? [y/N]: ").strip().lower() == "y"

    async with async_session_factory() as db:
        existing = await db.execute(select(AdminUser).where(AdminUser.username == username))
        if existing.scalar_one_or_none():
            print(f"Error: admin '{username}' already exists")
            sys.exit(1)

        admin = AdminUser(
            username=username,
            hashed_password=hash_password(password),
            email=email,
            is_superadmin=is_super,
        )
        db.add(admin)
        await db.commit()

    print(f"\n✅ Admin '{username}' created successfully!")
    print(f"   Superadmin: {'Yes' if is_super else 'No'}")
    print("\nLog in at: http://localhost:8000/admin/login")


if __name__ == "__main__":
    asyncio.run(main())
