"""
travel_graph.py
================
AI Travel Planner — LangGraph Multi-Agent Orchestration
9 Specialized Agents running in a supervised parallel pipeline

Architecture:
  supervisor ──► researcher
                     │
          ┌──────────┼──────────┬───────────┬──────────┐
          ▼          ▼          ▼           ▼          ▼
       weather  accommodation activity    food      budget
          │          │          │           │          │
          └──────────┴──────────┴───────────┴──────────┘
                                │
                             packing
                                │
                            composer ──► END
"""

import json
import re
import os
import operator
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langchain_ollama import OllamaLLM


# ─────────────────────────────────────────────
#  Shared State (all agents read/write this)
# ─────────────────────────────────────────────

class TravelState(TypedDict):
    trip_input:         Dict[str, Any]
    model_name:         str
    destination_info:   str
    weather_raw:        str
    accommodations_raw: str
    activities_raw:     str
    food_raw:           str
    budget_raw:         str
    packing_raw:        str
    final_result:       Dict[str, Any]
    messages:           Annotated[List[str], operator.add]
    errors:             Annotated[List[str], operator.add]


# ─────────────────────────────────────────────
#  LLM Factory + Safe Caller
# ─────────────────────────────────────────────

def get_llm(model: str = None) -> OllamaLLM:
    m = model or os.getenv("OLLAMA_MODEL", "llama3.2")
    return OllamaLLM(model=m, temperature=0.7, timeout=180)


def llm_call(llm: OllamaLLM, prompt: str, agent: str, retries: int = 2) -> str:
    """Call LLM with retry. Returns __ERROR__ prefixed string on failure."""
    for attempt in range(retries + 1):
        try:
            response = llm.invoke(prompt)
            if response and len(response.strip()) > 10:
                return response
        except Exception as e:
            if attempt == retries:
                return f"__ERROR__ [{agent}]: {str(e)}"
    return f"__ERROR__ [{agent}]: Empty response after {retries+1} attempts"


# ─────────────────────────────────────────────
#  Agent 1 — Supervisor
# ─────────────────────────────────────────────

def supervisor_agent(state: TravelState) -> dict:
    inp = state["trip_input"]
    msg = (
        f"[Supervisor] Mission started: {inp['duration']}-day trip to "
        f"{inp['destination']} | {inp['travelers']} traveler(s) | "
        f"{inp['budget']} | Interests: {', '.join(inp.get('interests', []))}"
    )
    return {"messages": [msg]}


# ─────────────────────────────────────────────
#  Agent 2 — Destination Researcher
# ─────────────────────────────────────────────

def researcher_agent(state: TravelState) -> dict:
    llm  = get_llm(state.get("model_name"))
    inp  = state["trip_input"]

    prompt = f"""You are an expert travel researcher with deep knowledge of world destinations.

Destination: {inp['destination']}
Trip duration: {inp['duration']} days
Travelers: {inp['travelers']} person(s)
Interests: {', '.join(inp.get('interests', []))}
Travel style: {inp.get('travel_style', 'Balanced')}
Special requests: {inp.get('special_requests', 'None')}

Write a comprehensive destination brief covering:
1. DESTINATION ESSENCE (2-3 sentences — what makes it truly special)
2. TOP NEIGHBORHOODS TO STAY (3 areas with one-line description each)
3. ICONIC ATTRACTIONS (5 must-see places with a unique insider tip per place)
4. GETTING AROUND (transport options with approximate costs)
5. CULTURE & CUSTOMS (3 etiquette tips that matter)
6. SAFETY SNAPSHOT (2-3 practical tips)
7. IDEAL VISIT TIMING (best season and why)

Write in an engaging, expert tone. Use real place names. Max 450 words."""

    result = llm_call(llm, prompt, "Researcher")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "destination_info": result if not result.startswith("__ERROR__") else "",
        "messages": ["[Researcher] ✓ Destination intelligence gathered"],
        "errors":   errors,
    }


# ─────────────────────────────────────────────
#  Agent 3 — Weather Advisor
# ─────────────────────────────────────────────

