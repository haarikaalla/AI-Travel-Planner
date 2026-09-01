"""
agents.py — the ten specialists.

Each agent is a pure ``state -> partial state`` function, which is what makes
them trivially unit-testable and freely re-orderable in the graph. Every agent
follows the same three-step contract:

1. Build a prompt that embeds the trip brief *and* the verified real-world
   facts gathered by :mod:`travel_planner.tools`.
2. Call :func:`travel_planner.llm.invoke_structured` with a Pydantic schema, so
   the return value is validated before it is written back to state.
3. Never raise. A failure is recorded in ``errors`` and a deterministic
   fallback is written instead, so the pipeline always reaches the composer.
"""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, TypedDict

from travel_planner import fallbacks as fb
from travel_planner.llm import invoke_text
from travel_planner.llm import invoke_structured as _invoke_structured
from travel_planner.schemas import (
    AccommodationSet,
    BudgetPlan,
    DestinationBrief,
    FoodGuide,
    GeoPoint,
    Itinerary,
    PackingList,
    RiskReport,
    TravelPlan,
    TripInput,
    WeatherBrief,
)
from travel_planner.tools import context_to_prompt, gather_context

# ─────────────────────────────────────────────────────────────
#  Shared state
# ─────────────────────────────────────────────────────────────


class TravelState(TypedDict, total=False):
    """The blackboard every agent reads from and writes to.

    ``messages``, ``errors`` and ``timings`` use ``operator.add`` reducers so
    that agents running concurrently in the fan-out merge cleanly instead of
    overwriting one another.
    """

    trip_input: dict[str, Any]
    provider: str
    model_name: str

    live_context: dict[str, Any]
    destination: DestinationBrief
    weather: WeatherBrief
    accommodations: AccommodationSet
    itinerary: Itinerary
    food: FoodGuide
    budget: BudgetPlan
    packing: PackingList
    review: RiskReport

    final_result: dict[str, Any]
    messages: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    timings: Annotated[list[dict[str, Any]], operator.add]


def _trip(state: TravelState) -> TripInput:
    return TripInput.model_validate(state["trip_input"])


def _grounding(state: TravelState) -> str:
    return context_to_prompt(state.get("live_context") or {})


def _route(state: TravelState) -> dict[str, Any]:
    return {"provider": state.get("provider"), "model": state.get("model_name")}


def _emit(agent: str, started: float, note: str, error: str | None) -> dict[str, Any]:
    """Uniform log / timing / error payload appended by every agent."""
    elapsed = round(time.perf_counter() - started, 2)
    status = "degraded" if error else "ok"
    return {
        "messages": [f"[{agent}] {'⚠' if error else '✓'} {note} ({elapsed}s)"],
        "errors": [f"{agent}: {error}"] if error else [],
        "timings": [{"agent": agent, "seconds": elapsed, "status": status}],
    }


# ─────────────────────────────────────────────────────────────
#  1 — Supervisor: validate the request, fetch ground truth
# ─────────────────────────────────────────────────────────────


def supervisor_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    context = gather_context(trip.destination)
    sources = context.get("sources", [])
    note = (
        f"{trip.duration}-day trip to {trip.destination} for {trip.travelers} "
        f"traveller(s) — grounded by {len(sources)} live source(s)"
    )
    return {"live_context": context, **_emit("Supervisor", started, note, None)}


# ─────────────────────────────────────────────────────────────
#  2 — Researcher
# ─────────────────────────────────────────────────────────────


def researcher_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    prompt = f"""You are a destination researcher who has personally spent months in {trip.destination}.

{trip.brief()}

{_grounding(state)}

Produce a destination brief. Use real, verifiable place names — never invent
landmarks. Every attraction needs an insider tip that a first-time visitor
would not find on the first page of search results. Keep each field tight."""

    result, error = _invoke_structured(
        prompt,
        DestinationBrief,
        fallback=fb.fb_destination(trip, state.get("live_context")),
        **_route(state),
    )
    return {"destination": result, **_emit("Researcher", started, "destination brief ready", error)}


