"""
fallbacks.py — deterministic, offline-safe stand-ins.

If every provider in the chain fails, the user still gets a usable plan rather
than an error page. These builders are pure functions of the trip input (plus
whatever real data we managed to fetch), so they are fast, deterministic and
trivially testable.
"""

from __future__ import annotations

from typing import Any

from travel_planner.schemas import (
    Accommodation,
    Activity,
    BudgetPlan,
    ClothingPlan,
    CurrencyInfo,
    DayPlan,
    DestinationBrief,
    Dish,
    FoodGuide,
    FoodMarket,
    PackingList,
    Restaurant,
    RiskReport,
    TripInput,
    WeatherBrief,
)


def fb_destination(trip: TripInput, context: dict[str, Any] | None = None) -> DestinationBrief:
    context = context or {}
    wiki = context.get("wiki") or {}
    facts = context.get("country") or {}
    essence = wiki.get("extract", "")[:400] or (
        f"{trip.destination} rewards curious travellers with a distinctive blend of "
        "history, food and everyday street life."
    )
    phrases = ["Hello", "Thank you", "How much?", "Where is…?"]
    language = (facts.get("languages") or [""])[0]
    return DestinationBrief(
        essence=essence,
        best_neighborhoods=[
            "City centre — walkable, close to the main sights",
            "Old quarter — historic streets and independent cafés",
            "Riverside / residential district — quieter and better value",
        ],
        iconic_attractions=[
            f"Main square of {trip.destination} — arrive before 9am to beat the crowds",
            "Principal museum — free or reduced entry on the first Sunday",
            "Historic district — best explored on foot in the late afternoon",
            "Central market — go hungry, and go early",
            "Panoramic viewpoint — sunset is worth the climb",
        ],
        getting_around=(
            "Public transport with a multi-day pass is usually the best value; "
            "the historic core is typically walkable end to end."
        ),
        culture_customs=[
            "Greet people before asking a question — it changes the whole interaction",
            "Dress modestly at religious sites; carry a light scarf",
            "Learn the words for please and thank you in the local language",
        ],
        safety_notes=[
            "Pickpocketing concentrates at transport hubs and crowded viewpoints",
            "Keep a digital and a paper copy of your passport in separate places",
        ],
        ideal_timing=(
            ", ".join((context.get("climate") or {}).get("best_months", []))
            or "Shoulder season — fewer crowds and gentler prices"
        ),
        language_phrases=[f"{p} — in {language or 'the local language'}" for p in phrases],
    )


def fb_weather(trip: TripInput, context: dict[str, Any] | None = None) -> WeatherBrief:
    climate = (context or {}).get("climate")
    if climate:
        return WeatherBrief(
            season_overview=(
                f"Average highs across the year sit near {climate['annual_high_c']}°C "
                f"with lows near {climate['annual_low_c']}°C, based on measured "
                "reanalysis data."
            ),
            temperature_range=(
                f"{climate['annual_low_c']}°C - {climate['annual_high_c']}°C "
                f"({round(climate['annual_low_c'] * 9 / 5 + 32)}°F - "
                f"{round(climate['annual_high_c'] * 9 / 5 + 32)}°F)"
            ),
            humidity="Moderate",
            rainfall=(
                f"Wettest month is {climate['wettest_month']}; "
                f"driest is {climate['driest_month']}."
            ),
            best_months=climate["best_months"],
            shoulder_months=[],
            avoid_if_possible=[climate["wettest_month"]],
            clothing_advice="Layer up — mornings and evenings run cooler than midday.",
            umbrella_needed=True,
            sun_protection=True,
            weather_warning=None,
        )
    return WeatherBrief(
        season_overview=f"{trip.destination} is generally pleasant, with clear seasonal shifts.",
        temperature_range="Varies by season",
        rainfall="Check a local forecast a week before departure.",
        clothing_advice="Pack layers and a compact rain shell.",
    )


def fb_accommodations(trip: TripInput) -> list[Accommodation]:
    place = trip.destination
    return [
        Accommodation(
            name=f"{place} Central Hotel",
            type="Hotel",
            stars=3,
            price_range="$60 - $100 per night",
            neighborhood="City Centre",
            description=f"Straightforward, well-located base in central {place} with easy transit access.",
            top_amenity="Unbeatable location",
            pros="Walk to most major sights",
            cons="Street noise on lower floors",
            best_for="First-time visitors",
            booking_tip="Book 4-6 weeks ahead for the best rate",
        ),
        Accommodation(
            name=f"The {place} Boutique",
            type="Boutique Hotel",
            stars=4,
            price_range="$120 - $200 per night",
            neighborhood="Old Quarter",
            description="Small, design-led property with genuinely local character and attentive staff.",
            top_amenity="Rooftop terrace",
            pros="Real sense of place",
            cons="Rooms are compact",
            best_for="Couples and culture-first travellers",
            booking_tip="Request a courtyard-facing room when you book",
        ),
        Accommodation(
            name=f"Grand {place} Resort",
            type="Resort",
            stars=5,
            price_range="$250 - $450 per night",
            neighborhood="Upscale District",
            description="Full-service luxury with a spa, pool and the service level to match.",
            top_amenity="Spa and infinity pool",
            pros="Comfort with zero friction",
            cons="Further from the historic centre",
            best_for="Travellers prioritising rest over proximity",
            booking_tip="Booking direct often unlocks a free room upgrade",
        ),
    ]


