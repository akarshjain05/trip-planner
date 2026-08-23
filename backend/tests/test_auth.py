from __future__ import annotations

import uuid

import pytest


class TestRegisterAndLogin:
    @pytest.mark.asyncio
    async def test_register_returns_tokens(self, client):
        email = f"new-{uuid.uuid4().hex[:8]}@example.com"
        resp = await client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, client):
        email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        r1 = await client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
        assert r1.status_code == 201
        r2 = await client.post("/api/auth/register", json={"email": email, "password": "anotherpass123"})
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_password_too_short_rejected(self, client):
        email = f"short-{uuid.uuid4().hex[:8]}@example.com"
        resp = await client.post("/api/auth/register", json={"email": email, "password": "short"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_login_with_correct_password(self, client):
        email = f"login-{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
        resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    @pytest.mark.asyncio
    async def test_login_with_wrong_password_rejected(self, client):
        email = f"wrong-{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
        resp = await client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_current_user(self, client, registered_user):
        resp = await client.get("/api/auth/me", headers=registered_user["headers"])
        assert resp.status_code == 200
        assert resp.json()["email"] == registered_user["email"]

    @pytest.mark.asyncio
    async def test_garbage_token_rejected(self, client):
        resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        assert resp.status_code == 401


class TestUserPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_creates_default_row(self, client, registered_user):
        resp = await client.get("/api/users/me/preferences", headers=registered_user["headers"])
        assert resp.status_code == 200
        assert resp.json()["currency"] == "INR"

    @pytest.mark.asyncio
    async def test_update_preferences(self, client, registered_user):
        resp = await client.put(
            "/api/users/me/preferences",
            json={"home_city": "Mumbai", "pace": "relaxed"},
            headers=registered_user["headers"],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["home_city"] == "Mumbai"
        assert body["pace"] == "relaxed"
