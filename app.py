"""
app.py — AI Travel Planner, Streamlit front end.

Highlights
----------
* **Real** progress. The agent tracker is driven by ``stream_travel_planner``,
  which yields once per agent completion — no timers, no fake animation.
* Provider switching with a live health probe before you spend a minute waiting.
* Live-data panels: an actual map, actual climate normals, actual FX rates.
* Four export formats generated on demand.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from travel_planner.agents import AGENT_META
from travel_planner.config import PROVIDER_LABELS, SUGGESTED_MODELS, get_settings
from travel_planner.exporters import (
    generate_ics,
    generate_markdown,
    generate_pdf,
    generate_text,
)
from travel_planner.graph import stream_travel_planner
from travel_planner.llm import health_check
from travel_planner.schemas import TripInput
from travel_planner.tools import geocode

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
#  Theme
# ─────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"], .stApp { font-family:'DM Sans',sans-serif; }
.stApp { background:#080810; color:#f0ece4; }
.block-container { padding-top:2rem !important; max-width:1180px !important; }

.hero { text-align:center; padding:2rem 0 1rem; }
.hero-eyebrow { font-size:.72rem; letter-spacing:.28em; text-transform:uppercase;
    color:#c8a96e; font-weight:500; margin-bottom:.6rem; }
.hero-title { font-family:'Playfair Display',serif; font-size:clamp(2.6rem,6vw,4.6rem);
    font-weight:900; color:#f0ece4; line-height:1; letter-spacing:-2px; margin:0; }
.hero-title span { color:#c8a96e; font-style:italic; }
.hero-sub { font-size:.98rem; color:#7a7060; font-weight:300; margin-top:.8rem; }

.stTextInput>div>div>input, .stTextArea>div>div>textarea,
.stNumberInput>div>div>input, .stSelectbox>div>div, .stDateInput>div>div>input {
    background:#10101a !important; border:1px solid #2a2a3a !important;
    color:#f0ece4 !important; border-radius:10px !important; }
label, .stLabel { color:#6a6055 !important; font-size:.74rem !important;
    text-transform:uppercase !important; letter-spacing:.1em !important; font-weight:500 !important; }
.stMultiSelect>div>div { background:#10101a !important; border:1px solid #2a2a3a !important;
    border-radius:10px !important; }
.stMultiSelect span[data-baseweb="tag"] { background:#2a2218 !important;
    border:1px solid #c8a96e !important; color:#c8a96e !important; }

.stButton>button { background:linear-gradient(135deg,#c8a96e,#d4b97e) !important;
    color:#080810 !important; border:none !important; border-radius:12px !important;
    font-weight:600 !important; padding:.7rem 2rem !important; width:100% !important;
    transition:all .2s !important; }
.stButton>button:hover { transform:translateY(-2px) !important;
    box-shadow:0 8px 24px rgba(200,169,110,.25) !important; }
.stDownloadButton>button { background:#10101a !important; color:#c8a96e !important;
    border:1px solid #c8a96e !important; border-radius:10px !important;
    font-weight:500 !important; width:100% !important; }
.stDownloadButton>button:hover { background:#c8a96e !important; color:#080810 !important; }

.stTabs [data-baseweb="tab-list"] { background:#10101a; border-radius:12px; padding:4px;
    border:1px solid #1e1e2e; gap:2px; }
.stTabs [data-baseweb="tab"] { background:transparent !important; color:#6a6055 !important;
    border-radius:9px !important; font-size:.84rem !important; font-weight:500 !important; }
.stTabs [aria-selected="true"] { background:#1e1e2e !important; color:#c8a96e !important; }

.card { background:#10101a; border:1px solid #1e1e2e; border-radius:14px;
    padding:1.2rem 1.4rem; margin-bottom:.8rem; }
.card-gold { border-color:#3a2e18; background:#0e0c08; }
.card-header { font-family:'Playfair Display',serif; font-size:1.08rem; color:#c8a96e;
    font-weight:700; margin-bottom:.6rem; }
.card-sub { font-size:.78rem; color:#6a6055; text-transform:uppercase;
    letter-spacing:.1em; font-weight:500; }

.agent-box { background:#0e0e18; border:1px solid #1e1e2e; border-radius:10px;
    padding:.7rem .9rem; text-align:center; transition:all .3s; }
.agent-box.active { border-color:#c8a96e; background:#130f05;
    box-shadow:0 0 20px rgba(200,169,110,.15); }
.agent-box.done { border-color:#2a5a2a; background:#080e08; }
.agent-box.warn { border-color:#6a5a20; background:#12100a; }
.agent-icon { font-size:1.3rem; }
.agent-name { font-size:.66rem; font-weight:600; letter-spacing:.09em;
    text-transform:uppercase; color:#6a6055; }
.agent-status { font-size:.74rem; margin-top:.15rem; color:#f0ece4; min-height:1rem; }

.act-row { display:flex; gap:1rem; padding:.6rem 0; border-bottom:1px solid #161620;
    align-items:flex-start; }
.act-time { color:#6a6055; font-size:.78rem; min-width:70px; padding-top:2px;
    font-weight:500; flex-shrink:0; }
.act-name { font-size:.9rem; font-weight:500; color:#f0ece4; }
.act-desc { font-size:.83rem; color:#8a8070; margin-top:2px; line-height:1.5; }
.meta-chip { font-size:.71rem; padding:2px 8px; border-radius:999px; background:#1e1e2e;
    color:#c8a96e; border:1px solid #2a2a3a; margin-right:.35rem; }
.pro-tip { font-size:.78rem; color:#8a7040; font-style:italic; margin-top:4px;
    padding-left:.5rem; border-left:2px solid #3a2e18; }

.summary-box { background:linear-gradient(135deg,#0e0c08,#130f05); border:1px solid #3a2e18;
    border-radius:14px; padding:1.4rem 1.7rem; margin:1rem 0; }
.summary-text { font-family:'Playfair Display',serif; font-size:1.12rem; color:#e8d5a3;
    line-height:1.7; font-style:italic; }

.chip-row { display:flex; flex-wrap:wrap; gap:.4rem; margin:.8rem 0; }
.ov-chip { font-size:.77rem; padding:.3rem .9rem; border-radius:999px; background:#1a1a2e;
    border:1px solid #2a2a4a; color:#9090c0; font-weight:500; }
.src-chip { font-size:.72rem; padding:.25rem .8rem; border-radius:999px; background:#08160c;
    border:1px solid #2a5a2a; color:#6aba6a; font-weight:500; margin-right:.35rem; }

.section-title { font-family:'Playfair Display',serif; font-size:1.4rem; font-weight:700;
    color:#f0ece4; margin:1.4rem 0 .7rem; padding-bottom:.45rem; border-bottom:1px solid #3a2e18; }
.dim-text { color:#6a6055; font-size:.84rem; }
.tip-bar { background:#130f05; border-left:3px solid #c8a96e; border-radius:0 8px 8px 0;
    padding:.55rem 1rem; margin:.45rem 0; font-size:.85rem; color:#b09060; }
.risk-bar { background:#180d08; border-left:3px solid #b06a30; border-radius:0 8px 8px 0;
    padding:.55rem 1rem; margin:.45rem 0; font-size:.85rem; color:#c08a5a; }
.fix-bar { background:#08160c; border-left:3px solid #2a7a2a; border-radius:0 8px 8px 0;
    padding:.55rem 1rem; margin:.45rem 0; font-size:.85rem; color:#7aba7a; }
.error-bar { background:#180808; border-left:3px solid #8b2222; border-radius:0 8px 8px 0;
    padding:.55rem 1rem; font-size:.82rem; color:#c07070; }

.stProgress>div>div { background:linear-gradient(90deg,#c8a96e,#d4b97e) !important; }
details { background:#10101a !important; border:1px solid #1e1e2e !important;
    border-radius:12px !important; }
summary { color:#f0ece4 !important; font-weight:500 !important; }
hr { border-color:#1e1e2e !important; }
</style>
""",
    unsafe_allow_html=True,
)

