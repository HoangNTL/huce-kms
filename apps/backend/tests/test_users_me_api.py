import asyncio
from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from api.core.dependencies import CurrentUser, get_current_user
from api.main import app
from api.models.user import User
from api.v1.routes.users import get_user_service


class TestUsersMeApi(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.mock_user_id = UUID("01a1e8e0-3c89-753b-b04b-04e74605a649")
        self.mock_current_user = CurrentUser(
            id=self.mock_user_id,
            username="testadmin",
            email="testadmin@huce.edu.vn",
            full_name="Test Administrator",
            role="admin",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        app.dependency_overrides[get_current_user] = lambda: self.mock_current_user

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_users_me_endpoint_returns_user_profile(self):
        async def _run():
            mock_user = User(
                id=self.mock_user_id,
                username="testadmin",
                email="testadmin@huce.edu.vn",
                full_name="Test Administrator",
                role="admin",
                is_active=True,
                hashed_password="hash",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_service = AsyncMock()
            mock_service.get_user_by_id.return_value = mock_user

            app.dependency_overrides[get_user_service] = lambda: mock_service

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/api/v1/users/me")
                self.assertEqual(res.status_code, 200)
                body = res.json()
                self.assertTrue(body["success"])
                self.assertEqual(body["data"]["id"], str(self.mock_user_id))
                self.assertEqual(body["data"]["username"], "testadmin")

        asyncio.run(_run())

    def test_get_auth_me_endpoint_returns_user_profile(self):
        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/api/v1/auth/me")
                self.assertEqual(res.status_code, 200)
                body = res.json()
                self.assertTrue(body["success"])
                self.assertEqual(body["data"]["id"], str(self.mock_user_id))
                self.assertEqual(body["data"]["username"], "testadmin")

        asyncio.run(_run())
