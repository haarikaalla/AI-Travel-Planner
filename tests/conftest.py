"""Shared fixtures. No test in this suite requires a network or an LLM."""

from __future__ import annotations

import pytest

from travel_planner.schemas import TripInput


@pytest.fixture
def trip() -> TripInput:
    return TripInput(
        destination="Kyoto, Japan",
        duration=4,
        travelers=2,
        budget="Mid-range",
        interests=["Culture & History", "Food & Cuisine"],
        travel_style="Balanced",
        special_requests="Vegetarian",
    )


@pytest.fixture
def plan(trip: TripInput) -> dict:
    """A fully-populated plan dict built entirely from deterministic fallbacks."""
    from travel_planner import fallbacks as fb
    from travel_planner.schemas import TravelPlan

    weather = fb.fb_weather(trip)
    return TravelPlan(
        summary="A deliberately short summary used for export tests.",
        overview={
            "Destination": trip.destination,
            "Duration": f"{trip.duration} days",
            "Travellers": str(trip.travelers),
            "Budget": trip.budget,
        },
        destination=fb.fb_destination(trip),
        weather=weather,
        accommodations=fb.fb_accommodations(trip),
        itinerary=fb.fb_itinerary(trip),
        food=fb.fb_food(trip),
        budget=fb.fb_budget(trip),
        packing=fb.fb_packing(trip, weather),
        review=fb.fb_review(trip),
        live_sources=["Open-Meteo Geocoding"],
        agent_log=["[Supervisor] ok"],
    ).model_dump()
