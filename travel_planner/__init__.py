"""
AI Travel Planner — a multi-agent, multi-provider travel planning engine.

Public API
----------
    from travel_planner import run_travel_planner, stream_travel_planner, TripInput

Layers
------
    config      Typed settings loaded from environment / .env
    schemas     Pydantic v2 contracts every agent must satisfy
    llm         Provider-agnostic model router with structured output
    tools       Real-world data (geocoding, climate, FX, encyclopedia)
    agents      The specialist agent implementations
    graph       LangGraph wiring, checkpointing and streaming
    exporters   PDF / TXT / Markdown / ICS renderers
"""

from travel_planner.config import Settings, get_settings
from travel_planner.graph import (
    build_graph,
    run_travel_planner,
    stream_travel_planner,
)
from travel_planner.schemas import TravelPlan, TripInput

__version__ = "2.0.0"

__all__ = [
    "Settings",
    "TravelPlan",
    "TripInput",
    "__version__",
    "build_graph",
    "get_settings",
    "run_travel_planner",
    "stream_travel_planner",
]
