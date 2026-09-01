"""
schemas.py — the typed contract between every agent and the rest of the system.

These models are handed directly to ``llm.with_structured_output(...)``, so the
field descriptions double as prompt instructions. Validation happens at the
boundary, which means no downstream code ever needs to guard against a missing
key or a string where a list was expected.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

# ─────────────────────────────────────────────────────────────
#  Input
# ─────────────────────────────────────────────────────────────

BudgetTier = Literal["Budget", "Mid-range", "Luxury"]

TravelStyle = Literal[
    "Balanced",
    "Packed (max activities)",
    "Relaxed (slow travel)",
    "Off-the-beaten-path",
    "Family-friendly",
    "Solo & social",
]

#: Budget tier → (low, high) USD per person for a one-week trip.
BUDGET_BANDS: dict[str, tuple[int, int]] = {
    "Budget": (500, 1000),
    "Mid-range": (1000, 3000),
    "Luxury": (3000, 8000),
}


class TripInput(BaseModel):
    """Everything the user tells us about the trip they want."""

    destination: Annotated[str, Field(min_length=2, max_length=120)]
    duration: Annotated[int, Field(ge=1, le=30)] = 5
    travelers: Annotated[int, Field(ge=1, le=20)] = 2
    budget: BudgetTier = "Mid-range"
    interests: list[str] = Field(default_factory=lambda: ["Culture & History"])
    travel_style: TravelStyle = "Balanced"
    special_requests: str = "None"
    start_month: str | None = None

    @field_validator("destination")
    @classmethod
    def _clean_destination(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("destination must not be blank")
        return cleaned

    @field_validator("interests")
    @classmethod
    def _at_least_one_interest(cls, value: list[str]) -> list[str]:
        return value or ["General sightseeing"]

    @property
    def budget_band(self) -> tuple[int, int]:
        return BUDGET_BANDS[self.budget]

    def brief(self) -> str:
        """Compact one-paragraph restatement injected into every prompt."""
        return (
            f"Destination: {self.destination}\n"
            f"Duration: {self.duration} days\n"
            f"Travelers: {self.travelers}\n"
            f"Budget tier: {self.budget} "
            f"(~${self.budget_band[0]}-${self.budget_band[1]} per person)\n"
            f"Interests: {', '.join(self.interests)}\n"
            f"Travel style: {self.travel_style}\n"
            f"Special requests: {self.special_requests}"
        )


# ─────────────────────────────────────────────────────────────
#  Agent outputs
# ─────────────────────────────────────────────────────────────


class DestinationBrief(BaseModel):
    """Agent 2 — grounded destination intelligence."""

    essence: str = Field(description="2-3 sentences on what makes this place special")
    best_neighborhoods: list[str] = Field(
        default_factory=list,
        description="3 areas to stay, each as 'Name — one-line reason'",
    )
    iconic_attractions: list[str] = Field(
        default_factory=list,
        description="5 must-see places, each as 'Name — insider tip'",
    )
    getting_around: str = Field(default="", description="Transport options with costs")
    culture_customs: list[str] = Field(
        default_factory=list, description="3 etiquette tips that actually matter"
    )
    safety_notes: list[str] = Field(
        default_factory=list, description="2-3 practical safety tips"
    )
    ideal_timing: str = Field(default="", description="Best season to visit and why")
    language_phrases: list[str] = Field(
        default_factory=list,
        description="4 useful local phrases as 'phrase — meaning'",
    )


class WeatherBrief(BaseModel):
    """Agent 3 — climate context, grounded by Open-Meteo when available."""

    season_overview: str = Field(description="2-sentence climate summary")
    temperature_range: str = Field(default="", description="e.g. '12°C - 24°C (54°F - 75°F)'")
    humidity: str = Field(default="Moderate")
    rainfall: str = Field(default="", description="Brief rain pattern description")
    best_months: list[str] = Field(default_factory=list)
    shoulder_months: list[str] = Field(default_factory=list)
    avoid_if_possible: list[str] = Field(default_factory=list)
    clothing_advice: str = Field(default="")
    umbrella_needed: bool = True
    sun_protection: bool = True
    weather_warning: str | None = Field(
        default=None, description="Extreme weather risk, or null if none"
    )


class Accommodation(BaseModel):
    name: str
    type: str = Field(default="Hotel", description="Hotel / Boutique / Hostel / Apartment / Resort")
    stars: Annotated[int, Field(ge=1, le=5)] = 3
    price_range: str = Field(default="", description="e.g. '$80 - $140 per night'")
    neighborhood: str = ""
    description: str = ""
    top_amenity: str = ""
    pros: str = ""
    cons: str = Field(default="", description="One honest limitation")
    best_for: str = ""
    booking_tip: str = ""


class AccommodationSet(BaseModel):
    """Agent 4 — exactly one option per price tier."""

    options: list[Accommodation] = Field(
        default_factory=list,
        description="Three stays: one budget, one mid-range, one premium",
    )


class Activity(BaseModel):
    time: str = Field(description="Local clock time, e.g. '9:00 AM'")
    activity: str = Field(description="Specific named place or experience")
    description: str = ""
    cost: str = Field(default="", description="e.g. '$12-20' or 'Free'")
    duration: str = Field(default="", description="e.g. '~2h'")
    pro_tip: str = ""
    category: str = Field(
        default="sightseeing",
        description="One of: sightseeing, food, museum, outdoors, nightlife, shopping, transit, rest",
    )


class DayPlan(BaseModel):
    day: Annotated[int, Field(ge=1)]
    title: str = Field(description="Evocative day title")
    theme_emoji: str = "🗺️"
    activities: list[Activity] = Field(default_factory=list)
    day_highlights: str = ""
    transport_for_day: str = ""
    estimated_daily_cost: str = ""
    walking_distance_km: float = Field(default=0.0, ge=0.0)


class Itinerary(BaseModel):
    """Agent 5 — the day-by-day plan."""

    days: list[DayPlan] = Field(default_factory=list)


class Dish(BaseModel):
    name: str
    description: str = ""
    find_at: str = ""
    avg_cost: str = ""
    dietary: str = Field(default="", description="e.g. 'vegetarian-friendly', 'contains pork'")


class Restaurant(BaseModel):
    name: str
    vibe: str = Field(default="", description="Casual / Fine dining / Street food / Market")
    cuisine: str = ""
    price: str = Field(default="$$", description="$ to $$$$")
    signature_dish: str = ""
    neighborhood: str = ""
    why_go: str = ""


class FoodMarket(BaseModel):
    name: str
    specialty: str = ""
    best_time: str = ""


class FoodGuide(BaseModel):
    """Agent 6 — culinary guide."""

    culinary_intro: str = ""
    must_try_dishes: list[Dish] = Field(default_factory=list)
    restaurants: list[Restaurant] = Field(default_factory=list)
    food_markets: list[FoodMarket] = Field(default_factory=list)
    drink_culture: str = ""
    food_etiquette: str = ""
    dietary_advice: str = ""


class CurrencyInfo(BaseModel):
    local_currency: str = ""
    symbol: str = ""
    usd_rate: str = ""


class BudgetPlan(BaseModel):
    """Agent 7 — costed plan."""

    currency_info: CurrencyInfo = Field(default_factory=CurrencyInfo)
    per_person_breakdown: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Keys: flights_roundtrip, accommodation_total, food_daily, "
            "activities_total, local_transport_daily, sim_card_data, "
            "travel_insurance, visa_fee, shopping_buffer, emergency_buffer, "
            "total_per_person"
        ),
    )
    total_for_group: str = ""
    daily_budget_target: str = ""
    budget_breakdown_percent: dict[str, str] = Field(default_factory=dict)
    money_saving_hacks: list[str] = Field(default_factory=list)
    splurge_worthy: str = ""
    atm_card_tips: str = ""
    tipping_culture: str = ""


class ClothingPlan(BaseModel):
    tops: list[str] = Field(default_factory=list)
    bottoms: list[str] = Field(default_factory=list)
    outerwear: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)


class PackingList(BaseModel):
    """Agent 8 — weather-aware packing list."""

    packing_philosophy: str = ""
    bag_recommendation: str = ""
    essentials: list[str] = Field(default_factory=list)
    clothing: ClothingPlan = Field(default_factory=ClothingPlan)
    toiletries: list[str] = Field(default_factory=list)
    health_safety: list[str] = Field(default_factory=list)
    electronics: list[str] = Field(default_factory=list)
    documents_money: list[str] = Field(default_factory=list)
    activity_gear: list[str] = Field(default_factory=list)
    do_not_pack: list[str] = Field(default_factory=list)
    buy_there: list[str] = Field(default_factory=list)
    weight_tip: str = ""


class RiskReport(BaseModel):
    """Agent 9 — the critic. Reviews the assembled plan and scores it."""

    overall_score: Annotated[int, Field(ge=0, le=100)] = 80
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(
        default_factory=list, description="Concrete things that could go wrong"
    )
    fixes: list[str] = Field(
        default_factory=list, description="Actionable improvement per risk"
    )
    pacing_verdict: str = Field(
        default="", description="Is the schedule too packed, too loose, or right?"
    )
    budget_realism: str = Field(default="", description="Is the budget achievable?")


# ─────────────────────────────────────────────────────────────
#  Final assembled artefact
# ─────────────────────────────────────────────────────────────


class GeoPoint(BaseModel):
    name: str = ""
    country: str = ""
    country_code: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = ""
    population: int = 0


class TravelPlan(BaseModel):
    """The single object the UI and every exporter consume."""

    summary: str = ""
    overview: dict[str, str] = Field(default_factory=dict)
    destination: DestinationBrief = Field(default_factory=DestinationBrief.model_construct)
    weather: WeatherBrief = Field(default_factory=WeatherBrief.model_construct)
    accommodations: list[Accommodation] = Field(default_factory=list)
    itinerary: list[DayPlan] = Field(default_factory=list)
    food: FoodGuide = Field(default_factory=FoodGuide)
    budget: BudgetPlan = Field(default_factory=BudgetPlan)
    packing: PackingList = Field(default_factory=PackingList)
    review: RiskReport = Field(default_factory=RiskReport)
    geo: GeoPoint = Field(default_factory=GeoPoint)
    live_sources: list[str] = Field(
        default_factory=list, description="Which real APIs grounded this plan"
    )
    agent_log: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "BUDGET_BANDS",
    "Accommodation",
    "AccommodationSet",
    "Activity",
    "BudgetPlan",
    "BudgetTier",
    "ClothingPlan",
    "CurrencyInfo",
    "DayPlan",
    "DestinationBrief",
    "Dish",
    "FoodGuide",
    "FoodMarket",
    "GeoPoint",
    "Itinerary",
    "PackingList",
    "Restaurant",
    "RiskReport",
    "TravelPlan",
    "TravelStyle",
    "TripInput",
    "WeatherBrief",
]
