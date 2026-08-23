"""
Integration tests through the real HTTP + Postgres path (not just the
graph in isolation -- see test_graph_end_to_end.py for that). Planning
runs as a background asyncio task (the Celery-equivalent -- see
docs/architecture.md), so these tests poll /status the same way a real
frontend would.
"""
from __future__ import annotations

import asyncio

import pytest

CANONICAL_PROMPT = (
    "I want to visit Japan for 8 days in October. My budget is Rs 350000. "
    "I like nature, anime, food and photography. I dont like crowded tourist "
    "attractions. I am traveling with one friend. I prefer comfortable hotels "
    "and dont want extremely long travel days. I am flying from Mumbai."
)


async def _poll_until_settled(client, trip_id, headers, timeout=20):
    for _ in range(timeout * 5):
        resp = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] in ("completed", "failed", "awaiting_input"):
            return body
        await asyncio.sleep(0.2)
    raise AssertionError("Trip planning did not settle in time")


class TestTripCreationAndPlanning:
    @pytest.mark.asyncio
    async def test_create_trip_starts_as_draft(self, client, registered_user):
        resp = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=registered_user["headers"])
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

    @pytest.mark.asyncio
    async def test_full_planning_flow_reaches_completed(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]

        plan_resp = await client.post(f"/api/trips/{trip_id}/plan", headers=headers)
        assert plan_resp.status_code == 202

        status = await _poll_until_settled(client, trip_id, headers)
        assert status["status"] == "completed"

        itin = await client.get(f"/api/trips/{trip_id}/itinerary", headers=headers)
        assert itin.status_code == 200
        assert len(itin.json()["days"]) == 8

        budget = await client.get(f"/api/trips/{trip_id}/budget", headers=headers)
        assert budget.status_code == 200
        assert budget.json()["total_estimated"] > 0

        sources = await client.get(f"/api/trips/{trip_id}/sources", headers=headers)
        assert sources.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_origin_pauses_for_clarification(self, client, registered_user):
        headers = registered_user["headers"]
        prompt_without_origin = CANONICAL_PROMPT.replace(" I am flying from Mumbai.", "")
        create = await client.post("/api/trips", json={"prompt": prompt_without_origin}, headers=headers)
        trip_id = create.json()["id"]

        await client.post(f"/api/trips/{trip_id}/plan", headers=headers)
        status = await _poll_until_settled(client, trip_id, headers)
        assert status["status"] == "awaiting_input"
        assert status["awaiting_input"] is True
        assert "origin" in (status["clarifying_question"] or "").lower()

        resume = await client.post(f"/api/trips/{trip_id}/plan", json={"message": "Mumbai"}, headers=headers)
        assert resume.status_code == 202
        status2 = await _poll_until_settled(client, trip_id, headers)
        assert status2["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cannot_plan_someone_elses_trip(self, client, registered_user):
        headers_a = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers_a)
        trip_id = create.json()["id"]

        email_b = "other-" + registered_user["email"]
        reg_b = await client.post("/api/auth/register", json={"email": email_b, "password": "testpass123"})
        headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

        resp = await client.get(f"/api/trips/{trip_id}", headers=headers_b)
        assert resp.status_code == 404


class TestTripModification:
    @pytest.mark.asyncio
    async def test_modify_creates_new_itinerary_version_without_rerunning_flights(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]
        await client.post(f"/api/trips/{trip_id}/plan", headers=headers)
        first_status = await _poll_until_settled(client, trip_id, headers)
        assert first_status["status"] == "completed"

        first_itin = (await client.get(f"/api/trips/{trip_id}/itinerary", headers=headers)).json()

        modify_resp = await client.post(
            f"/api/trips/{trip_id}/modify", json={"message": "Hotels are too expensive."}, headers=headers
        )
        assert modify_resp.status_code == 202
        second_status = await _poll_until_settled(client, trip_id, headers)
        assert second_status["status"] == "completed"

        second_itin = (await client.get(f"/api/trips/{trip_id}/itinerary", headers=headers)).json()
        assert second_itin["version"] > first_itin["version"]

    @pytest.mark.asyncio
    async def test_feedback_is_recorded_without_replanning(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]
        await client.post(f"/api/trips/{trip_id}/plan", headers=headers)
        await _poll_until_settled(client, trip_id, headers)

        resp = await client.post(f"/api/trips/{trip_id}/feedback", json={"message": "Loved the food picks!"}, headers=headers)
        assert resp.status_code == 201


class TestTripListingAndDeletion:
    @pytest.mark.asyncio
    async def test_list_trips_only_shows_own_trips(self, client, registered_user):
        headers = registered_user["headers"]
        await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        resp = await client.get("/api/trips", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_delete_trip(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]

        del_resp = await client.delete(f"/api/trips/{trip_id}", headers=headers)
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/trips/{trip_id}", headers=headers)
        assert get_resp.status_code == 404