def fb_day(trip: TripInput, day_number: int) -> DayPlan:
    place = trip.destination
    return DayPlan(
        day=day_number,
        title=f"Discovering {place} — Day {day_number}",
        theme_emoji="🗺️",
        activities=[
            Activity(
                time="8:30 AM",
                activity="Morning walk through the historic core",
                description=f"Start slow and get your bearings in {place} before the crowds arrive.",
                cost="Free",
                duration="~2h",
                pro_tip="Early light is the best light for photos",
                category="sightseeing",
            ),
            Activity(
                time="11:00 AM",
                activity="Principal museum or landmark",
                description="The one cultural site you would regret skipping.",
                cost="$10-20",
                duration="~2h",
                pro_tip="Buy a timed ticket online the night before",
                category="museum",
            ),
            Activity(
                time="1:00 PM",
                activity="Lunch at a neighbourhood restaurant",
                description="Eat where the queue is local rather than international.",
                cost="$10-20",
                duration="~1h",
                pro_tip="Set lunch menus are far cheaper than dinner",
                category="food",
            ),
            Activity(
                time="3:30 PM",
                activity="Market or park wander",
                description="Unstructured time — this is usually where the trip memories come from.",
                cost="$5-15",
                duration="~2h",
                pro_tip="Carry small notes; many stalls do not take cards",
                category="outdoors",
            ),
            Activity(
                time="7:30 PM",
                activity="Dinner and an evening stroll",
                description="A longer, unhurried meal followed by the city after dark.",
                cost="$20-40",
                duration="~2h",
                pro_tip="Reserve ahead on Friday and Saturday",
                category="food",
            ),
        ],
        day_highlights=f"A balanced first pass at the best of {place}",
        transport_for_day="Walking plus one or two public transport hops",
        estimated_daily_cost="$60 - $120 per person",
        walking_distance_km=6.5,
    )


def fb_itinerary(trip: TripInput) -> list[DayPlan]:
    return [fb_day(trip, index + 1) for index in range(trip.duration)]


def fb_food(trip: TripInput) -> FoodGuide:
    place = trip.destination
    return FoodGuide(
        culinary_intro=(
            f"{place} has a layered food culture that runs from street stalls to "
            "serious kitchens. Eating well here costs less than you would expect."
        ),
        must_try_dishes=[
            Dish(
                name=f"The signature dish of {place}",
                description="The plate locals name first when asked what to eat.",
                find_at="Traditional restaurants and the central market",
                avg_cost="$5-15",
                dietary="Ask about substitutions",
            ),
            Dish(
                name="Street snack",
                description="Sold everywhere, eaten standing up, gone in four bites.",
                find_at="Night markets and food stalls",
                avg_cost="$2-5",
                dietary="Often vegetarian",
            ),
            Dish(
                name="Regional dessert",
                description="A sweet that barely exists outside this region.",
                find_at="Neighbourhood bakeries",
                avg_cost="$3-8",
                dietary="Contains dairy",
            ),
        ],
        restaurants=[
            Restaurant(
                name=f"{place} Food Hall",
                vibe="Market",
                cuisine="Mixed local",
                price="$",
                signature_dish="Whatever the busiest stall is selling",
                neighborhood="City Centre",
                why_go="Maximum variety at minimum cost",
            ),
            Restaurant(
                name="Traditional Kitchen",
                vibe="Casual",
                cuisine="Traditional local",
                price="$$",
                signature_dish="The house recommendation",
                neighborhood="Old Town",
                why_go="Recipes that have not changed in decades",
            ),
            Restaurant(
                name="The Modern Table",
                vibe="Fine dining",
                cuisine="Contemporary local",
                price="$$$",
                signature_dish="Tasting menu",
                neighborhood="Upscale District",
                why_go="Classic flavours, rebuilt from scratch",
            ),
        ],
        food_markets=[
            FoodMarket(
                name=f"{place} Central Market",
                specialty="Produce, prepared food and local snacks",
                best_time="Weekday mornings",
            )
        ],
        drink_culture="Ask a local what they drink with dinner, then order that.",
        food_etiquette="Watch a nearby table for a few seconds before you start eating.",
        dietary_advice=(
            "Write your dietary requirement on your phone in the local language "
            "and show it — far more reliable than pronunciation."
        ),
    )


