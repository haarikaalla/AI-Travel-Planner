"""
travel_graph.py — backwards-compatible facade.

The implementation now lives in the :mod:`travel_planner` package. This module
keeps the pre-2.0 import surface working:

    from travel_graph import run_travel_planner, build_graph, parse_json

New code should import from :mod:`travel_planner` directly.
"""

from __future__ import annotations

from typing import Any

from travel_planner.agents import AGENT_META, AGENTS, TravelState
from travel_planner.fallbacks import (
    fb_accommodations,
    fb_budget,
    fb_day,
    fb_food,
    fb_itinerary,
    fb_packing,
)
from travel_planner.graph import _normalise_legacy, build_graph, mermaid_diagram
from travel_planner.graph import run_travel_planner as _run_travel_planner
from travel_planner.graph import stream_travel_planner
from travel_planner.llm import get_chat_model, salvage_json
from travel_planner.schemas import TripInput


def run_travel_planner(
    trip_input: dict[str, Any],
    model_name: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """Legacy signature — ``model_name`` stays the second positional argument."""
    return _run_travel_planner(trip_input, provider=provider, model_name=model_name)


def parse_json(text: str, fallback: Any = None) -> Any:
    """Legacy name for the resilient JSON salvage parser."""
    result = salvage_json(text)
    return fallback if result is None else result


def _as_trip(payload: dict[str, Any]) -> TripInput:
    return TripInput.model_validate(_normalise_legacy(payload))


# ── Legacy fallback helpers: dict in, dict/list out ───────────────────────────


def _fb_accommodations(inp: dict[str, Any]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in fb_accommodations(_as_trip(inp))]


def _fb_day(inp: dict[str, Any], day_num: int) -> dict[str, Any]:
    return fb_day(_as_trip(inp), day_num).model_dump()


def _fb_itinerary(inp: dict[str, Any]) -> list[dict[str, Any]]:
    return [day.model_dump() for day in fb_itinerary(_as_trip(inp))]


def _fb_food(inp: dict[str, Any]) -> dict[str, Any]:
    return fb_food(_as_trip(inp)).model_dump()


def _fb_budget(inp: dict[str, Any]) -> dict[str, Any]:
    return fb_budget(_as_trip(inp)).model_dump()


def _fb_packing(inp: dict[str, Any]) -> dict[str, Any]:
    return fb_packing(_as_trip(inp)).model_dump()


get_llm = get_chat_model

__all__ = [
    "AGENTS",
    "AGENT_META",
    "TravelState",
    "TripInput",
    "build_graph",
    "get_llm",
    "mermaid_diagram",
    "parse_json",
    "run_travel_planner",
    "stream_travel_planner",
]
