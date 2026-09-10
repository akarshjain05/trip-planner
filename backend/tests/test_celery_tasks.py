"""
Integration tests for Celery tasks directly.
These mirror the API tests but bypass the HTTP layer for planning,
calling the Celery tasks directly using CELERY_TASK_ALWAYS_EAGER=true.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.workers.tasks import modify_trip_task, plan_trip_task, regenerate_trip_task

CANONICAL_PROMPT = (
    "I want to visit Japan for 8 days in October. My budget is Rs 350000. "
    "I like nature, anime, food and photography. I dont like crowded tourist "
    "attractions. I am traveling with one friend. I prefer comfortable hotels "
    "and dont want extremely long travel days. I am flying from Mumbai."
)


class TestCeleryTripPlanning:
    @pytest.mark.asyncio
    async def test_full_planning_flow_reaches_completed(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]

        # Call Celery task directly in a separate thread so asyncio.run doesn't fail
        await asyncio.to_thread(plan_trip_task.delay, trip_id, CANONICAL_PROMPT, False)

        # It's synchronous (in the thread), so we can just fetch the status immediately
        status_resp = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "completed"

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

        await asyncio.to_thread(plan_trip_task.delay, trip_id, prompt_without_origin, False)

        status_resp = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        status = status_resp.json()
        assert status["status"] == "awaiting_input"
        assert status["awaiting_input"] is True
        assert "origin" in (status["clarifying_question"] or "").lower()

        await asyncio.to_thread(plan_trip_task.delay, trip_id, "Mumbai", True)
        
        status_resp2 = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert status_resp2.json()["status"] == "completed"

class TestCeleryTripModification:
    @pytest.mark.asyncio
    async def test_modify_creates_new_itinerary_version(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]
        
        await asyncio.to_thread(plan_trip_task.delay, trip_id, CANONICAL_PROMPT, False)
        
        first_status = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert first_status.json()["status"] == "completed"

        first_itin = (await client.get(f"/api/trips/{trip_id}/itinerary", headers=headers)).json()

        await asyncio.to_thread(modify_trip_task.delay, trip_id, "Hotels are too expensive.")
        
        second_status = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert second_status.json()["status"] == "completed"

        second_itin = (await client.get(f"/api/trips/{trip_id}/itinerary", headers=headers)).json()
        assert second_itin["version"] > first_itin["version"]

    @pytest.mark.asyncio
    async def test_regenerate_trip(self, client, registered_user):
        headers = registered_user["headers"]
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=headers)
        trip_id = create.json()["id"]
        
        await asyncio.to_thread(plan_trip_task.delay, trip_id, CANONICAL_PROMPT, False)
        
        first_status = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert first_status.json()["status"] == "completed"

        await asyncio.to_thread(regenerate_trip_task.delay, trip_id)
        
        second_status = await client.get(f"/api/trips/{trip_id}/status", headers=headers)
        assert second_status.json()["status"] == "completed"

