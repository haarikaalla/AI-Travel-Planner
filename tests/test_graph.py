"""Graph topology and a full offline pipeline run with a stubbed LLM."""

from __future__ import annotations

import pytest

from travel_planner.graph import PARALLEL_AGENTS, _normalise_legacy, build_graph
from travel_planner.schemas import TripInput


def test_graph_compiles_with_every_agent() -> None:
    nodes = set(build_graph().get_graph().nodes)
    for agent in (
        "supervisor", "researcher", "weather", "accommodation", "activity",
        "food", "budget", "packing", "critic", "composer",
    ):
        assert agent in nodes


def test_researcher_fans_out_to_all_parallel_agents() -> None:
    edges = {(edge.source, edge.target) for edge in build_graph().get_graph().edges}
    for agent in PARALLEL_AGENTS:
        assert ("researcher", agent) in edges
        assert (agent, "packing") in edges
    assert ("packing", "critic") in edges
    assert ("critic", "composer") in edges


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("Budget ($500-1000)", "Budget"),
        ("Mid-range ($1000-3000)", "Mid-range"),
        ("Luxury ($3000+)", "Luxury"),
        ("something unrecognised", "Mid-range"),
    ],
)
def test_legacy_budget_strings_are_normalised(legacy: str, expected: str) -> None:
    assert _normalise_legacy({"destination": "Rome", "budget": legacy})["budget"] == expected


def test_full_pipeline_runs_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """With every provider unreachable the graph must still emit a complete plan.

    This is the guarantee that matters most: a user is never shown a stack trace
    because a model was slow, rate-limited or offline.
    """
    import travel_planner.agents as agents
    import travel_planner.tools as tools

    def dead_structured(prompt, schema, *, fallback=None, **_kwargs):
        assert fallback is not None, f"{schema.__name__} has no fallback"
        return fallback, "stubbed provider outage"

    monkeypatch.setattr(agents, "_invoke_structured", dead_structured)
    monkeypatch.setattr(agents, "invoke_text", lambda *_a, **kw: (kw.get("fallback", ""), "down"))
    monkeypatch.setattr(tools, "gather_context", lambda _destination: {"sources": []})
    monkeypatch.setattr(agents, "gather_context", lambda _destination: {"sources": []})

    trip = TripInput(destination="Kyoto, Japan", duration=3, travelers=2)
    result = build_graph().invoke(
        {
            "trip_input": trip.model_dump(),
            "provider": "ollama",
            "model_name": "llama3.2",
            "live_context": {},
            "messages": [],
            "errors": [],
            "timings": [],
        }
    )["final_result"]

    assert len(result["itinerary"]) == 3
    assert result["accommodations"]
    assert result["budget"]["per_person_breakdown"]
    assert result["packing"]["essentials"]
    assert result["summary"]
    assert len(result["errors"]) >= 8, "degradations must be reported, not hidden"

    # Nine timings, not ten: the composer builds the plan before emitting its
    # own timing, so it can never appear in its own output.
    timings = result["meta"]["timings"]
    assert len(timings) == 9
    assert {entry["agent"] for entry in timings} == {
        "Supervisor", "Researcher", "Weather", "Accommodation", "Activity Curator",
        "Food Guide", "Budget Planner", "Packing", "Critic",
    }