def weather_agent(state: TravelState) -> dict:
    llm = get_llm(state.get("model_name"))
    inp = state["trip_input"]

    prompt = f"""You are a travel weather and climate expert.
Destination: {inp['destination']} | Trip: {inp['duration']} days

Respond ONLY with a valid JSON object — no markdown, no extra text:
{{
  "season_overview": "2 sentence climate summary",
  "temperature_range": "XX°C - XX°C (XX°F - XX°F) typical range",
  "humidity": "Low / Moderate / High",
  "rainfall": "Brief rain pattern description",
  "best_months": ["Month1", "Month2", "Month3"],
  "shoulder_months": ["Month1", "Month2"],
  "avoid_if_possible": ["Month1"],
  "clothing_advice": "Specific clothing recommendation",
  "umbrella_needed": true,
  "sun_protection": true,
  "weather_warning": "Any extreme weather risks to know about or null"
}}"""

    result = llm_call(llm, prompt, "Weather")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "weather_raw": result,
        "messages": ["[Weather Advisor] ✓ Climate analysis complete"],
        "errors":    errors,
    }


# ─────────────────────────────────────────────
#  Agent 4 — Accommodation Scout
# ─────────────────────────────────────────────

def accommodation_agent(state: TravelState) -> dict:
    llm = get_llm(state.get("model_name"))
    inp = state["trip_input"]

    prompt = f"""You are a world-class travel accommodation expert.

Destination: {inp['destination']} | Travelers: {inp['travelers']}
Duration: {inp['duration']} nights | Budget: {inp['budget']}
Style: {inp.get('travel_style','Balanced')} | Requests: {inp.get('special_requests','None')}

Respond ONLY with a valid JSON array — no markdown, no extra text:
[
  {{
    "name": "Specific real or realistic hotel name",
    "type": "Hotel / Boutique / Hostel / Apartment / Resort",
    "stars": 3,
    "price_range": "$XX - $XX per night",
    "neighborhood": "Specific neighborhood name",
    "description": "2 vivid sentences about why this property stands out",
    "top_amenity": "Single best feature",
    "pros": "Biggest advantage for this trip",
    "cons": "One honest limitation",
    "best_for": "Type of traveler this suits most",
    "booking_tip": "One tip for getting the best deal"
  }}
]

Include one budget option, one mid-range, one premium. Return ONLY the JSON array."""

    result = llm_call(llm, prompt, "Accommodation")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "accommodations_raw": result,
        "messages": ["[Accommodation Scout] ✓ Stay options identified"],
        "errors":   errors,
    }


# ─────────────────────────────────────────────
#  Agent 5 — Activity Curator
# ─────────────────────────────────────────────

def activity_agent(state: TravelState) -> dict:
    llm = get_llm(state.get("model_name"))
    inp = state["trip_input"]
    dur = int(inp["duration"])

    prompt = f"""You are an elite travel activities curator with insider knowledge of {inp['destination']}.

Travelers: {inp['travelers']} | Interests: {', '.join(inp.get('interests', []))}
Budget: {inp['budget']} | Style: {inp.get('travel_style','Balanced')}
Special requests: {inp.get('special_requests','None')}

Create a detailed day-by-day itinerary. Return ONLY a valid JSON array with EXACTLY {dur} objects:
[
  {{
    "day": 1,
    "title": "Evocative day title",
    "theme_emoji": "🗺️",
    "activities": [
      {{"time": "8:00 AM",  "activity": "Specific named place or experience", "description": "What to do and why it's special", "cost": "$X-XX", "duration": "~Xh", "pro_tip": "Insider tip"}},
      {{"time": "11:00 AM", "activity": "Activity name", "description": "Details", "cost": "$X-XX", "duration": "~Xh", "pro_tip": "Tip"}},
      {{"time": "1:00 PM",  "activity": "Lunch spot type or name", "description": "What to eat", "cost": "$X-XX", "duration": "~1h", "pro_tip": "Tip"}},
      {{"time": "3:00 PM",  "activity": "Afternoon activity", "description": "Details", "cost": "$X-XX", "duration": "~Xh", "pro_tip": "Tip"}},
      {{"time": "7:00 PM",  "activity": "Evening plan", "description": "Dinner and evening", "cost": "$X-XX", "duration": "~2h", "pro_tip": "Tip"}}
    ],
    "day_highlights": "One sentence summary of the day",
    "transport_for_day": "How to get around today",
    "estimated_daily_cost": "$XXX - $XXX per person"
  }}
]

Use real attraction names. Make each day feel distinct. Return ONLY the JSON array."""

    result = llm_call(llm, prompt, "Activity Curator")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "activities_raw": result,
        "messages": ["[Activity Curator] ✓ Day-by-day itinerary crafted"],
        "errors":   errors,
    }


