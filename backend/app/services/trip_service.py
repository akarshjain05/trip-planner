"""
The service layer between the API and the agent graph.

Three entry points map onto the three ways a planning run can start
(spec sections 3, 7, and 33):
  - start_trip     : brand-new trip from a natural-language prompt
  - continue_trip   : the user answered a clarifying question (missing info)
  - modify_trip     : the user asked for a change to an existing itinerary
                       ("hotels are too expensive") -> partial replan

All three funnel into _run_graph, which builds a fresh graph + deps, runs
it, and syncs the resulting TripState into normalized Postgres tables
(dropping and recreating the regenerable research/itinerary rows -- trips
are small enough that this is simpler and safer than diffing).
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import NodeDeps
from app.agents.graph import build_trip_graph

from app.ai.orchestrator import LLMOrchestrator
from app.core.config import Settings
from app.models.agent import AgentRun, AgentRunStatus
from app.models.itinerary import Itinerary, ItineraryActivity, ItineraryDay, ItineraryStatus, TripBudget
from app.models.research import Destination, FlightOption, HotelOption, Place, ResearchSource, Restaurant
from app.models.trip import Trip, TripFeedback, TripRequirement, TripStatus
from app.schemas.domain import ModificationInterpretation, TripRequirements
from app.services.progress import emit_event
from app.tools.factory import (
    get_currency_provider,
    get_flight_provider,
    get_hotel_provider,
    get_maps_provider,
    get_places_provider,
    get_restaurant_provider,
    get_weather_provider,
    get_web_search_provider,
)


class TripService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _build_deps(self) -> NodeDeps:
        s = self.settings
        from functools import partial
        from app.db.session import AsyncSessionLocal
        
        return NodeDeps(
            settings=s,
            orchestrator=LLMOrchestrator(s),
            flight_provider=get_flight_provider(s),
            hotel_provider=get_hotel_provider(s),
            places_provider=get_places_provider(s),
            restaurant_provider=get_restaurant_provider(s),
            weather_provider=get_weather_provider(s),
            currency_provider=get_currency_provider(s),
            maps_provider=get_maps_provider(s),
            web_search_provider=get_web_search_provider(s),
            session_factory=AsyncSessionLocal,
            emit=partial(emit_event, AsyncSessionLocal),
        )

    # ------------------------------------------------------------------
    async def start_trip(self, db: AsyncSession, user_id: uuid.UUID, prompt: str) -> Trip:
        trip = Trip(
            user_id=user_id, title=prompt[:80] or "Untitled trip",
            status=TripStatus.PLANNING, original_prompt=prompt, state_snapshot={},
        )
        db.add(trip)
        await db.commit()
        await db.refresh(trip)
        return await self.plan_existing_trip(db, trip, prompt)

    async def plan_existing_trip(self, db: AsyncSession, trip: Trip, message: str, celery_task_id: str | None = None) -> Trip:
        """Runs an initial planning pass against a trip row that already
        exists (e.g. created via POST /trips as a draft). Used both by
        start_trip and directly by POST /trips/{id}/plan."""
        trip.status = TripStatus.PLANNING
        run = AgentRun(trip_id=trip.id, status=AgentRunStatus.RUNNING, trigger="initial_plan", celery_task_id=celery_task_id)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        await self._run_graph(
            db, trip, run, trigger="initial_plan", user_message=message,
            base_state=trip.state_snapshot or {},
        )
        return trip

    async def continue_trip(self, db: AsyncSession, trip: Trip, message: str, celery_task_id: str | None = None) -> Trip:
        trip.status = TripStatus.PLANNING
        run = AgentRun(trip_id=trip.id, status=AgentRunStatus.RUNNING, trigger="initial_plan", celery_task_id=celery_task_id)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        # Clear completed_nodes so requirement_extractor runs again with the new message
        # Also clear any stale missing_info state so the graph doesn't instantly end or prompt again
        base_state = trip.state_snapshot or {}
        base_state["completed_nodes"] = []
        base_state.pop("awaiting_input", None)
        base_state.pop("missing_info", None)

        await self._run_graph(
            db, trip, run, trigger="initial_plan", user_message=message,
            base_state=base_state,
        )
        return trip

    async def modify_trip(self, db: AsyncSession, trip: Trip, message: str, celery_task_id: str | None = None) -> Trip:
        deps_for_interp = self._build_deps()
        prior = trip.state_snapshot or {}
        req = TripRequirements(**(prior.get("requirements") or {}))
        result = await deps_for_interp.orchestrator.interpret_modification(message, req)
        mod: ModificationInterpretation = result.value

        merged_req = req.model_copy(update=mod.changed_fields) if mod.changed_fields else req
        targets = mod.nodes_to_rerun

        db.add(TripFeedback(
            trip_id=trip.id, message=message,
            interpreted_changes=mod.changed_fields, nodes_rerun=targets,
        ))

        run = AgentRun(trip_id=trip.id, status=AgentRunStatus.RUNNING, trigger="modification", celery_task_id=celery_task_id)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        base_state = {
            **prior,
            "requirements": merged_req.model_dump(mode="json"),
            "replan_target": targets,
            "iteration_count": 0,
            "critic_result": {},
        }
        await self._run_graph(db, trip, run, trigger="modification", user_message=message, base_state=base_state)
        return trip

    async def regenerate_trip(self, db: AsyncSession, trip: Trip, celery_task_id: str | None = None) -> Trip:
        """Full regenerate: re-run the whole research+planning pipeline (spec
        section 14's 'regenerate the whole itinerary' control), as opposed to
        modify_trip's targeted partial replan."""
        run = AgentRun(trip_id=trip.id, status=AgentRunStatus.RUNNING, trigger="modification", celery_task_id=celery_task_id)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        base_state = {
            **(trip.state_snapshot or {}),
            "replan_target": ["destination_research"],
            "iteration_count": 0,
            "critic_result": {},
            "final": False,
            "error": None,
            "tool_call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
        # Also remove completed_nodes so we start totally fresh
        base_state.pop("completed_nodes", None)
        await self._run_graph(
            db, trip, run, trigger="modification",
            user_message="(full regenerate requested)", base_state=base_state,
        )
        return trip

    # ------------------------------------------------------------------
    async def _run_graph(
        self, db: AsyncSession, trip: Trip, run: AgentRun, *, trigger: str, user_message: str, base_state: dict,
    ) -> None:
        deps = self._build_deps()
        graph = build_trip_graph(deps)

        initial_state = {
            **base_state,
            "trip_id": str(trip.id),
            "agent_run_id": str(run.id),
            "trigger": trigger,
            "user_message": user_message,
            "max_iterations": self.settings.MAX_AGENT_ITERATIONS,
        }
        if trigger == "initial_plan":
            initial_state.setdefault("requirements", {})
            initial_state["awaiting_input"] = False
        import time
        initial_state["start_time"] = time.time()

        config = {
            "configurable": {"thread_id": str(run.id)},
            # Generous relative to max_iterations so OUR loop guard is what
            # stops a runaway critic loop, not LangGraph's cruder step-count
            # safety net (each loop iteration costs several graph steps).
            "recursion_limit": 20 + self.settings.MAX_AGENT_ITERATIONS * 10,
        }

        import time
        from app.tools.cache import get_redis
        import json
        from app.agents.state import NODE_ORDER

        r = get_redis()
        
        async def _pub(type_: str, agent: str | None, msg: str | None, payload: dict = None):
            ev = {
                "type": type_,
                "agent": agent,
                "message": msg,
                "payload": payload or {},
                "ts": int(time.time() * 1000)
            }
            try:
                await r.publish(f"trip_stream:{trip.id}", json.dumps(ev))
            except Exception:
                pass

        try:
            final_state = dict(initial_state)
            async for event in graph.astream_events(initial_state, config, version="v2"):
                kind = event["event"]
                name = event["name"]
                
                if name in NODE_ORDER:
                    emoji = "⏳"
                    if "flight" in name or "transportation" in name: emoji = "✈️"
                    elif "hotel" in name or "places" in name: emoji = "🏨"
                    elif "itinerary" in name or "critic" in name: emoji = "📝"
                    
                    if kind == "on_chain_start":
                        await _pub("agent_started", name, f"{emoji} Working on {name.replace('_', ' ')}...", {})
                    elif kind == "on_chain_end":
                        await _pub("agent_completed", name, f"{emoji} Finished {name.replace('_', ' ')}.", {})
                
                if kind == "on_chain_end" and isinstance(event.get("data", {}).get("output"), dict) and "trip_id" in event["data"]["output"]:
                    final_state = event["data"]["output"]
                    
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.error_message = str(exc)[:2000]
            trip.status = TripStatus.FAILED
            await db.commit()
            await _pub("error", None, str(exc), {})
            raise

        await self._sync_state_to_db(db, trip, final_state)

        run.status = AgentRunStatus.AWAITING_INPUT if final_state.get("awaiting_input") else AgentRunStatus.COMPLETED
        trip.status = TripStatus.AWAITING_INPUT if final_state.get("awaiting_input") else TripStatus.COMPLETED
        run.iteration_count = final_state.get("iteration_count", 0)
        run.tool_call_count = final_state.get("tool_call_count", 0)
        run.input_tokens = final_state.get("input_tokens", 0)
        run.output_tokens = final_state.get("output_tokens", 0)
        run.estimated_cost_usd = final_state.get("estimated_cost_usd", 0.0)
        trip.state_snapshot = final_state

        await db.commit()

    # ------------------------------------------------------------------
    async def _sync_state_to_db(self, db: AsyncSession, trip: Trip, state: dict) -> None:
        trip_id = trip.id

        req_data = state.get("requirements") or {}
        if req_data:
            result = await db.execute(select(TripRequirement).where(TripRequirement.trip_id == trip_id))
            row = result.scalar_one_or_none()

            def _parse_date(v):
                if isinstance(v, str):
                    return date.fromisoformat(v)
                return v

            fields = {
                "origin": req_data.get("origin"), "destination": req_data.get("destination"),
                "start_date": _parse_date(req_data.get("start_date")), "end_date": _parse_date(req_data.get("end_date")),
                "duration_days": req_data.get("duration_days"), "travelers": req_data.get("travelers", 1),
                "adults": req_data.get("adults", 1), "children": req_data.get("children", 0),
                "budget_amount": req_data.get("budget_amount"), "budget_currency": req_data.get("budget_currency", "INR"),
                "travel_style": req_data.get("travel_style"), "pace": req_data.get("pace"),
                "climate_preferences": req_data.get("climate_preferences"),
                "accessibility_requirements": req_data.get("accessibility_requirements"),
                "hotel_preferences": req_data.get("hotel_preferences", []),
                "food_preferences": req_data.get("food_preferences", []),
                "activity_preferences": req_data.get("activity_preferences", []),
                "transportation_preferences": req_data.get("transportation_preferences", []),
                "must_see": req_data.get("must_see", []), "avoid": req_data.get("avoid", []),
                "priorities": req_data.get("priorities", []),
                "missing_fields": (state.get("missing_info") or {}).get("missing_fields", []),
            }
            if row:
                for k, v in fields.items():
                    setattr(row, k, v)
            else:
                db.add(TripRequirement(trip_id=trip_id, **fields))

        if state.get("destination_result"):
            await db.execute(delete(Destination).where(Destination.trip_id == trip_id))
            for c in state["destination_result"].get("candidates", []):
                db.add(Destination(
                    trip_id=trip_id, name=c["name"], country=c.get("country"),
                    rank=c.get("rank", 1), reasons=c.get("reasons"),
                    suitability_score=c.get("suitability_score"), is_mock=self.settings.use_mock_llm,
                ))

        if state.get("research_sources"):
            await db.execute(delete(ResearchSource).where(ResearchSource.agent_run_id == uuid.UUID(state["agent_run_id"])))
            for s in state["research_sources"]:
                db.add(ResearchSource(
                    agent_run_id=uuid.UUID(state["agent_run_id"]), url=s["url"], title=s.get("title"),
                    source=s.get("source"), extracted_facts=s.get("extracted_facts"),
                    confidence=s.get("confidence", 0.5),
                ))

        if "flights" in state:
            await db.execute(delete(FlightOption).where(FlightOption.trip_id == trip_id))
            for f in state.get("flights", []):
                db.add(FlightOption(
                    trip_id=trip_id, provider=f["provider"], origin=f["origin"], destination=f["destination"],
                    depart_at=f["depart_at"], return_at=f.get("return_at"), airline=f.get("airline"),
                    price=f["price"], currency=f.get("currency", "INR"), duration_minutes=f.get("duration_minutes"),
                    stops=f.get("stops", 0), cabin=f.get("cabin", "economy"), baggage=f.get("baggage"),
                    raw_data=f, is_mock=f.get("is_mock", True),
                ))

        if "hotels" in state:
            await db.execute(delete(HotelOption).where(HotelOption.trip_id == trip_id))
            for h in state.get("hotels", []):
                db.add(HotelOption(
                    trip_id=trip_id, provider=h["provider"], name=h["name"], location=h.get("location"),
                    price_per_night=h["price_per_night"], currency=h.get("currency", "INR"), rating=h.get("rating"),
                    distance_from_center_km=h.get("distance_from_center_km"), amenities=h.get("amenities", []),
                    raw_data=h, is_mock=h.get("is_mock", True),
                ))

        if "places" in state:
            await db.execute(delete(Place).where(Place.trip_id == trip_id))
            for p in state.get("places", []):
                db.add(Place(
                    trip_id=trip_id, name=p["name"], category=p.get("category"), description=p.get("description"),
                    rating=p.get("rating"), estimated_visit_minutes=p.get("estimated_visit_minutes"),
                    estimated_cost=p.get("estimated_cost"), opening_hours=p.get("opening_hours"),
                    crowd_level=p.get("crowd_level"), is_mock=p.get("is_mock", True),
                ))

        if "restaurants" in state:
            await db.execute(delete(Restaurant).where(Restaurant.trip_id == trip_id))
            for r in state.get("restaurants", []):
                db.add(Restaurant(
                    trip_id=trip_id, name=r["name"], cuisine=r.get("cuisine"), price_level=r.get("price_level"),
                    description=r.get("description"), rating=r.get("rating"), is_mock=r.get("is_mock", True),
                ))

        if state.get("itinerary"):
            itin_data = state["itinerary"]
            critic = state.get("critic_result") or {}
            result = await db.execute(select(func.max(Itinerary.version)).where(Itinerary.trip_id == trip_id))
            next_version = (result.scalar() or 0) + 1

            itinerary_row = Itinerary(
                trip_id=trip_id, version=next_version,
                status=ItineraryStatus.APPROVED if critic.get("approved") else ItineraryStatus.NEEDS_REVISION,
                total_estimated_cost=itin_data.get("total_estimated_cost"),
                currency=itin_data.get("currency", "INR"),
                critic_notes="; ".join(i["description"] for i in critic.get("issues", [])) or None,
            )
            db.add(itinerary_row)
            await db.flush()

            for day in itin_data.get("days", []):
                day_date = day.get("date")
                if isinstance(day_date, str):
                    day_date = date.fromisoformat(day_date)
                day_row = ItineraryDay(
                    itinerary_id=itinerary_row.id, day_number=day["day_number"], date=day_date,
                    title=day.get("title"), weather_summary=day.get("weather_summary"),
                )
                db.add(day_row)
                await db.flush()
                for i, act in enumerate(day.get("activities", [])):
                    db.add(ItineraryActivity(
                        itinerary_day_id=day_row.id, order_index=i, time=act.get("time"),
                        activity_type=act["activity_type"], title=act["title"], description=act.get("description"),
                        location=act.get("location"), estimated_cost=act.get("estimated_cost"),
                        duration_minutes=act.get("duration_minutes"), source_ref=act.get("source_ref"),
                    ))

            budget_data = state.get("budget") or {}
            for line in budget_data.get("lines", []):
                db.add(TripBudget(
                    itinerary_id=itinerary_row.id, category=line["category"],
                    estimated_amount=line["estimated_amount"], currency=line.get("currency", "INR"),
                ))

        await db.commit()
