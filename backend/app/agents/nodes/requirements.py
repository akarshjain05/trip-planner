"""Trip Requirement Agent + Missing Info Checker (spec section 4 / graph
diagram nodes 1-2). The output of requirement_extractor -- a validated
TripRequirements -- is exactly the input every downstream node consumes."""
from __future__ import annotations

from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import MissingInfoResult, TripRequirements


def _validate_and_correct_iata(req: TripRequirements) -> None:
    """Validates origin_iata and destination_iata. If they are invalid, attempts
    to look up the correct code using the city name."""
    try:
        import airportsdata
        # Load the IATA database (dict keyed by 3-letter IATA code)
        airports = airportsdata.load('IATA')
        
        def fix_code(iata: str | None, city_name: str | None) -> str | None:
            if not iata and not city_name:
                return None
                
            # If the LLM gave us an IATA code that actually exists, keep it
            if iata and iata.upper() in airports:
                return iata.upper()
                
            # Otherwise, we have an invalid IATA (like 'STQ') or it was completely missing.
            # Let's search the database for the city name to find the real one.
            if city_name:
                search_term = city_name.split(',')[0].strip().lower()
                for code, data in airports.items():
                    if data.get('city', '').lower() == search_term:
                        from app.core.logging import get_logger
                        get_logger(__name__).info(
                            "iata_autocorrect",
                            old_iata=iata,
                            new_iata=code,
                            city=city_name
                        )
                        return code
                        
            # If we couldn't find a fix, just leave it as whatever it was
            return iata

        req.origin_iata = fix_code(req.origin_iata, req.origin)
        req.destination_iata = fix_code(req.destination_iata, req.destination)
        
    except ImportError:
        pass  # Just in case airportsdata isn't installed


def make_requirement_extractor_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "requirement_extractor", "Understanding your trip request...")
        base = TripRequirements(**state["requirements"]) if state.get("requirements") else None
        prior_missing = (state.get("missing_info") or {}).get("missing_fields")
        result = await deps.orchestrator.extract_requirements(state["user_message"], base, prior_missing)
        req: TripRequirements = result.value
        
        # Validate and fix IATA codes (e.g. STQ -> STV)
        _validate_and_correct_iata(req)
        
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_completed",
                         "requirement_extractor", "Extracted your trip requirements.",
                         {"requirements": req.model_dump(mode="json")})
        return {
            "requirements": req.model_dump(mode="json"),
            **usage_update(state, result.usage),
        }
    return node


def make_missing_info_checker_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "missing_info_checker", "Checking whether anything critical is missing...")
        req = TripRequirements(**state["requirements"])
        result = await deps.orchestrator.check_missing_info(req)
        mi: MissingInfoResult = result.value
        awaiting = not mi.can_proceed
        await deps.emit(
            state["trip_id"], state["agent_run_id"], "agent_completed", "missing_info_checker",
            mi.clarifying_question if awaiting else "All required trip details are present.",
            {"missing_fields": mi.missing_fields, "awaiting_input": awaiting},
        )
        return {
            "missing_info": mi.model_dump(),
            "awaiting_input": awaiting,
            **usage_update(state, result.usage),
        }
    return node