# ─────────────────────────────────────────────────────────────
#  3 — Weather
# ─────────────────────────────────────────────────────────────


def weather_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    prompt = f"""You are a travel climate analyst.

{trip.brief()}

{_grounding(state)}

Interpret the measured climate normals above for a traveller. Your temperature
figures MUST match the measured data — do not substitute your own recollection.
Explain what the numbers mean in practice: what to wear, whether rain gear is
genuinely needed, and which months to favour or avoid."""

    result, error = _invoke_structured(
        prompt,
        WeatherBrief,
        fallback=fb.fb_weather(trip, state.get("live_context")),
        **_route(state),
    )

    # Real observations always win over model recollection.
    climate = (state.get("live_context") or {}).get("climate")
    if climate:
        result.best_months = climate["best_months"]
        if not result.temperature_range:
            result.temperature_range = (
                f"{climate['annual_low_c']}°C - {climate['annual_high_c']}°C"
            )
    return {"weather": result, **_emit("Weather", started, "climate analysis complete", error)}


# ─────────────────────────────────────────────────────────────
#  4 — Accommodation
# ─────────────────────────────────────────────────────────────


def accommodation_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    low, high = trip.budget_band
    prompt = f"""You are an accommodation scout who books this city constantly.

{trip.brief()}

{_grounding(state)}

Return exactly three stays for {trip.duration} nights: one clearly budget, one
mid-range, one premium. Nightly rates must be plausible for this city and stay
consistent with a total trip budget of roughly ${low}-${high} per person.
Name the real neighbourhood. Give one honest drawback per property — a listing
with no downside reads as marketing, not advice."""

    result, error = _invoke_structured(
        prompt,
        AccommodationSet,
        fallback=AccommodationSet(options=fb.fb_accommodations(trip)),
        **_route(state),
    )
    if not result.options:
        result = AccommodationSet(options=fb.fb_accommodations(trip))
    return {
        "accommodations": result,
        **_emit("Accommodation", started, f"{len(result.options)} stays shortlisted", error),
    }


# ─────────────────────────────────────────────────────────────
#  5 — Activity curator
# ─────────────────────────────────────────────────────────────

_PACING = {
    "Balanced": "4-5 activities per day with real breaks between them",
    "Packed (max activities)": "6-7 activities per day, tightly sequenced",
    "Relaxed (slow travel)": "3 activities per day, long unhurried meals",
    "Off-the-beaten-path": "4 activities per day, at most one famous landmark",
    "Family-friendly": "4 activities per day, nothing over 90 minutes, daily downtime",
    "Solo & social": "4-5 activities per day biased toward group tours and social venues",
}


def activity_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    prompt = f"""You are an itinerary designer with deep local knowledge of {trip.destination}.

{trip.brief()}

{_grounding(state)}

Design exactly {trip.duration} days, numbered 1 to {trip.duration}.
Pacing for this travel style: {_PACING.get(trip.travel_style, _PACING['Balanced'])}.

Hard requirements:
- Group each day geographically so travellers are not crossing the city twice.
- Every day must have a distinct theme; no repeated attractions across days.
- Use real, named places. Include realistic local costs.
- Reflect these interests concretely: {', '.join(trip.interests)}.
- Honour the special requests: {trip.special_requests}.
- Estimate walking distance in km per day."""

    result, error = _invoke_structured(
        prompt,
        Itinerary,
        fallback=Itinerary(days=fb.fb_itinerary(trip)),
        **_route(state),
    )

    days = sorted([d for d in result.days if d.day >= 1], key=lambda d: d.day)[: trip.duration]
    for index, day in enumerate(days, start=1):
        day.day = index
    while len(days) < trip.duration:
        days.append(fb.fb_day(trip, len(days) + 1))
    result = Itinerary(days=days)

    return {
        "itinerary": result,
        **_emit("Activity Curator", started, f"{len(days)}-day itinerary crafted", error),
    }


# ─────────────────────────────────────────────────────────────
#  6 — Food
# ─────────────────────────────────────────────────────────────