# ─────────────────────────────────────────────
#  Agent 6 — Food & Dining Guide
# ─────────────────────────────────────────────

def food_agent(state: TravelState) -> dict:
    llm = get_llm(state.get("model_name"))
    inp = state["trip_input"]

    prompt = f"""You are a Michelin-level culinary travel expert for {inp['destination']}.

Travelers: {inp['travelers']} | Budget: {inp['budget']}
Dietary/special notes: {inp.get('special_requests','None')}

Return ONLY a valid JSON object — no markdown, no extra text:
{{
  "culinary_intro": "2 sentences about the food culture of this destination",
  "must_try_dishes": [
    {{"name": "Dish name", "description": "What it is and why it's unmissable", "find_at": "Where to get it", "avg_cost": "$X-XX"}},
    {{"name": "Dish name", "description": "...", "find_at": "...", "avg_cost": "$X-XX"}},
    {{"name": "Dish name", "description": "...", "find_at": "...", "avg_cost": "$X-XX"}},
    {{"name": "Dish name", "description": "...", "find_at": "...", "avg_cost": "$X-XX"}}
  ],
  "restaurants": [
    {{"name": "Restaurant name", "vibe": "Casual / Fine dining / Street food / Market", "cuisine": "Type", "price": "$ to $$$$", "signature_dish": "What to order", "neighborhood": "Area", "why_go": "One sentence reason"}},
    {{"name": "...", "vibe": "...", "cuisine": "...", "price": "...", "signature_dish": "...", "neighborhood": "...", "why_go": "..."}},
    {{"name": "...", "vibe": "...", "cuisine": "...", "price": "...", "signature_dish": "...", "neighborhood": "...", "why_go": "..."}},
    {{"name": "...", "vibe": "...", "cuisine": "...", "price": "...", "signature_dish": "...", "neighborhood": "...", "why_go": "..."}},
    {{"name": "...", "vibe": "...", "cuisine": "...", "price": "...", "signature_dish": "...", "neighborhood": "...", "why_go": "..."}}
  ],
  "food_markets": [
    {{"name": "Market name", "specialty": "What it's known for", "best_time": "When to visit"}}
  ],
  "drink_culture": "Local drinks and where to have them",
  "food_etiquette": "One important dining custom",
  "dietary_advice": "Advice for the stated dietary needs"
}}"""

    result = llm_call(llm, prompt, "Food Guide")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "food_raw": result,
        "messages": ["[Food Agent] ✓ Culinary guide compiled"],
        "errors":   errors,
    }


# ─────────────────────────────────────────────
#  Agent 7 — Budget Planner
# ─────────────────────────────────────────────

def budget_agent(state: TravelState) -> dict:
    llm = get_llm(state.get("model_name"))
    inp = state["trip_input"]
    dur = inp["duration"]
    travelers = inp["travelers"]

    prompt = f"""You are a travel budget expert with deep knowledge of costs in {inp['destination']}.

Trip: {dur} days | Travelers: {travelers} | Budget level: {inp['budget']}

Return ONLY a valid JSON object — no markdown, no extra text:
{{
  "currency_info": {{"local_currency": "Name", "symbol": "Symbol", "usd_rate": "Approx rate"}},
  "per_person_breakdown": {{
    "flights_roundtrip": "$XXX - $XXX",
    "accommodation_total": "$XXX - $XXX for {dur} nights",
    "food_daily": "$XX - $XX per day",
    "activities_total": "$XXX - $XXX",
    "local_transport_daily": "$XX - $XX per day",
    "sim_card_data": "$XX - $XX",
    "travel_insurance": "$XX - $XX",
    "visa_fee": "$XX or Free",
    "shopping_buffer": "$XXX",
    "emergency_buffer": "$XXX",
    "total_per_person": "$X,XXX - $X,XXX"
  }},
  "total_for_group": "$X,XXX - $X,XXX for {travelers} traveler(s)",
  "daily_budget_target": "$XXX - $XXX per person per day",
  "budget_breakdown_percent": {{
    "transport": "XX%",
    "accommodation": "XX%",
    "food": "XX%",
    "activities": "XX%",
    "other": "XX%"
  }},
  "money_saving_hacks": ["Hack 1", "Hack 2", "Hack 3", "Hack 4"],
  "splurge_worthy": "One experience worth spending extra on",
  "atm_card_tips": "Cash vs card advice for this destination",
  "tipping_culture": "Tipping norms at this destination"
}}"""

    result = llm_call(llm, prompt, "Budget Planner")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "budget_raw": result,
        "messages": ["[Budget Planner] ✓ Financial plan ready"],
        "errors":   errors,
    }


