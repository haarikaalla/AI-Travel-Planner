"""Fallbacks must produce complete, schema-valid output with no network."""

from __future__ import annotations

from travel_planner import fallbacks as fb
from travel_planner.schemas import TripInput


def test_itinerary_length_matches_duration(trip: TripInput) -> None:
    days = fb.fb_itinerary(trip)
    assert len(days) == trip.duration
    assert [day.day for day in days] == list(range(1, trip.duration + 1))


def test_every_day_has_activities(trip: TripInput) -> None:
    assert all(day.activities for day in fb.fb_itinerary(trip))


def test_three_accommodation_tiers(trip: TripInput) -> None:
    stays = fb.fb_accommodations(trip)
    assert len(stays) == 3
    assert len({stay.stars for stay in stays}) == 3
    assert all(stay.cons for stay in stays), "an option with no downside is marketing"


def test_budget_covers_every_required_key(trip: TripInput) -> None:
    breakdown = fb.fb_budget(trip).per_person_breakdown
    for key in (
        "flights_roundtrip",
        "accommodation_total",
        "food_daily",
        "activities_total",
        "total_per_person",
    ):
        assert key in breakdown


def test_budget_scales_with_tier() -> None:
    def midpoint(tier: str) -> int:
        trip = TripInput(destination="Lima", duration=7, budget=tier)
        total = fb.fb_budget(trip).per_person_breakdown["total_per_person"]
        return int(total.split("-")[0].strip().lstrip("$").replace(",", ""))

    assert midpoint("Budget") < midpoint("Mid-range") < midpoint("Luxury")


def test_packing_reacts_to_rain(trip: TripInput) -> None:
    wet = fb.fb_weather(trip)
    wet.umbrella_needed = True
    assert "rain" in " ".join(fb.fb_packing(trip, wet).clothing.outerwear).lower()

    dry = fb.fb_weather(trip)
    dry.umbrella_needed = False
    assert "rain" not in " ".join(fb.fb_packing(trip, dry).clothing.outerwear).lower()


def test_weather_uses_measured_normals_when_available(trip: TripInput) -> None:
    context = {
        "climate": {
            "annual_high_c": 20.0,
            "annual_low_c": 10.0,
            "best_months": ["April", "May", "October"],
            "wettest_month": "June",
            "driest_month": "January",
            "source": "test",
        }
    }
    weather = fb.fb_weather(trip, context)
    assert weather.best_months == ["April", "May", "October"]
    assert "20.0" in weather.temperature_range
    assert "10.0" in weather.temperature_range


def test_food_guide_is_populated(trip: TripInput) -> None:
    guide = fb.fb_food(trip)
    assert guide.must_try_dishes and guide.restaurants and guide.food_markets
