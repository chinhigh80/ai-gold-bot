#!/usr/bin/env python3
"""Seed demo data for development."""
import asyncio
import sys

sys.path.insert(0, ".")


async def main():
    from app.admin.auth import hash_password
    from app.db.session import async_session_factory
    from app.models.admin_user import AdminUser
    from app.models.user import User

    async with async_session_factory() as db:
        # Demo admin
        admin = AdminUser(
            username="admin",
            hashed_password=hash_password("admin1234"),
            is_superadmin=True,
        )
        db.add(admin)

        # Demo users
        for i in range(1, 6):
            user = User(
                telegram_id=100000000 + i,
                username=f"trader{i}",
                first_name=f"Trader {i}",
                gold_grams=float(i * 10),
                balance_usd=float(i * 100),
            )
            db.add(user)

        await db.commit()

    print("✅ Demo data seeded successfully!")
    print("   Admin: admin / admin1234")
    print("   5 demo users with gold holdings")


if __name__ == "__main__":
    asyncio.run(main())