# ─────────────────────────────────────────────
#  Agent 8 — Smart Packing Agent
# ─────────────────────────────────────────────

def packing_agent(state: TravelState) -> dict:
    llm = get_llm(state.get("model_name"))
    inp = state["trip_input"]
    weather = parse_json(state.get("weather_raw", "{}"), {})
    temp = weather.get("temperature_range", "moderate temperatures")
    umbrella = weather.get("umbrella_needed", True)

    prompt = f"""You are a professional travel packing consultant.

Destination: {inp['destination']} | Duration: {inp['duration']} days
Weather: {temp} | Rain expected: {umbrella}
Activities: {', '.join(inp.get('interests', []))}
Travelers: {inp['travelers']} | Special: {inp.get('special_requests','None')}

Return ONLY a valid JSON object — no markdown, no extra text:
{{
  "packing_philosophy": "One-line packing strategy for this trip",
  "bag_recommendation": "Type and size of bag recommended",
  "essentials": ["item1", "item2", "item3", "item4", "item5", "item6"],
  "clothing": {{
    "tops": ["item1", "item2", "item3"],
    "bottoms": ["item1", "item2"],
    "outerwear": ["item1"],
    "footwear": ["item1", "item2"],
    "accessories": ["item1", "item2"]
  }},
  "toiletries": ["item1", "item2", "item3", "item4"],
  "health_safety": ["item1", "item2", "item3"],
  "electronics": ["item1", "item2", "item3", "item4"],
  "documents_money": ["Passport", "item2", "item3", "item4", "item5"],
  "activity_gear": ["Specific to their interests 1", "item2", "item3"],
  "do_not_pack": ["Unnecessary item 1", "item2", "item3"],
  "buy_there": ["Things cheaper to buy at destination 1", "item2"],
  "weight_tip": "Advice on keeping bag light"
}}"""

    result = llm_call(llm, prompt, "Packing Agent")
    errors = [result] if result.startswith("__ERROR__") else []
    return {
        "packing_raw": result,
        "messages": ["[Packing Agent] ✓ Smart packing list ready"],
        "errors":   errors,
    }


# ─────────────────────────────────────────────
#  Agent 9 — Composer (Final Assembly)
# ─────────────────────────────────────────────