settings = get_settings()

st.markdown(
    """
<div class="hero">
  <div class="hero-eyebrow">✦ 10-Agent LangGraph System ✦</div>
  <h1 class="hero-title">AI <span>Travel</span> Planner</h1>
  <p class="hero-sub">Structured multi-agent planning · grounded in live climate, currency &amp; geo data</p>
</div>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
#  Sidebar — provider, model, diagnostics
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Engine")

    available = settings.configured_providers()
    provider = st.selectbox(
        "Provider",
        available,
        index=available.index(settings.llm_provider) if settings.llm_provider in available else 0,
        format_func=lambda key: PROVIDER_LABELS[key],
    )

    suggestions = SUGGESTED_MODELS.get(provider, [])
    default_model = settings.default_model_for(provider)
    options = list(dict.fromkeys([default_model, *suggestions]))
    model_name = st.selectbox("Model", options, index=0)

    if st.button("🩺 Test connection"):
        with st.spinner("Probing provider…"):
            healthy, detail = health_check(provider, model_name)
        (st.success if healthy else st.error)(
            f"{'Connected' if healthy else 'Unreachable'} — {detail}"
        )

    missing = [key for key in PROVIDER_LABELS if key not in available]
    if missing:
        st.caption("Not configured: " + ", ".join(missing))
        st.caption("Add API keys to `.env` to unlock them.")

    st.markdown("---")
    st.markdown("### 🔗 Live grounding")
    st.caption(
        "Enabled" if settings.enable_live_data else "Disabled — set ENABLE_LIVE_DATA=true"
    )
    for source in (
        "Open-Meteo geocoding",
        "ERA5 climate normals",
        "REST Countries",
        "ECB exchange rates",
        "Wikipedia",
    ):
        st.markdown(f"<span class='src-chip'>{source}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🤖 Agent pipeline")
    for _, icon, name, description in AGENT_META:
        st.markdown(f"**{icon} {name}** — <span class='dim-text'>{description}</span>",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  Input form
# ─────────────────────────────────────────────────────────────

st.markdown("---")

with st.form("trip_form"):
    left, middle, right = st.columns([1.25, 1, 1])

    with left:
        destination = st.text_input("Destination", placeholder="e.g. Kyoto, Japan")
        interests = st.multiselect(
            "Your interests",
            [
                "Culture & History", "Food & Cuisine", "Adventure & Outdoors",
                "Art & Museums", "Shopping", "Nightlife", "Nature & Wildlife",
                "Photography", "Relaxation & Spa", "Architecture", "Local Markets",
                "Music & Live Events", "Coffee & Cafés",
            ],
            default=["Culture & History", "Food & Cuisine"],
        )

    with middle:
        duration = st.number_input("Duration (days)", min_value=1, max_value=30, value=5)
        travelers = st.number_input("Travellers", min_value=1, max_value=20, value=2)
        start_date = st.date_input("Departure date", value=date.today() + timedelta(days=30))

    with right:
        budget = st.selectbox(
            "Budget tier",
            ["Budget", "Mid-range", "Luxury"],
            index=1,
            format_func=lambda tier: {
                "Budget": "Budget · $500-1,000 pp",
                "Mid-range": "Mid-range · $1,000-3,000 pp",
                "Luxury": "Luxury · $3,000+ pp",
            }[tier],
        )
        travel_style = st.selectbox(
            "Travel style",
            [
                "Balanced", "Packed (max activities)", "Relaxed (slow travel)",
                "Off-the-beaten-path", "Family-friendly", "Solo & social",
            ],
        )

    special = st.text_area(
        "Special requests (dietary, accessibility, must-dos…)",
        placeholder="e.g. vegetarian, step-free access, one day trip outside the city",
        height=72,
    )

    submitted = st.form_submit_button("✈️  Generate my itinerary")

# ─────────────────────────────────────────────────────────────
#  Execution — real streaming progress
# ─────────────────────────────────────────────────────────────


def _render_agent(placeholder, icon: str, name: str, state: str, note: str) -> None:
    colour = {"done": "#5aaa5a", "warn": "#c8a96e", "active": "#f0ece4"}.get(state, "#2a2a3a")
    placeholder.markdown(
        f"""<div class="agent-box {state}">
            <div class="agent-icon">{icon}</div>
            <div class="agent-name">{name}</div>
            <div class="agent-status" style="color:{colour}">{note}</div>
        </div>""",
        unsafe_allow_html=True,
    )


if submitted:
    try:
        trip = TripInput(
            destination=destination,
            duration=int(duration),
            travelers=int(travelers),
            budget=budget,
            interests=interests,
            travel_style=travel_style,
            special_requests=special.strip() or "None",
            start_month=start_date.strftime("%B"),
        )
    except Exception as exc:
        st.error(f"Please check your inputs — {exc}")
        st.stop()

    st.markdown("### 🤖 Agents at work")

    placeholders: dict[str, tuple] = {}
    for row_start in range(0, len(AGENT_META), 5):
        row = AGENT_META[row_start : row_start + 5]
        columns = st.columns(len(row))
        for column, (key, icon, name, _) in zip(columns, row, strict=True):
            with column:
                placeholder = st.empty()
                placeholders[key] = (placeholder, icon, name)
                _render_agent(placeholder, icon, name, "", "queued")

    progress = st.progress(0.0)
    status = st.empty()
    started = time.perf_counter()
    result: dict = {}
    completed = 0

    try:
        for agent_name, update in stream_travel_planner(
            trip, provider=provider, model_name=model_name
        ):
            if agent_name not in placeholders:
                continue
            placeholder, icon, name = placeholders[agent_name]
            degraded = bool(update.get("errors"))
            timing = (update.get("timings") or [{}])[0]
            seconds = timing.get("seconds", 0)
            _render_agent(
                placeholder,
                icon,
                name,
                "warn" if degraded else "done",
                f"{'fallback' if degraded else 'done'} · {seconds}s",
            )
            completed += 1
            progress.progress(min(completed / len(AGENT_META), 1.0))
            status.markdown(
                f"*{icon} {name} finished — {completed}/{len(AGENT_META)} agents · "
                f"{round(time.perf_counter() - started, 1)}s elapsed*"
            )
            if update.get("final_result"):
                result = update["final_result"]
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
        if provider == "ollama":
            st.info(
                "Ollama not responding? Start it with `ollama serve` and pull the model "
                f"with `ollama pull {model_name}`. Or switch to a cloud provider in the sidebar."
            )
        st.stop()

    if not result:
        st.error("The pipeline finished without producing a plan. Check the agent log below.")
        st.stop()

    progress.progress(1.0)
    status.markdown(
        f"**✅ Plan ready in {round(time.perf_counter() - started, 1)}s**"
    )
    st.session_state["result"] = result
    st.session_state["trip"] = trip.model_dump()
    st.session_state["start_date"] = start_date

# ─────────────────────────────────────────────────────────────
#  Results
# ─────────────────────────────────────────────────────────────

if "result" in st.session_state:
    result = st.session_state["result"]
    trip_data = st.session_state["trip"]
    trip_start = st.session_state.get("start_date", date.today() + timedelta(days=30))
    dest_name = trip_data["destination"]
    slug = dest_name.replace(" ", "_").replace(",", "")

    st.markdown("---")

    if result.get("summary"):
        st.markdown(
            f'<div class="summary-box"><p class="summary-text">{result["summary"]}</p></div>',
            unsafe_allow_html=True,
        )

    chips = "".join(
        f'<span class="ov-chip">{key}: {value}</span>'
        for key, value in (result.get("overview") or {}).items()
    )
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)

    sources = result.get("live_sources") or []
    if sources:
        badges = "".join(f'<span class="src-chip">✓ {s}</span>' for s in sources)
        st.markdown(f"<div>{badges}</div>", unsafe_allow_html=True)

    errors = result.get("errors") or []
    if errors:
        with st.expander(f"⚠️ {len(errors)} agent(s) degraded to fallback data"):
            for message in errors:
                st.markdown(f'<div class="error-bar">{message}</div>', unsafe_allow_html=True)

    # ── Downloads ────────────────────────────────────────────────────────
    st.markdown("")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        try:
            st.download_button(
                "📄 PDF",
                data=generate_pdf(result),
                file_name=f"{slug}_itinerary.pdf",
                mime="application/pdf",
            )
        except Exception as exc:
            st.caption(f"PDF unavailable: {exc}")
    with d2:
        st.download_button(
            "📝 Markdown",
            data=generate_markdown(result),
            file_name=f"{slug}_itinerary.md",
            mime="text/markdown",
        )
    with d3:
        st.download_button(
            "📥 Text",
            data=generate_text(result),
            file_name=f"{slug}_itinerary.txt",
            mime="text/plain",
        )
    with d4:
        st.download_button(
            "📅 Calendar",
            data=generate_ics(result, trip_start),
            file_name=f"{slug}_itinerary.ics",
            mime="text/calendar",
        )

    st.markdown("---")

    tabs = st.tabs(
        [
            "📅 Itinerary", "🗺 Map & Weather", "🏨 Stays", "🍜 Food",
            "💰 Budget", "🧳 Packing", "🧠 Review", "🔬 Trace",
        ]
    )

    # ── Itinerary ────────────────────────────────────────────────────────
    with tabs[0]:
        brief = result.get("destination") or {}
        if brief.get("essence"):
            with st.expander("📍 Destination brief", expanded=False):
                st.markdown(brief["essence"])
                for label, key in (
                    ("Where to stay", "best_neighborhoods"),
                    ("Do not miss", "iconic_attractions"),
                    ("Local customs", "culture_customs"),
                    ("Safety", "safety_notes"),
                    ("Useful phrases", "language_phrases"),
                ):
                    items = brief.get(key) or []
                    if items:
                        st.markdown(f"**{label}**")
                        for item in items:
                            st.markdown(f"- {item}")
                if brief.get("getting_around"):
                    st.markdown(f"**Getting around** — {brief['getting_around']}")

        for day in result.get("itinerary", []):
            day_number = day.get("day", "?")
            day_date = trip_start + timedelta(days=int(day_number) - 1)
            label = (
                f"{day.get('theme_emoji', '🗺️')} Day {day_number} "
                f"({day_date.strftime('%a %d %b')}) — {day.get('title', '')}"
            )
            with st.expander(label, expanded=(day_number == 1)):
                if day.get("day_highlights"):
                    st.markdown(
                        f'<div class="tip-bar">{day["day_highlights"]}</div>',
                        unsafe_allow_html=True,
                    )
                rows = ""
                for activity in day.get("activities", []):
                    chips_html = ""
                    if activity.get("cost"):
                        chips_html += f'<span class="meta-chip">💵 {activity["cost"]}</span>'
                    if activity.get("duration"):
                        chips_html += f'<span class="meta-chip">⏱ {activity["duration"]}</span>'
                    if activity.get("category"):
                        chips_html += f'<span class="meta-chip">{activity["category"]}</span>'
                    tip = activity.get("pro_tip")
                    rows += f"""
                    <div class="act-row">
                      <div class="act-time">{activity.get('time', '')}</div>
                      <div style="flex:1">
                        <div class="act-name">{activity.get('activity', '')}</div>
                        <div class="act-desc">{activity.get('description', '')}</div>
                        <div style="margin-top:4px">{chips_html}</div>
                        {f'<div class="pro-tip">💡 {tip}</div>' if tip else ''}
                      </div>
                    </div>"""
                st.markdown(rows, unsafe_allow_html=True)

                footer = [
                    part
                    for part in (
                        f"🚌 {day.get('transport_for_day', '')}"
                        if day.get("transport_for_day") else "",
                        f"💵 {day.get('estimated_daily_cost', '')}"
                        if day.get("estimated_daily_cost") else "",
                        f"🚶 ~{day.get('walking_distance_km', 0)} km"
                        if day.get("walking_distance_km") else "",
                    )
                    if part
                ]
                if footer:
                    st.markdown(
                        f'<div class="dim-text" style="margin-top:.5rem">{" · ".join(footer)}</div>',
                        unsafe_allow_html=True,
                    )

    # ── Map & weather ────────────────────────────────────────────────────
    with tabs[1]:
        geo = result.get("geo") or {}
        if geo.get("latitude") or geo.get("longitude"):
            st.markdown(
                f"**{geo.get('name', dest_name)}, {geo.get('country', '')}** · "
                f"{geo.get('latitude', 0):.4f}, {geo.get('longitude', 0):.4f} · "
                f"timezone {geo.get('timezone', 'n/a')}"
            )
            st.map(
                pd.DataFrame(
                    {"lat": [geo.get("latitude", 0.0)], "lon": [geo.get("longitude", 0.0)]}
                ),
                zoom=9,
            )
        else:
            st.info("Live geocoding was unavailable, so no map could be drawn.")

        weather = result.get("weather") or {}
        left, right = st.columns(2)
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">🌡️ Climate</div>', unsafe_allow_html=True)
            st.markdown(weather.get("season_overview", ""))
            for label, key in (
                ("Temperature", "temperature_range"),
                ("Humidity", "humidity"),
                ("Rainfall", "rainfall"),
            ):
                if weather.get(key):
                    st.markdown(f"**{label}:** {weather[key]}")
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">📅 When to go</div>', unsafe_allow_html=True)
            for label, key in (
                ("Best", "best_months"),
                ("Shoulder", "shoulder_months"),
                ("Avoid", "avoid_if_possible"),
            ):
                if weather.get(key):
                    st.markdown(f"**{label}:** {' · '.join(weather[key])}")
            if weather.get("weather_warning"):
                st.markdown(
                    f'<div class="error-bar">⚠️ {weather["weather_warning"]}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        if weather.get("clothing_advice"):
            st.markdown(
                f'<div class="tip-bar">👗 {weather["clothing_advice"]}</div>',
                unsafe_allow_html=True,
            )

        # Measured climate chart, straight from ERA5.
        if geo.get("latitude"):
            from travel_planner.tools import climate_normals

            normals = climate_normals(geo["latitude"], geo["longitude"])
            if normals:
                st.markdown(
                    '<div class="section-title" style="font-size:1.05rem">'
                    "📊 Measured monthly normals (ERA5 reanalysis)</div>",
                    unsafe_allow_html=True,
                )
                frame = pd.DataFrame(normals["months"]).set_index("month")
                st.line_chart(frame[["avg_high_c", "avg_low_c"]], height=240)
                st.bar_chart(frame[["rain_mm"]], height=180)

    # ── Stays ────────────────────────────────────────────────────────────
    with tabs[2]:
        for stay in result.get("accommodations", []):
            stars = "⭐" * int(stay.get("stars", 3) or 3)
            st.markdown(
                f"""<div class="card card-gold">
                  <div class="card-header">🏨 {stay.get('name', '')}
                    <span class="dim-text"> · {stay.get('type', '')} · {stars}</span>
                  </div>
                  <div style="color:#c8a96e;font-size:.88rem;margin-bottom:.5rem">
                    {stay.get('price_range', '')} &nbsp;·&nbsp; 📍 {stay.get('neighborhood', '')}
                  </div>
                  <p style="color:#9a9080;font-size:.89rem;line-height:1.6">
                    {stay.get('description', '')}</p>
                  <div style="display:flex;gap:1rem;flex-wrap:wrap;font-size:.83rem">
                    <span>✅ {stay.get('pros', '')}</span>
                    <span style="color:#8a7060">⚠️ {stay.get('cons', '')}</span>
                    <span style="color:#6a6055">👤 {stay.get('best_for', '')}</span>
                  </div>
                  <div class="tip-bar" style="margin-top:.6rem">
                    💡 {stay.get('booking_tip', '')}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Food ─────────────────────────────────────────────────────────────
    with tabs[3]:
        food = result.get("food") or {}
        if food.get("culinary_intro"):
            st.markdown(
                f'<div class="summary-box"><p class="summary-text">'
                f'{food["culinary_intro"]}</p></div>',
                unsafe_allow_html=True,
            )
        left, right = st.columns(2)
        with left:
            st.markdown(
                '<div class="section-title" style="font-size:1.05rem">🍽️ Must-try dishes</div>',
                unsafe_allow_html=True,
            )
            for dish in food.get("must_try_dishes", []):
                st.markdown(
                    f"""<div class="card" style="padding:.85rem 1rem">
                      <div style="font-weight:600;color:#f0ece4">{dish.get('name', '')}</div>
                      <div style="color:#8a8070;font-size:.85rem;margin:.3rem 0">
                        {dish.get('description', '')}</div>
                      <div style="font-size:.77rem;color:#c8a96e">
                        📍 {dish.get('find_at', '')} · {dish.get('avg_cost', '')}
                        {' · ' + dish['dietary'] if dish.get('dietary') else ''}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        with right:
            st.markdown(
                '<div class="section-title" style="font-size:1.05rem">🏪 Markets & culture</div>',
                unsafe_allow_html=True,
            )
            for market in food.get("food_markets", []):
                st.markdown(
                    f"""<div class="card" style="padding:.85rem 1rem">
                      <div style="font-weight:600;color:#f0ece4">{market.get('name', '')}</div>
                      <div style="color:#8a8070;font-size:.85rem">
                        {market.get('specialty', '')} · {market.get('best_time', '')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            for emoji, key in (
                ("🥂", "drink_culture"), ("🙏", "food_etiquette"), ("🥗", "dietary_advice")
            ):
                if food.get(key):
                    st.markdown(
                        f'<div class="tip-bar">{emoji} {food[key]}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown(
            '<div class="section-title" style="font-size:1.05rem">🍴 Restaurants</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(2)
        for index, restaurant in enumerate(food.get("restaurants", [])):
            with columns[index % 2]:
                st.markdown(
                    f"""<div class="card" style="padding:.85rem 1rem">
                      <div style="font-weight:600;color:#f0ece4">{restaurant.get('name', '')}</div>
                      <div style="color:#c8a96e;font-size:.77rem;margin:.2rem 0">
                        {restaurant.get('price', '')} · {restaurant.get('vibe', '')} ·
                        {restaurant.get('neighborhood', '')}</div>
                      <div style="color:#8a8070;font-size:.83rem">
                        {restaurant.get('why_go', '')}</div>
                      <div style="color:#6a6055;font-size:.77rem;margin-top:.3rem">
                        Order: {restaurant.get('signature_dish', '')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ── Budget ───────────────────────────────────────────────────────────
    with tabs[4]:
        budget_data = result.get("budget") or {}
        left, right = st.columns([1.35, 1])
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(
                '<div class="card-header">💵 Per-person breakdown</div>', unsafe_allow_html=True
            )
            for key, value in (budget_data.get("per_person_breakdown") or {}).items():
                is_total = "total" in key.lower()
                st.markdown(
                    f"""<div style="display:flex;justify-content:space-between;padding:.38rem 0;
                         border-bottom:1px solid #161620;font-size:.87rem">
                      <span style="color:#8a8070">{key.replace('_', ' ').title()}</span>
                      <span style="color:{'#c8a96e' if is_total else '#f0ece4'};
                        font-weight:{'600' if is_total else '400'}">{value}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

            percentages = budget_data.get("budget_breakdown_percent") or {}
            if percentages:
                parsed = {}
                for key, value in percentages.items():
                    try:
                        parsed[key.title()] = float(str(value).strip().rstrip("%"))
                    except ValueError:
                        continue
                if parsed:
                    st.bar_chart(pd.DataFrame({"share %": parsed}), height=220)

        with right:
            currency = budget_data.get("currency_info") or {}
            if currency.get("local_currency"):
                st.markdown(
                    f"""<div class="card">
                      <div class="card-header">💱 Currency</div>
                      <div style="color:#8a8070;font-size:.88rem">
                        {currency.get('local_currency', '')} {currency.get('symbol', '')}</div>
                      <div style="color:#8a8070;font-size:.84rem">
                        {currency.get('usd_rate', '')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            for emoji, key in (
                ("👥 Group total:", "total_for_group"),
                ("📅 Daily target:", "daily_budget_target"),
                ("✨ Splurge on:", "splurge_worthy"),
                ("💳", "atm_card_tips"),
                ("🤝 Tipping:", "tipping_culture"),
            ):
                if budget_data.get(key):
                    st.markdown(
                        f'<div class="tip-bar">{emoji} {budget_data[key]}</div>',
                        unsafe_allow_html=True,
                    )

        hacks = budget_data.get("money_saving_hacks") or []
        if hacks:
            st.markdown(
                '<div class="section-title" style="font-size:1.05rem">💡 Money-saving hacks</div>',
                unsafe_allow_html=True,
            )
            hack_columns = st.columns(2)
            for index, hack in enumerate(hacks):
                with hack_columns[index % 2]:
                    st.markdown(f'<div class="tip-bar">{hack}</div>', unsafe_allow_html=True)

    # ── Packing ──────────────────────────────────────────────────────────
    with tabs[5]:
        packing = result.get("packing") or {}
        if packing.get("packing_philosophy"):
            st.markdown(
                f'<div class="summary-box"><p class="summary-text">'
                f'{packing["packing_philosophy"]}</p></div>',
                unsafe_allow_html=True,
            )
        if packing.get("bag_recommendation"):
            st.markdown(
                f'<div class="tip-bar">👜 {packing["bag_recommendation"]}</div>',
                unsafe_allow_html=True,
            )

        columns = st.columns(2)
        sections = [
            ("✈️ Essentials", "essentials"),
            ("💊 Health & safety", "health_safety"),
            ("🔌 Electronics", "electronics"),
            ("📄 Documents & money", "documents_money"),
            ("🎒 Activity gear", "activity_gear"),
            ("🧴 Toiletries", "toiletries"),
            ("🛍️ Buy on arrival", "buy_there"),
            ("🚫 Leave at home", "do_not_pack"),
        ]
        for index, (label, key) in enumerate(sections):
            items = packing.get(key) or []
            if not items:
                continue
            with columns[index % 2], st.container():
                st.markdown(f"**{label}**")
                for item_index, item in enumerate(items):
                    st.checkbox(str(item), key=f"pack_{key}_{item_index}")

        clothing = packing.get("clothing") or {}
        if any(clothing.values()):
            st.markdown(
                '<div class="section-title" style="font-size:1.05rem">👗 Clothing</div>',
                unsafe_allow_html=True,
            )
            clothing_columns = st.columns(3)
            for index, (category, items) in enumerate(clothing.items()):
                if items:
                    with clothing_columns[index % 3]:
                        listing = "".join(
                            f"<li style='color:#9a9080;font-size:.85rem;padding:.15rem 0'>"
                            f"{item}</li>"
                            for item in items
                        )
                        st.markdown(
                            f"""<div class="card">
                              <div class="card-sub">{category}</div>
                              <ul style="margin:.3rem 0;padding-left:1.1rem">{listing}</ul>
                            </div>""",
                            unsafe_allow_html=True,
                        )

        if packing.get("weight_tip"):
            st.markdown(
                f'<div class="tip-bar">⚖️ {packing["weight_tip"]}</div>', unsafe_allow_html=True
            )

    # ── Review ───────────────────────────────────────────────────────────
    with tabs[6]:
        review = result.get("review") or {}
        score = int(review.get("overall_score", 0) or 0)
        st.metric("Plan confidence score", f"{score}/100")
        st.progress(score / 100)

        for label, key in (("Pacing", "pacing_verdict"), ("Budget realism", "budget_realism")):
            if review.get(key):
                st.markdown(f"**{label}** — {review[key]}")

        left, right = st.columns(2)
        with left:
            st.markdown("**⚠️ Risks the critic found**")
            for risk in review.get("risks", []) or ["None flagged."]:
                st.markdown(f'<div class="risk-bar">{risk}</div>', unsafe_allow_html=True)
        with right:
            st.markdown("**✅ Recommended fixes**")
            for fix in review.get("fixes", []) or ["Nothing to change."]:
                st.markdown(f'<div class="fix-bar">{fix}</div>', unsafe_allow_html=True)

        strengths = review.get("strengths") or []
        if strengths:
            st.markdown("**💪 Strengths**")
            for strength in strengths:
                st.markdown(f"- {strength}")

    # ── Trace ────────────────────────────────────────────────────────────
    with tabs[7]:
        meta = result.get("meta") or {}
        c1, c2, c3 = st.columns(3)
        c1.metric("Provider", str(meta.get("provider", "—")))
        c2.metric("Model", str(meta.get("model", "—")))
        c3.metric("Activities planned", str(meta.get("total_activities", "—")))

        timings = meta.get("timings") or []
        if timings:
            frame = pd.DataFrame(timings).set_index("agent")
            st.bar_chart(frame[["seconds"]], height=260)
            st.dataframe(frame, use_container_width=True)

        st.markdown("**Execution log**")
        for message in result.get("agent_log", []):
            st.code(message, language=None)

# ─────────────────────────────────────────────────────────────
#  Idle state
# ─────────────────────────────────────────────────────────────

elif not submitted:
    with st.expander("🔎 Preview live grounding for any destination"):
        probe = st.text_input("Destination to look up", value="", key="probe")
        if probe:
            point = geocode(probe)
            if point:
                st.success(
                    f"{point.name}, {point.country} — {point.latitude:.4f}, "
                    f"{point.longitude:.4f} · {point.timezone}"
                )
                st.map(pd.DataFrame({"lat": [point.latitude], "lon": [point.longitude]}), zoom=8)
            else:
                st.warning("No match found. Try adding the country, e.g. 'Porto, Portugal'.")
