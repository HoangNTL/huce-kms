"""
HUCE-KMS — Initial Database Seeder (api.core.seeder)

Provisions initial baseline data for the platform:
  1. Default Super-Admin User ('admin' / 'AdminPassword2026@')
  2. Default Standard Demo User ('user' / 'UserPassword2026@')
  3. Core Academic Categories for HUCE (Quy chế đào tạo, Đồ án, Học bổng...)

Can be executed standalone via CLI:
  uv run python -m api.core.seeder
  # or
  uv run python scripts/seed.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure apps/backend/src is in pythonpath
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent.parent.parent
src_dir = backend_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.core.database import async_session_factory
from api.core.security import hash_password
from api.models.category import Category
from api.models.user import User

logger = logging.getLogger("huce_kms.seeder")


async def seed_users() -> None:
    """Seed baseline administrator and standard user accounts if not present."""
    async with async_session_factory() as session:
        # 1. Default Admin User
        admin_stmt = select(User).where(User.username == "admin").limit(1)
        res_admin = await session.execute(admin_stmt)
        admin = res_admin.scalar_one_or_none()

        if not admin:
            default_admin = User(
                username="admin",
                email="admin@huce.edu.vn",
                full_name="HUCE KMS Administrator",
                hashed_password=hash_password("AdminPassword2026@"),
                role="admin",
                is_active=True,
            )
            session.add(default_admin)
            logger.info("[SEEDER] Created default admin: 'admin' / 'AdminPassword2026@'")
            print("  ✓ Created default admin account ('admin' / 'AdminPassword2026@')")
        else:
            logger.debug("[SEEDER] Admin user 'admin' already exists.")

        # 2. Default Standard User
        user_stmt = select(User).where(User.username == "user").limit(1)
        res_user = await session.execute(user_stmt)
        demo_user = res_user.scalar_one_or_none()

        if not demo_user:
            default_user = User(
                username="user",
                email="user@huce.edu.vn",
                full_name="Standard User",
                hashed_password=hash_password("UserPassword2026@"),
                role="user",
                is_active=True,
            )
            session.add(default_user)
            logger.info("[SEEDER] Created demo user: 'user' / 'UserPassword2026@'")
            print("  ✓ Created demo standard user ('user' / 'UserPassword2026@')")
        else:
            logger.debug("[SEEDER] Standard user 'user' already exists.")

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.info("[SEEDER] Baseline users were already committed by a concurrent worker.")


async def seed_categories() -> None:
    """Seed baseline institutional document categories for HUCE."""
    initial_categories = [
        ("Quy chế đào tạo", "quy-che-dao-tao", "Các quy chế, quy định chung về đào tạo đại học và sau đại học"),
        ("Đồ án tốt nghiệp", "do-an-tot-nghiep", "Hướng dẫn, quy trình giao và bảo vệ đồ án tốt nghiệp"),
        ("Học bổng & Khen thưởng", "hoc-bong-khen-thuong", "Tiêu chuẩn xét cấp học bổng khuyến khích và khen thưởng"),
        ("Học phí & Tài chính", "hoc-phi-tai-chinh", "Quy định mức thu học phí, miễn giảm học phí và hỗ trợ chi phí"),
        ("Công tác sinh viên", "cong-tac-sinh-vien", "Sổ tay sinh viên, chế độ chính sách và hoạt động phong trào"),
        ("Khác", "khac", "Các văn bản hướng dẫn và thông báo chung khác"),
    ]

    async with async_session_factory() as session:
        created_count = 0
        for name, slug, desc in initial_categories:
            stmt = select(Category).where(Category.slug == slug).limit(1)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                session.add(Category(name=name, slug=slug, description=desc))
                created_count += 1
                logger.info("[SEEDER] Created category: '%s'", name)
                print(f"  ✓ Created category: '{name}' ({slug})")

        try:
            await session.commit()
            if created_count > 0:
                print(f"  ✓ Successfully seeded {created_count} default categories.")
        except IntegrityError:
            await session.rollback()
            logger.info("[SEEDER] Categories were already committed by a concurrent worker.")


async def seed_initial_data() -> None:
    """Run all database seeders sequentially."""
    print("\n--- Seeding Initial HUCE-KMS Baseline Data ---")
    await seed_users()
    await seed_categories()
    print("--- Database Seeding Completed Successfully ---\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(seed_initial_data())