def composer_agent(state: TravelState) -> dict:
    llm  = get_llm(state.get("model_name"))
    inp  = state["trip_input"]

    # Parse all agent outputs with fallbacks
    accommodations = parse_json(state.get("accommodations_raw","[]"), None) or _fb_accommodations(inp)
    itinerary      = parse_json(state.get("activities_raw","[]"),    None) or _fb_itinerary(inp)
    food           = parse_json(state.get("food_raw","{}"),          None) or _fb_food(inp)
    budget         = parse_json(state.get("budget_raw","{}"),        None) or _fb_budget(inp)
    weather        = parse_json(state.get("weather_raw","{}"),       None) or {"season_overview": "Pleasant year-round", "temperature_range": "Varies by season"}
    packing        = parse_json(state.get("packing_raw","{}"),       None) or _fb_packing(inp)

    # Ensure itinerary has exactly the right number of days
    while len(itinerary) < inp["duration"]:
        day_num = len(itinerary) + 1
        itinerary.append(_fb_day(inp, day_num))

    # Trip summary
    prompt = f"""Write 2-3 vivid, inspiring sentences about a {inp['duration']}-day trip to {inp['destination']}.
{inp['travelers']} traveler(s), {inp['budget']} budget, loves {', '.join(inp.get('interests',[]))}.
Second person ("you"). Warm and exciting. No bullet points. No generic phrases."""

    summary = llm_call(llm, prompt, "Composer")
    if summary.startswith("__ERROR__"):
        summary = (f"Your {inp['duration']}-day journey through {inp['destination']} promises to be an extraordinary adventure "
                   f"crafted around your passion for {', '.join(inp.get('interests',['exploration']))}. "
                   f"Every detail has been curated to match your {inp.get('travel_style','balanced')} travel style "
                   f"and {inp['budget']} budget — from hidden local gems to iconic landmarks.")

    final = {
        "summary":          summary.strip(),
        "overview":         {
            "Destination":  inp["destination"],
            "Duration":     f"{inp['duration']} days",
            "Travelers":    str(inp["travelers"]),
            "Budget":       inp["budget"],
            "Style":        inp.get("travel_style","Balanced"),
            "Interests":    ", ".join(inp.get("interests",[])),
        },
        "destination_info": state.get("destination_info",""),
        "itinerary":        itinerary,
        "accommodations":   accommodations,
        "food":             food,
        "budget":           budget,
        "weather":          weather,
        "packing":          packing,
        "agent_log":        state.get("messages",[]),
        "errors":           state.get("errors",[]),
    }

    return {
        "final_result": final,
        "messages":     ["[Composer] ✓ Complete itinerary assembled!"],
    }


# ─────────────────────────────────────────────
#  JSON Parser (3-strategy, battle-tested)
# ─────────────────────────────────────────────

def parse_json(text: str, fallback):
    if not text or text.startswith("__ERROR__"):
        return fallback
    # Strategy 1: direct
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # Strategy 2: strip markdown fences
    clean = re.sub(r"```(?:json)?\s*|```", "", text).strip()
    try:
        return json.loads(clean)
    except Exception:
        pass
    # Strategy 3: extract first complete JSON structure
    for start_ch, end_ch in [('[', ']'), ('{', '}')]:
        s = text.find(start_ch)
        if s == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[s:], s):
            depth += (ch == start_ch) - (ch == end_ch)
            if depth == 0:
                try:
                    return json.loads(text[s:i+1])
                except Exception:
                    break
    return fallback


# ─────────────────────────────────────────────
#  Fallback Generators
# ─────────────────────────────────────────────

def _fb_accommodations(inp):
    d = inp["destination"]
    return [
        {"name": f"{d} Central Hotel", "type": "Hotel", "stars": 3, "price_range": "$60-100/night", "neighborhood": "City Center",
         "description": f"Perfectly located in central {d} with easy access to all major sights.", "top_amenity": "Great location",
         "pros": "Walk to everything", "cons": "Can be busy", "best_for": "First-timers", "booking_tip": "Book 4-6 weeks ahead"},
        {"name": f"The {d} Boutique", "type": "Boutique Hotel", "stars": 4, "price_range": "$120-200/night", "neighborhood": "Old Quarter",
         "description": "Intimate boutique property with local design and personal service.", "top_amenity": "Rooftop terrace",
         "pros": "Authentic character", "cons": "Smaller rooms", "best_for": "Couples & culture lovers", "booking_tip": "Ask for courtyard room"},
        {"name": f"Grand {d} Resort", "type": "Resort", "stars": 5, "price_range": "$250-450/night", "neighborhood": "Upscale District",
         "description": "Luxury resort with world-class amenities and impeccable service.", "top_amenity": "Infinity pool + spa",
         "pros": "Ultimate comfort", "cons": "Further from city center", "best_for": "Luxury seekers", "booking_tip": "Free upgrade if you book direct"},
    ]