def fb_budget(trip: TripInput, context: dict[str, Any] | None = None) -> BudgetPlan:
    low, high = trip.budget_band
    per_person = int((low + high) / 2 * (trip.duration / 7))
    per_person = max(per_person, 200)
    group_total = per_person * trip.travelers

    facts = (context or {}).get("country") or {}
    fx = (context or {}).get("fx") or {}
    currency = CurrencyInfo(
        local_currency=facts.get("currency_name", "Local currency"),
        symbol=facts.get("currency_symbol", ""),
        usd_rate=(
            f"1 USD ≈ {fx['rate']:.2f} {fx['code']} (as of {fx['date']})"
            if fx.get("rate")
            else "Check a live rate before you travel"
        ),
    )

    def band(fraction: float) -> str:
        return f"${int(per_person * fraction * 0.9):,} - ${int(per_person * fraction * 1.1):,}"

    return BudgetPlan(
        currency_info=currency,
        per_person_breakdown={
            "flights_roundtrip": band(0.35),
            "accommodation_total": f"{band(0.28)} for {trip.duration} nights",
            "food_daily": f"${int(per_person * 0.16 / trip.duration):,} - "
            f"${int(per_person * 0.20 / trip.duration):,} per day",
            "activities_total": band(0.12),
            "local_transport_daily": f"${int(per_person * 0.05 / trip.duration):,} - "
            f"${int(per_person * 0.07 / trip.duration):,} per day",
            "sim_card_data": "$10 - $25",
            "travel_insurance": "$50 - $120",
            "visa_fee": "Varies by nationality",
            "shopping_buffer": f"${int(per_person * 0.06):,}",
            "emergency_buffer": f"${int(per_person * 0.05):,}",
            "total_per_person": f"${int(per_person * 0.9):,} - ${int(per_person * 1.1):,}",
        },
        total_for_group=(
            f"${int(group_total * 0.9):,} - ${int(group_total * 1.1):,} "
            f"for {trip.travelers} traveller(s)"
        ),
        daily_budget_target=f"${int(per_person / trip.duration):,} - "
        f"${int(per_person * 1.15 / trip.duration):,} per person per day",
        budget_breakdown_percent={
            "transport": "35%",
            "accommodation": "28%",
            "food": "18%",
            "activities": "12%",
            "other": "7%",
        },
        money_saving_hacks=[
            "Book flights 6-8 weeks out and fly midweek",
            "Eat your main meal at lunch — the same kitchen, a lower price",
            "Buy a multi-day transit pass on arrival",
            "Stay one neighbourhood out from the tourist core",
        ],
        splurge_worthy="One standout meal or one guided experience — not both",
        atm_card_tips="Withdraw from bank ATMs, always decline dynamic currency conversion.",
        tipping_culture="Tipping norms vary sharply by country — confirm before you arrive.",
    )


def fb_packing(trip: TripInput, weather: WeatherBrief | None = None) -> PackingList:
    rain = weather.umbrella_needed if weather else True
    return PackingList(
        packing_philosophy="Pack light and do laundry once — you will thank yourself.",
        bag_recommendation=(
            "30-40L carry-on backpack" if trip.duration <= 7 else "45L carry-on plus a daypack"
        ),
        essentials=[
            "Passport plus a digital copy stored offline",
            "Travel insurance documents",
            "Two payment cards from different networks",
            "Phone and charger",
            "Power bank (10,000 mAh)",
            "Universal power adapter",
        ],
        clothing=ClothingPlan(
            tops=["4 versatile tops", "1 smart shirt or blouse", "1 mid layer"],
            bottoms=["2 pairs of trousers", "1 pair of shorts or a skirt"],
            outerwear=["Packable rain shell"] if rain else ["Light jacket"],
            footwear=["Broken-in walking shoes", "1 smarter pair"],
            accessories=["Sunglasses", "Packable daypack", "Light scarf"],
        ),
        toiletries=[
            "Sunscreen SPF 50",
            "Solid toiletries to skip the liquids bag",
            "Personal medication in original packaging",
            "Hand sanitiser",
        ],
        health_safety=[
            "Compact first-aid kit",
            "Double supply of any prescription medication",
            "Electrolyte sachets",
        ],
        electronics=["Phone and charger", "Power bank", "Earphones", "Short multi-tip cable"],
        documents_money=[
            "Passport",
            "Visa or entry documents",
            "Printed booking confirmations",
            "Emergency contact card",
            "Insurance policy number",
        ],
        activity_gear=["Reusable water bottle", "Compact umbrella", "Daypack"],
        do_not_pack=["A third pair of shoes", "Full-size toiletries", "Travel iron"],
        buy_there=["Sunscreen", "Bottled water and snacks", "Anything you forget"],
        weight_tip="Over 10kg for a one-week trip means something needs to come out.",
    )


def fb_review(trip: TripInput) -> RiskReport:
    return RiskReport(
        overall_score=75,
        strengths=[
            "Coverage across every planning dimension",
            f"Pacing matched to a {trip.travel_style.lower()} style",
        ],
        risks=[
            "Opening hours and prices drift — verify before you go",
            "Popular sites may require timed tickets booked well in advance",
        ],
        fixes=[
            "Re-check every opening time 48 hours before each visit",
            "Book the two highest-demand attractions the moment dates are fixed",
        ],
        pacing_verdict="Reasonable, with room to drop one afternoon activity per day.",
        budget_realism="Directionally correct; treat it as a planning range, not a quote.",
    )


__all__ = [
    "fb_accommodations",
    "fb_budget",
    "fb_day",
    "fb_destination",
    "fb_food",
    "fb_itinerary",
    "fb_packing",
    "fb_review",
    "fb_weather",
]