def food_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    prompt = f"""You are a food writer who has eaten their way through {trip.destination}.

{trip.brief()}

{_grounding(state)}

Give 4 must-try dishes, 5 restaurants across the price range, and the markets
worth a detour. Flag allergens and dietary suitability per dish. Address these
dietary notes directly and specifically: {trip.special_requests}.
Prefer places locals actually go to over places that appear in every listicle."""

    result, error = _invoke_structured(
        prompt, FoodGuide, fallback=fb.fb_food(trip), **_route(state)
    )
    return {"food": result, **_emit("Food Guide", started, "culinary guide compiled", error)}


# ─────────────────────────────────────────────────────────────
#  7 — Budget
# ─────────────────────────────────────────────────────────────


def budget_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    low, high = trip.budget_band
    prompt = f"""You are a travel cost analyst.

{trip.brief()}

{_grounding(state)}

Cost this trip for {trip.travelers} traveller(s) over {trip.duration} days at a
{trip.budget} level (target ${low}-${high} per person for a week, scaled to the
actual duration). Use the verified exchange rate above where relevant.
All values are USD ranges as strings. The percentage breakdown must sum to 100%.
Fill every key of per_person_breakdown listed in the schema."""

    result, error = _invoke_structured(
        prompt,
        BudgetPlan,
        fallback=fb.fb_budget(trip, state.get("live_context")),
        **_route(state),
    )
    if not result.per_person_breakdown:
        result = fb.fb_budget(trip, state.get("live_context"))
    return {"budget": result, **_emit("Budget Planner", started, "financial plan ready", error)}


# ─────────────────────────────────────────────────────────────
#  8 — Packing (depends on weather + itinerary)
# ─────────────────────────────────────────────────────────────


def packing_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    weather = state.get("weather") or fb.fb_weather(trip, state.get("live_context"))
    itinerary = state.get("itinerary")
    categories = sorted(
        {
            activity.category
            for day in (itinerary.days if itinerary else [])
            for activity in day.activities
        }
    )

    prompt = f"""You are a packing consultant. Build a list for this exact trip.

{trip.brief()}

Confirmed climate: {weather.temperature_range or 'see below'} — {weather.season_overview}
Rain gear needed: {weather.umbrella_needed}. Sun protection needed: {weather.sun_protection}.
Activity types actually scheduled: {', '.join(categories) or 'general sightseeing'}.

Rules: every item must earn its place for THIS trip. Scale quantities to
{trip.duration} days assuming one laundry cycle. Name specific items travellers
routinely forget, and list what to deliberately leave at home."""

    result, error = _invoke_structured(
        prompt, PackingList, fallback=fb.fb_packing(trip, weather), **_route(state)
    )
    return {"packing": result, **_emit("Packing", started, "packing list optimised", error)}


# ─────────────────────────────────────────────────────────────
#  9 — Critic (reflection pass over the assembled plan)
# ─────────────────────────────────────────────────────────────


def critic_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    itinerary = state.get("itinerary")
    budget = state.get("budget")

    day_lines = "\n".join(
        f"Day {day.day} ({day.title}): "
        + "; ".join(f"{a.time} {a.activity}" for a in day.activities)
        + f" | ~{day.walking_distance_km}km | {day.estimated_daily_cost}"
        for day in (itinerary.days if itinerary else [])
    ) or "No itinerary produced."

    prompt = f"""You are a demanding travel editor. Review this draft plan and be
genuinely critical — a review that finds no problems is a useless review.

{trip.brief()}

DRAFT ITINERARY
{day_lines}

BUDGET TARGET: {budget.total_for_group if budget else 'unknown'}
DAILY TARGET: {budget.daily_budget_target if budget else 'unknown'}

Assess: is the pacing achievable on foot and by transit? Are opening hours and
travel times realistic? Does the budget hold up? Does the plan actually reflect
the stated interests and special requests? Score it 0-100 and pair every risk
you raise with a concrete, actionable fix."""

    result, error = _invoke_structured(
        prompt, RiskReport, fallback=fb.fb_review(trip), **_route(state)
    )
    return {
        "review": result,
        **_emit("Critic", started, f"plan reviewed — score {result.overall_score}/100", error),
    }