def _fb_day(inp, day_num):
    d = inp["destination"]
    return {
        "day": day_num, "title": f"Discovering {d}", "theme_emoji": "🗺️",
        "activities": [
            {"time": "8:00 AM",  "activity": "Morning exploration", "description": f"Start your day exploring {d}", "cost": "$5-10", "duration": "~2h", "pro_tip": "Go early to beat crowds"},
            {"time": "12:00 PM", "activity": "Local lunch",         "description": "Try a local restaurant", "cost": "$10-20", "duration": "~1h", "pro_tip": "Ask staff what's fresh today"},
            {"time": "2:00 PM",  "activity": "Landmark visit",      "description": "Visit a key attraction", "cost": "$10-20", "duration": "~2h", "pro_tip": "Buy tickets online in advance"},
            {"time": "7:00 PM",  "activity": "Dinner & evening",    "description": "Evening dining and stroll", "cost": "$20-40", "duration": "~2h", "pro_tip": "Explore the night market if available"},
        ],
        "day_highlights": f"A full day immersed in the best of {d}",
        "transport_for_day": "Public transport or walking",
        "estimated_daily_cost": "$60-120 per person",
    }

def _fb_itinerary(inp):
    return [_fb_day(inp, i+1) for i in range(inp["duration"])]

def _fb_food(inp):
    d = inp["destination"]
    return {
        "culinary_intro": f"{d} offers a rich and diverse food scene ranging from vibrant street food to elegant restaurants. The local cuisine reflects the culture and history of the region.",
        "must_try_dishes": [
            {"name": f"{d} Signature Dish", "description": "The iconic local dish every visitor must try.", "find_at": "Local markets and traditional restaurants", "avg_cost": "$5-15"},
            {"name": "Street Snack", "description": "Popular street food sold throughout the city.", "find_at": "Night markets and food stalls", "avg_cost": "$2-5"},
            {"name": "Local Dessert", "description": "Traditional sweet treat unique to this region.", "find_at": "Bakeries and dessert shops", "avg_cost": "$3-8"},
        ],
        "restaurants": [
            {"name": f"{d} Food Hall", "vibe": "Market", "cuisine": "Mixed Local", "price": "$", "signature_dish": "Daily special", "neighborhood": "City Center", "why_go": "Best variety at lowest prices"},
            {"name": "Traditional Kitchen", "vibe": "Casual", "cuisine": "Traditional Local", "price": "$$", "signature_dish": "Chef's recommendation", "neighborhood": "Old Town", "why_go": "Authentic recipes unchanged for decades"},
            {"name": "The Modern Table", "vibe": "Fine dining", "cuisine": "Contemporary Local", "price": "$$$", "signature_dish": "Tasting menu", "neighborhood": "Upscale District", "why_go": "Modern interpretations of classic flavors"},
        ],
        "food_markets": [{"name": f"{d} Central Market", "specialty": "Local produce and street food", "best_time": "Morning"}],
        "drink_culture": "Ask locals for the traditional drink of choice.",
        "food_etiquette": "Observe how locals eat and follow their lead.",
        "dietary_advice": "Vegetarian and dietary options are generally available — communicate needs clearly."
    }

def _fb_budget(inp):
    days, travelers = inp["duration"], inp["travelers"]
    base = {"Budget ($500-1000)": 700, "Mid-range ($1000-3000)": 2000, "Luxury ($3000+)": 5000}
    pp = base.get(inp["budget"], 1500)
    total = pp * travelers
    return {
        "currency_info": {"local_currency": "Local currency", "symbol": "varies", "usd_rate": "Check xe.com"},
        "per_person_breakdown": {
            "flights_roundtrip": f"${int(pp*.32):,} - ${int(pp*.38):,}",
            "accommodation_total": f"${int(pp*.26):,} - ${int(pp*.30):,} for {days} nights",
            "food_daily": f"${int(pp*.14/days):,} - ${int(pp*.18/days):,} per day",
            "activities_total": f"${int(pp*.10):,} - ${int(pp*.14):,}",
            "local_transport_daily": f"${int(pp*.05/days):,} - ${int(pp*.07/days):,} per day",
            "sim_card_data": "$10 - $25",
            "travel_insurance": "$50 - $120",
            "visa_fee": "Varies by nationality",
            "shopping_buffer": f"${int(pp*.06):,}",
            "emergency_buffer": f"${int(pp*.04):,}",
            "total_per_person": f"${int(pp*.9):,} - ${int(pp*1.1):,}",
        },
        "total_for_group": f"${int(total*.9):,} - ${int(total*1.1):,} for {travelers} traveler(s)",
        "daily_budget_target": f"${int(pp/days):,} - ${int(pp*1.1/days):,} per person per day",
        "budget_breakdown_percent": {"transport": "35%", "accommodation": "28%", "food": "17%", "activities": "12%", "other": "8%"},
        "money_saving_hacks": ["Book flights 6-8 weeks ahead", "Eat lunch at restaurants (cheaper than dinner)", "Use local public transport", "Stay in residential neighborhoods"],
        "splurge_worthy": "One memorable fine dining experience or iconic tour",
        "atm_card_tips": "Carry some local cash for markets and small vendors. Notify your bank before travel.",
        "tipping_culture": "Research local tipping norms — they vary widely by destination."
    }

