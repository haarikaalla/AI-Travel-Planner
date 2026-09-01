"""Input validation and budget-band behaviour."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from travel_planner.schemas import BUDGET_BANDS, TripInput


def test_destination_is_normalised() -> None:
    trip = TripInput(destination="  Porto ,   Portugal  ")
    assert trip.destination == "Porto , Portugal"


def test_blank_destination_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TripInput(destination="   ")


@pytest.mark.parametrize("duration", [0, 31, -3])
def test_duration_bounds(duration: int) -> None:
    with pytest.raises(ValidationError):
        TripInput(destination="Lisbon", duration=duration)


def test_empty_interests_get_a_default() -> None:
    assert TripInput(destination="Oslo", interests=[]).interests == ["General sightseeing"]


def test_budget_band_matches_tier() -> None:
    assert TripInput(destination="Oslo", budget="Luxury").budget_band == BUDGET_BANDS["Luxury"]


def test_brief_contains_every_planning_dimension(trip: TripInput) -> None:
    brief = trip.brief()
    for fragment in ("Kyoto", "4 days", "Mid-range", "Vegetarian", "Balanced"):
        assert fragment in brief