# ─────────────────────────────────────────────────────────────
#  10 — Composer (final assembly)
# ─────────────────────────────────────────────────────────────


def composer_agent(state: TravelState) -> dict[str, Any]:
    started = time.perf_counter()
    trip = _trip(state)
    context = state.get("live_context") or {}

    default_summary = (
        f"Your {trip.duration}-day journey through {trip.destination} is built around "
        f"{', '.join(trip.interests[:3]).lower()}, paced for {trip.travel_style.lower()} "
        f"travel and costed to a {trip.budget.lower()} budget."
    )
    summary_prompt = f"""Write 2-3 vivid sentences to open a travel document for a
{trip.duration}-day trip to {trip.destination} for {trip.travelers} traveller(s)
who love {', '.join(trip.interests)}. Address the reader as "you". Be specific to
this destination. No bullet points, no clichés such as "hidden gem" or
"vibrant tapestry", no preamble — return only the sentences."""

    summary, summary_error = invoke_text(
        summary_prompt, fallback=default_summary, **_route(state)
    )

    itinerary = state.get("itinerary") or Itinerary(days=fb.fb_itinerary(trip))
    weather = state.get("weather") or fb.fb_weather(trip, context)
    accommodations = state.get("accommodations") or AccommodationSet(
        options=fb.fb_accommodations(trip)
    )

    plan = TravelPlan(
        summary=summary.strip(),
        overview={
            "Destination": trip.destination,
            "Duration": f"{trip.duration} days",
            "Travellers": str(trip.travelers),
            "Budget": trip.budget,
            "Style": trip.travel_style,
            "Interests": ", ".join(trip.interests),
        },
        destination=state.get("destination") or fb.fb_destination(trip, context),
        weather=weather,
        accommodations=accommodations.options,
        itinerary=itinerary.days,
        food=state.get("food") or fb.fb_food(trip),
        budget=state.get("budget") or fb.fb_budget(trip, context),
        packing=state.get("packing") or fb.fb_packing(trip, weather),
        review=state.get("review") or fb.fb_review(trip),
        geo=context.get("geo") or GeoPoint(),
        live_sources=sorted(set(context.get("sources", []))),
        agent_log=list(state.get("messages", [])),
        errors=list(state.get("errors", [])),
        meta={
            "provider": state.get("provider"),
            "model": state.get("model_name"),
            "timings": list(state.get("timings", [])),
            "total_activities": sum(len(day.activities) for day in itinerary.days),
        },
    )

    return {
        "final_result": plan.model_dump(),
        **_emit("Composer", started, "itinerary assembled", summary_error),
    }


AGENTS = {
    "supervisor": supervisor_agent,
    "researcher": researcher_agent,
    "weather": weather_agent,
    "accommodation": accommodation_agent,
    "activity": activity_agent,
    "food": food_agent,
    "budget": budget_agent,
    "packing": packing_agent,
    "critic": critic_agent,
    "composer": composer_agent,
}

#: Display metadata for the UI agent tracker.
AGENT_META: list[tuple[str, str, str, str]] = [
    ("supervisor", "🧭", "Supervisor", "Validating request & fetching live data"),
    ("researcher", "🔍", "Researcher", "Gathering destination intelligence"),
    ("weather", "🌤", "Weather", "Reading measured climate normals"),
    ("accommodation", "🏨", "Accommodation", "Shortlisting stays by budget"),
    ("activity", "🎯", "Activities", "Designing the day-by-day route"),
    ("food", "🍜", "Food Guide", "Curating dishes and restaurants"),
    ("budget", "💰", "Budget", "Costing the trip"),
    ("packing", "🧳", "Packing", "Optimising the packing list"),
    ("critic", "🧠", "Critic", "Stress-testing the plan"),
    ("composer", "📄", "Composer", "Assembling the final document"),
]

__all__ = ["AGENTS", "AGENT_META", "TravelState", *AGENTS.keys()]