def _fb_packing(inp):
    return {
        "packing_philosophy": "Pack light, pack smart — everything you need, nothing you don't",
        "bag_recommendation": "20-30L carry-on backpack for most trips",
        "essentials": ["Passport (+ digital copy)", "Travel insurance docs", "Local currency + backup card", "Phone + charger", "Portable power bank", "Power adapter"],
        "clothing": {"tops": ["3-4 versatile tops", "1 smart shirt/blouse", "1 light layer"], "bottoms": ["2 pairs of pants/skirts", "1 pair shorts if warm"], "outerwear": ["Light rain jacket"], "footwear": ["Comfortable walking shoes", "1 dressier option"], "accessories": ["Sunglasses", "Compact day bag"]},
        "toiletries": ["Sunscreen SPF 50+", "Personal medications", "Basic first aid kit", "Hand sanitizer"],
        "health_safety": ["Travel-size first aid", "Any prescription medications x2 supply", "Motion sickness tabs if needed"],
        "electronics": ["Phone + charger", "Portable power bank", "Earphones", "Camera (optional)"],
        "documents_money": ["Passport", "Visa/entry docs", "Booking confirmations printed", "Emergency contact card", "Travel insurance card"],
        "activity_gear": ["Comfortable daypack", "Reusable water bottle", "Compact umbrella"],
        "do_not_pack": ["More than 2 pairs of shoes", "Full-size shampoo/conditioner", "Travel iron"],
        "buy_there": ["Sunscreen (often cheaper locally)", "Snacks and water", "Souvenirs — obviously"],
        "weight_tip": "If your bag weighs more than 10kg for a 1-week trip, start removing."
    }


# ─────────────────────────────────────────────
#  Build & Compile LangGraph
# ─────────────────────────────────────────────

def build_graph():
    g = StateGraph(TravelState)

    g.add_node("supervisor",    supervisor_agent)
    g.add_node("researcher",    researcher_agent)
    g.add_node("weather",       weather_agent)
    g.add_node("accommodation", accommodation_agent)
    g.add_node("activity",      activity_agent)
    g.add_node("food",          food_agent)
    g.add_node("budget",        budget_agent)
    g.add_node("packing",       packing_agent)
    g.add_node("composer",      composer_agent)

    # Entry point
    g.set_entry_point("supervisor")

    # supervisor → researcher
    g.add_edge("supervisor", "researcher")

    # researcher fans out to 5 parallel agents
    for node in ["weather", "accommodation", "activity", "food", "budget"]:
        g.add_edge("researcher", node)

    # all 5 converge to packing (LangGraph merges via Annotated)
    for node in ["weather", "accommodation", "activity", "food", "budget"]:
        g.add_edge(node, "packing")

    # packing → composer → END
    g.add_edge("packing",  "composer")
    g.add_edge("composer", END)

    return g.compile()


# ─────────────────────────────────────────────
#  Public Entry Point
# ─────────────────────────────────────────────

def run_travel_planner(trip_input: dict, model_name: str = "llama3.2") -> dict:
    """Run the full 9-agent pipeline. Returns structured result dict."""
    graph = build_graph()
    initial: TravelState = {
        "trip_input":         trip_input,
        "model_name":         model_name,
        "destination_info":   "",
        "weather_raw":        "",
        "accommodations_raw": "",
        "activities_raw":     "",
        "food_raw":           "",
        "budget_raw":         "",
        "packing_raw":        "",
        "final_result":       {},
        "messages":           [],
        "errors":             [],
    }
    final = graph.invoke(initial)
    return final["final_result"]
