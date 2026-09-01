"""
graph.py — LangGraph wiring, execution and streaming.

Topology
--------
::

    supervisor ──► researcher ──┬──► weather ───────┐
                                ├──► accommodation ─┤
                                ├──► activity ──────┼──► packing ──► critic ──► composer ──► END
                                ├──► food ──────────┤
                                └──► budget ────────┘

The five middle agents are independent, so LangGraph runs them as a concurrent
superstep and merges their writes through the ``operator.add`` reducers declared
on :class:`~travel_planner.agents.TravelState`. ``packing`` is deliberately
downstream of ``weather`` because it consumes the climate result, and ``critic``
is downstream of everything so it can review a complete draft.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from langgraph.graph import END, StateGraph

from travel_planner.agents import AGENT_META, AGENTS, TravelState
from travel_planner.config import get_settings
from travel_planner.schemas import TravelPlan, TripInput

logger = logging.getLogger(__name__)

#: Agents that may execute concurrently after the researcher completes.
PARALLEL_AGENTS = ("weather", "accommodation", "activity", "food", "budget")


def build_graph(checkpointer: Any | None = None) -> Any:
    """Compile the agent graph. Pass a checkpointer to enable resumable runs."""
    graph = StateGraph(TravelState)

    for name, fn in AGENTS.items():
        graph.add_node(name, fn)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "researcher")

    for name in PARALLEL_AGENTS:
        graph.add_edge("researcher", name)
        graph.add_edge(name, "packing")

    graph.add_edge("packing", "critic")
    graph.add_edge("critic", "composer")
    graph.add_edge("composer", END)

    return graph.compile(checkpointer=checkpointer) if checkpointer else graph.compile()


def _initial_state(
    trip_input: dict[str, Any] | TripInput,
    provider: str | None,
    model_name: str | None,
) -> TravelState:
    settings = get_settings()
    trip = (
        trip_input
        if isinstance(trip_input, TripInput)
        else TripInput.model_validate(_normalise_legacy(trip_input))
    )
    chosen_provider = (provider or settings.llm_provider).lower()
    return {
        "trip_input": trip.model_dump(),
        "provider": chosen_provider,
        "model_name": model_name or settings.default_model_for(chosen_provider),
        "live_context": {},
        "messages": [],
        "errors": [],
        "timings": [],
    }


def _normalise_legacy(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept the pre-2.0 input shape (``'Mid-range ($1000-3000)'`` etc.)."""
    data = dict(payload)
    budget = str(data.get("budget", "Mid-range"))
    for tier in ("Budget", "Mid-range", "Luxury"):
        if budget.startswith(tier):
            data["budget"] = tier
            break
    else:
        data["budget"] = "Mid-range"
    return data


# ─────────────────────────────────────────────────────────────
#  Execution
# ─────────────────────────────────────────────────────────────


def run_travel_planner(
    trip_input: dict[str, Any] | TripInput,
    provider: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Run the full pipeline to completion and return the plan as a dict."""
    graph = build_graph()
    final = graph.invoke(_initial_state(trip_input, provider, model_name))
    return final.get("final_result", {})


def stream_travel_planner(
    trip_input: dict[str, Any] | TripInput,
    provider: str | None = None,
    model_name: str | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(agent_name, state_update)`` as each agent finishes.

    This is what powers the live tracker in the UI — real progress driven by
    real completions, not a timer. The final tuple is always
    ``("composer", {...})`` carrying ``final_result``.
    """
    graph = build_graph()
    for chunk in graph.stream(
        _initial_state(trip_input, provider, model_name), stream_mode="updates"
    ):
        yield from chunk.items()


def plan_from_result(result: dict[str, Any]) -> TravelPlan:
    """Re-hydrate a validated :class:`TravelPlan` from a serialised result."""
    return TravelPlan.model_validate(result)


def mermaid_diagram() -> str:
    """Return the compiled graph as Mermaid source (used by the README/UI)."""
    try:
        return build_graph().get_graph().draw_mermaid()
    except Exception as exc:  # pragma: no cover - drawing is cosmetic
        logger.debug("Mermaid render unavailable: %s", exc)
        return ""


__all__ = [
    "AGENT_META",
    "PARALLEL_AGENTS",
    "build_graph",
    "mermaid_diagram",
    "plan_from_result",
    "run_travel_planner",
    "stream_travel_planner",
]
