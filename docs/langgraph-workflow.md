# LangGraph, explained for this project

A short primer on the LangGraph mechanics this codebase leans on — for
the project-specific graph itself (nodes, the critic loop, a real worked
example), see `docs/agent-architecture.md`. This doc is about the
underlying framework behavior.

## StateGraph, nodes, and edges

A `StateGraph` is built from a state schema (here, `TripState`, a
`TypedDict`), nodes (plain async functions: `state -> partial state
update`), and edges connecting them. `graph.compile()` produces a runnable
object; `await compiled.ainvoke(initial_state, config)` runs it to
completion (or until it hits `END`).

```python
graph = StateGraph(TripState)
graph.add_node("destination_research", make_destination_research_node(deps))
graph.add_edge("destination_research", "flight_research")
```

## Supersteps and parallelism

LangGraph executes in synchronous "supersteps": all nodes whose
dependencies are satisfied run concurrently in the same step. Two static
edges out of the same node (`destination_research → flight_research` and
`destination_research → hotel_research`) means both run in parallel once
`destination_research` finishes — no explicit `asyncio.gather` needed,
this project just relies on the graph topology.

A node with **two incoming edges** (a join, like `transportation` here)
only needs *one* of its predecessors to have fired to become eligible —
it doesn't require both to complete in the same step. This is
non-obvious and matters a lot for replanning (see
`docs/agent-architecture.md`'s worked example and
`backend/tests/test_graph_topology.py`, which characterizes this
behavior directly against a minimal isolated graph rather than just
asserting it from documentation).

## Conditional edges

```python
graph.add_conditional_edges("critic", route_after_critic, {"finalize": "finalize", "replanner": "replanner"})
```

The routing function returns either a single node name or a **list** of
node names — returning a list fans out to all of them in parallel, which
is how this project's replanner jumps into multiple independent branches
at once when a critic rejection spans more than one (see
`compute_replan_targets`).

## Checkpointing

`graph.compile(checkpointer=MemorySaver())` gives LangGraph in-process
memory of state across supersteps *within one `ainvoke()` call* — this is
what makes the fan-out/fan-in and conditional-loop mechanics above work
at all. This project does **not** use the checkpointer for
cross-request/cross-process resumption; that's handled explicitly in
application code (`Trip.state_snapshot` in Postgres) instead. See
`docs/architecture.md` for why.

## A bug this project actually hit (and how it was found)

Reentering two parallel branches in the same replan, at *different
depths* from their shared join node, makes the join fire twice —
double-executing everything downstream. This was found by literally
instrumenting a real run and watching `critic`/`finalize` fire more times
than `max_iterations` should have allowed, then reproduced in isolation
with a minimal 4-node toy graph before being fixed (normalize
simultaneously-targeted branches to their root nodes, so they're always
equal depth from the join). The isolated repro is a permanent test:
`backend/tests/test_graph_topology.py::TestLangGraphFanInSemantics`.
