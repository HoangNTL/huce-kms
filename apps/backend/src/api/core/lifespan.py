import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from api.core.config import settings
from api.core.database import Base, async_session_factory, engine
from api.core.security import hash_password
import api.models
from api.models.user import User

logger = logging.getLogger("huce_kms.lifespan")


async def seed_initial_data() -> None:
    """Seed initial administrator and demo user accounts if they do not exist."""
    async with async_session_factory() as session:
        # 1. Seed Default Admin User
        admin_stmt = select(User).where(User.username == "admin").limit(1)
        result = await session.execute(admin_stmt)
        admin = result.scalar_one_or_none()

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
            logger.info("[SEEDER] Created default admin account: 'admin' / 'AdminPassword2026@'")

        # 2. Seed Default Standard User
        user_stmt = select(User).where(User.username == "user").limit(1)
        result_user = await session.execute(user_stmt)
        demo_user = result_user.scalar_one_or_none()

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
            logger.info("[SEEDER] Created demo user account: 'user' / 'UserPassword2026@'")

        # 3. Seed Default Academic Categories
        from api.models.category import Category
        initial_categories = [
            ("Quy chế đào tạo", "quy-che-dao-tao", "Các quy chế, quy định chung về đào tạo đại học và sau đại học"),
            ("Đồ án tốt nghiệp", "do-an-tot-nghiep", "Hướng dẫn, quy trình giao và bảo vệ đồ án tốt nghiệp"),
            ("Học bổng & Khen thưởng", "hoc-bong-khen-thuong", "Tiêu chuẩn xét cấp học bổng khuyến khích và khen thưởng"),
            ("Học phí & Tài chính", "hoc-phi-tai-chinh", "Quy định mức thu học phí, miễn giảm học phí và hỗ trợ chi phí"),
            ("Công tác sinh viên", "cong-tac-sinh-vien", "Sổ tay sinh viên, chế độ chính sách và hoạt động phong trào"),
            ("Khác", "khac", "Các văn bản hướng dẫn và thông báo chung khác"),
        ]
        for name, slug, desc in initial_categories:
            cat_stmt = select(Category).where(Category.slug == slug).limit(1)
            cat_res = await session.execute(cat_stmt)
            if not cat_res.scalar_one_or_none():
                session.add(Category(name=name, slug=slug, description=desc))
                logger.info(f"[SEEDER] Created default category: '{name}'")

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage FastAPI application lifecycle (startup, data seeding, shutdown)."""
    # 1. Startup phase
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error("[STARTUP] Database schema initialization failed: %s", e)
        raise

    try:
        await seed_initial_data()
    except Exception as e:
        logger.error("[STARTUP] Initial data seeding error: %s", e)

    app.state.is_healthy = True

    # Yield control to FastAPI request handling
    yield

    # 2. Shutdown phase
    app.state.is_healthy = False
    await engine.dispose()
