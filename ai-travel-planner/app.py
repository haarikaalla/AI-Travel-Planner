"""
app.py — AI Travel Planner · Streamlit Frontend
Eye-catching dark UI with real-time agent tracking, 6 content tabs,
PDF export, model selector, and full itinerary rendering.
"""

import streamlit as st
import time
from travel_graph import run_travel_planner
from pdf_export import generate_pdf

# ─────────────────────────────────────────────
#  Page config  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"], .stApp { font-family:'DM Sans',sans-serif; }
.stApp { background:#080810; color:#f0ece4; }
.block-container { padding-top:2rem !important; max-width:1100px !important; }

/* ── Hero ── */
.hero { text-align:center; padding:2.5rem 0 1.5rem; }
.hero-eyebrow { font-size:.75rem; letter-spacing:.25em; text-transform:uppercase;
    color:#c8a96e; font-weight:500; margin-bottom:.6rem; }
.hero-title { font-family:'Playfair Display',serif; font-size:clamp(2.8rem,6vw,5rem);
    font-weight:900; color:#f0ece4; line-height:1.0; letter-spacing:-2px; margin:0; }
.hero-title span { color:#c8a96e; font-style:italic; }
.hero-sub { font-size:1rem; color:#7a7060; font-weight:300; margin-top:.8rem;
    letter-spacing:.04em; }

/* ── Inputs ── */
.stTextInput>div>div>input, .stTextArea>div>div>textarea,
.stNumberInput>div>div>input, .stSelectbox>div>div {
    background:#10101a !important; border:1px solid #2a2a3a !important;
    color:#f0ece4 !important; border-radius:10px !important;
    font-family:'DM Sans',sans-serif !important; }
label, .stLabel { color:#6a6055 !important; font-size:.75rem !important;
    text-transform:uppercase !important; letter-spacing:.1em !important; font-weight:500 !important;}
.stMultiSelect>div>div { background:#10101a !important; border:1px solid #2a2a3a !important; border-radius:10px !important; }
.stMultiSelect span[data-baseweb="tag"] { background:#2a2218 !important; border:1px solid #c8a96e !important; color:#c8a96e !important; }

/* ── Submit button ── */
.stButton>button { background:linear-gradient(135deg,#c8a96e,#d4b97e) !important;
    color:#080810 !important; border:none !important; border-radius:12px !important;
    font-family:'DM Sans',sans-serif !important; font-weight:600 !important;
    font-size:1rem !important; padding:.7rem 2rem !important;
    width:100% !important; letter-spacing:.03em !important; transition:all .2s !important; }
.stButton>button:hover { transform:translateY(-2px) !important;
    box-shadow:0 8px 24px rgba(200,169,110,.25) !important; }

/* ── Download buttons ── */
.stDownloadButton>button { background:#10101a !important; color:#c8a96e !important;
    border:1px solid #c8a96e !important; border-radius:10px !important;
    font-family:'DM Sans',sans-serif !important; font-weight:500 !important;
    font-size:.9rem !important; padding:.5rem 1.4rem !important;
    transition:all .2s !important; }
.stDownloadButton>button:hover { background:#c8a96e !important; color:#080810 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background:#10101a; border-radius:12px;
    padding:4px; border:1px solid #1e1e2e; gap:2px; }
.stTabs [data-baseweb="tab"] { background:transparent !important; color:#6a6055 !important;
    border-radius:9px !important; font-size:.85rem !important; font-weight:500 !important;
    padding:.4rem 1.1rem !important; }
.stTabs [aria-selected="true"] { background:#1e1e2e !important; color:#c8a96e !important; }

/* ── Cards ── */
.card { background:#10101a; border:1px solid #1e1e2e; border-radius:14px;
    padding:1.3rem 1.5rem; margin-bottom:.8rem; }
.card-gold { border-color:#3a2e18; background:#0e0c08; }
.card-header { font-family:'Playfair Display',serif; font-size:1.1rem;
    color:#c8a96e; font-weight:700; margin-bottom:.7rem; }
.card-sub { font-size:.82rem; color:#6a6055; text-transform:uppercase;
    letter-spacing:.1em; font-weight:500; }

/* ── Agent tracker ── */
.agent-box { background:#0e0e18; border:1px solid #1e1e2e; border-radius:10px;
    padding:.8rem 1rem; text-align:center; transition:all .3s; }
.agent-box.active { border-color:#c8a96e; background:#130f05;
    box-shadow:0 0 20px rgba(200,169,110,.15); }
.agent-box.done { border-color:#2a5a2a; background:#080e08; }
.agent-icon { font-size:1.4rem; margin-bottom:.3rem; }
.agent-name { font-size:.7rem; font-weight:600; letter-spacing:.1em;
    text-transform:uppercase; color:#6a6055; }
.agent-status { font-size:.78rem; margin-top:.2rem; color:#f0ece4; min-height:1.1rem; }

/* ── Activity items ── */
.act-row { display:flex; gap:1rem; padding:.6rem 0;
    border-bottom:1px solid #161620; align-items:flex-start; }
.act-time { color:#6a6055; font-size:.78rem; min-width:65px; padding-top:2px;
    font-weight:500; flex-shrink:0; }
.act-content { flex:1; }
.act-name { font-size:.9rem; font-weight:500; color:#f0ece4; }
.act-desc { font-size:.83rem; color:#8a8070; margin-top:2px; line-height:1.5; }
.act-meta { display:flex; gap:.5rem; margin-top:4px; flex-wrap:wrap; }
.meta-chip { font-size:.72rem; padding:2px 8px; border-radius:999px;
    background:#1e1e2e; color:#c8a96e; border:1px solid #2a2a3a; }
.pro-tip { font-size:.78rem; color:#8a7040; font-style:italic;
    margin-top:4px; padding-left:.5rem; border-left:2px solid #3a2e18; }

/* ── Summary box ── */
.summary-box { background:linear-gradient(135deg,#0e0c08,#130f05);
    border:1px solid #3a2e18; border-radius:14px; padding:1.5rem 1.8rem; margin:1rem 0; }
.summary-text { font-family:'Playfair Display',serif; font-size:1.15rem;
    color:#e8d5a3; line-height:1.7; font-style:italic; }

/* ── Overview chips ── */
.chip-row { display:flex; flex-wrap:wrap; gap:.4rem; margin:.8rem 0; }
.ov-chip { font-size:.78rem; padding:.3rem .9rem; border-radius:999px;
    background:#1a1a2e; border:1px solid #2a2a4a; color:#9090c0; font-weight:500; }

/* ── Misc ── */
.section-title { font-family:'Playfair Display',serif; font-size:1.5rem;
    font-weight:700; color:#f0ece4; margin:1.5rem 0 .8rem;
    padding-bottom:.5rem; border-bottom:1px solid #3a2e18; }
.gold-text { color:#c8a96e; }
.dim-text { color:#6a6055; font-size:.85rem; }
.tip-bar { background:#130f05; border-left:3px solid #c8a96e;
    border-radius:0 8px 8px 0; padding:.6rem 1rem; margin:.5rem 0;
    font-size:.85rem; color:#b09060; }
.error-bar { background:#180808; border-left:3px solid #8b2222;
    border-radius:0 8px 8px 0; padding:.6rem 1rem;
    font-size:.82rem; color:#c07070; }
hr { border-color:#1e1e2e !important; }

/* ── Progress ── */
.stProgress>div>div { background:linear-gradient(90deg,#c8a96e,#d4b97e) !important; }
.stProgress { border-radius:999px !important; }

/* ── Expander ── */
details { background:#10101a !important; border:1px solid #1e1e2e !important;
    border-radius:12px !important; padding:.3rem .5rem !important; }
summary { color:#f0ece4 !important; font-size:.9rem !important;
    font-weight:500 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Hero
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-eyebrow">✦ Multi-Agent AI System ✦</div>
  <h1 class="hero-title">AI <span>Travel</span><br>Planner</h1>
  <p class="hero-sub">9 specialized agents · LangGraph orchestration · 100% local & free</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Sidebar — model selector
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    model_choice = st.selectbox(
        "Ollama Model",
        ["llama3.2", "llama3", "mistral", "phi3", "gemma2"],
        help="Make sure model is pulled: ollama pull <model>"
    )
    st.markdown("---")
    st.markdown("**Agent Pipeline**")
    agents_info = [
        ("🧭","Supervisor","Validates & orchestrates"),
        ("🔍","Researcher","Destination intelligence"),
        ("🌤","Weather","Climate & packing context"),
        ("🏨","Accommodation","Stay options by budget"),
        ("🎯","Activities","Day-by-day schedule"),
        ("🍜","Food","Restaurants & dishes"),
        ("💰","Budget","Cost breakdown"),
        ("🧳","Packing","Smart packing list"),
        ("📄","Composer","Final assembly"),
    ]
    for icon, name, desc in agents_info:
        st.markdown(f"**{icon} {name}** — {desc}")
    st.markdown("---")
    st.markdown("**Stack**")
    for tech in ["LangGraph","LangChain","Ollama (local)","Streamlit","ReportLab PDF"]:
        st.markdown(f"• {tech}")


# ─────────────────────────────────────────────
#  Input form
# ─────────────────────────────────────────────
st.markdown("---")
with st.form("trip_form", clear_on_submit=False):
    c1, c2, c3 = st.columns([1.2, 1, 1])

    with c1:
        destination = st.text_input("Destination", placeholder="e.g. Tokyo, Japan")
        interests = st.multiselect("Your interests", [
            "Culture & History","Food & Cuisine","Adventure & Outdoors",
            "Art & Museums","Shopping","Nightlife","Nature & Wildlife",
            "Photography","Relaxation & Spa","Architecture","Local Markets",
        ], default=["Culture & History","Food & Cuisine"])

    with c2:
        duration  = st.number_input("Duration (days)", min_value=1, max_value=21, value=5)
        travelers = st.number_input("Travelers", min_value=1, max_value=20, value=2)

    with c3:
        budget = st.selectbox("Budget", [
            "Budget ($500-1000)","Mid-range ($1000-3000)","Luxury ($3000+)"
        ])
        travel_style = st.selectbox("Travel style", [
            "Balanced","Packed (max activities)","Relaxed (slow travel)",
            "Off-the-beaten-path","Family-friendly",
        ])

    special = st.text_area(
        "Special requests (dietary, accessibility, preferences…)",
        placeholder="e.g. vegetarian, avoid tourist traps, include a day trip to countryside…",
        height=70,
    )

    submitted = st.form_submit_button("✈️  Generate My Itinerary")


# ─────────────────────────────────────────────
#  Main execution
# ─────────────────────────────────────────────
if submitted:
    if not destination.strip():
        st.error("Please enter a destination to continue.")
        st.stop()

    trip_input = {
        "destination":    destination.strip(),
        "duration":       int(duration),
        "budget":         budget,
        "travelers":      int(travelers),
        "interests":      interests if interests else ["General sightseeing"],
        "travel_style":   travel_style,
        "special_requests": special.strip() or "None",
    }

    st.markdown("---")
    st.markdown("### 🤖 Agents at work")

    agents_display = [
        ("🧭","Supervisor",     "Orchestrating mission…"),
        ("🔍","Researcher",     "Gathering destination intel…"),
        ("🌤","Weather",        "Analyzing climate data…"),
        ("🏨","Accommodation",  "Scouting best stays…"),
        ("🎯","Activities",     "Curating experiences…"),
        ("🍜","Food Guide",     "Discovering local cuisine…"),
        ("💰","Budget",         "Calculating costs…"),
        ("🧳","Packing",        "Building smart packing list…"),
        ("📄","Composer",       "Assembling final plan…"),
    ]

    # Build agent tracker grid (3 rows of 3)
    ph_list = []
    rows = [agents_display[i:i+3] for i in range(0,len(agents_display),3)]
    for row in rows:
        cols = st.columns(len(row))
        for ci, (icon, name, action) in enumerate(row):
            with cols[ci]:
                ph = st.empty()
                ph.markdown(f"""<div class="agent-box">
                    <div class="agent-icon">{icon}</div>
                    <div class="agent-name">{name}</div>
                    <div class="agent-status" style="color:#2a2a3a">waiting</div>
                </div>""", unsafe_allow_html=True)
                ph_list.append((ph, icon, name, action))

    prog  = st.progress(0)
    status_ph = st.empty()

    # Animate agents
    for idx, (ph, icon, name, action) in enumerate(ph_list):
        ph.markdown(f"""<div class="agent-box active">
            <div class="agent-icon">{icon}</div>
            <div class="agent-name">{name}</div>
            <div class="agent-status">{action}</div>
        </div>""", unsafe_allow_html=True)
        prog.progress((idx + 1) / len(ph_list))
        status_ph.markdown(f"*{icon} {name} is working…*")
        time.sleep(0.25)

    status_ph.markdown("*🔄 Running LangGraph pipeline — this takes 2-5 min on CPU…*")

    try:
        result = run_travel_planner(trip_input, model_name=model_choice)
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.info("Make sure Ollama is running (`ollama serve`) and model is pulled (`ollama pull llama3.2`)")
        st.stop()

    # Mark all done
    for ph, icon, name, _ in ph_list:
        ph.markdown(f"""<div class="agent-box done">
            <div class="agent-icon">{icon}</div>
            <div class="agent-name">{name}</div>
            <div class="agent-status" style="color:#5aaa5a">✓ done</div>
        </div>""", unsafe_allow_html=True)

    prog.progress(1.0)
    status_ph.markdown("**✅ All agents complete — your itinerary is ready!**")

    st.session_state["result"]    = result
    st.session_state["trip_input"] = trip_input

# ─────────────────────────────────────────────
#  Render results
# ─────────────────────────────────────────────
if "result" in st.session_state:
    result     = st.session_state["result"]
    trip_input = st.session_state["trip_input"]
    dest       = trip_input["destination"]
    dur        = trip_input["duration"]

    st.markdown("---")

    # Summary
    summary = result.get("summary","")
    if summary:
        st.markdown(f'<div class="summary-box"><p class="summary-text">"{summary}"</p></div>', unsafe_allow_html=True)

    # Overview chips
    ov = result.get("overview", {})
    chips = "".join([f'<span class="ov-chip">{k}: {v}</span>' for k, v in ov.items()])
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)

    # Show errors (non-blocking)
    errors = result.get("errors", [])
    if errors:
        with st.expander(f"⚠️ {len(errors)} agent warning(s) — fallback data used"):
            for e in errors:
                st.markdown(f'<div class="error-bar">{e}</div>', unsafe_allow_html=True)

    # ── Downloads ────────────────────────────────────────────────────────────
    dcol1, dcol2, dcol3 = st.columns([1,1,2])
    with dcol1:
        try:
            pdf_bytes = generate_pdf(result)
            st.download_button(
                "📄 Download PDF",
                data=pdf_bytes,
                file_name=f"{dest.replace(' ','_')}_itinerary.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.caption(f"PDF error: {e}")
    with dcol2:
        txt = _build_txt(result, trip_input)
        st.download_button(
            "📥 Download TXT",
            data=txt,
            file_name=f"{dest.replace(' ','_')}_itinerary.txt",
            mime="text/plain",
        )

    st.markdown("---")

    # ── 6 content tabs ───────────────────────────────────────────────────────
    tab_labels = ["📅 Itinerary","🌤 Weather","🏨 Stays","🍜 Food","💰 Budget","🧳 Packing"]
    tabs = st.tabs(tab_labels)

    # TAB 1 — Itinerary
    with tabs[0]:
        itinerary = result.get("itinerary", [])
        dest_info = result.get("destination_info","")

        if dest_info and not dest_info.startswith("__ERROR__"):
            with st.expander("📍 Destination Overview", expanded=False):
                st.markdown(dest_info)

        if not itinerary:
            st.info("No itinerary data generated.")
        else:
            for day in itinerary:
                day_n = day.get("day","?")
                title = day.get("title","")
                emoji = day.get("theme_emoji","🗺️")
                highlights = day.get("day_highlights","")
                transport  = day.get("transport_for_day","")
                est_cost   = day.get("estimated_daily_cost","")

                with st.expander(f"{emoji} Day {day_n} — {title}", expanded=(day_n==1)):
                    if highlights:
                        st.markdown(f'<div class="tip-bar">{highlights}</div>', unsafe_allow_html=True)

                    acts_html = ""
                    for act in day.get("activities",[]):
                        time_s = act.get("time","")
                        aname  = act.get("activity","")
                        desc   = act.get("description","")
                        cost   = act.get("cost","")
                        dur_s  = act.get("duration","")
                        tip    = act.get("pro_tip","")

                        chips_html = ""
                        if cost:  chips_html += f'<span class="meta-chip">💵 {cost}</span>'
                        if dur_s: chips_html += f'<span class="meta-chip">⏱ {dur_s}</span>'

                        acts_html += f"""
                        <div class="act-row">
                          <div class="act-time">{time_s}</div>
                          <div class="act-content">
                            <div class="act-name">{aname}</div>
                            <div class="act-desc">{desc}</div>
                            {f'<div class="act-meta">{chips_html}</div>' if chips_html else ''}
                            {f'<div class="pro-tip">💡 {tip}</div>' if tip else ''}
                          </div>
                        </div>"""

                    st.markdown(acts_html, unsafe_allow_html=True)

                    foot = []
                    if transport: foot.append(f"🚌 {transport}")
                    if est_cost:  foot.append(f"💵 Est. {est_cost}")
                    if foot:
                        st.markdown(f'<div class="dim-text" style="margin-top:.5rem">{" · ".join(foot)}</div>', unsafe_allow_html=True)

    # TAB 2 — Weather
    with tabs[1]:
        weather = result.get("weather", {})
        if not weather:
            st.info("No weather data available.")
        else:
            wc1, wc2 = st.columns(2)
            with wc1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">🌡️ Climate Overview</div>', unsafe_allow_html=True)
                st.markdown(weather.get("season_overview",""), unsafe_allow_html=False)
                if weather.get("temperature_range"):
                    st.markdown(f"**Temperature:** {weather['temperature_range']}")
                if weather.get("humidity"):
                    st.markdown(f"**Humidity:** {weather['humidity']}")
                if weather.get("rainfall"):
                    st.markdown(f"**Rainfall:** {weather['rainfall']}")
                st.markdown("</div>", unsafe_allow_html=True)

            with wc2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">📅 Best Time to Visit</div>', unsafe_allow_html=True)
                if weather.get("best_months"):
                    st.markdown("**Best:** " + " · ".join(weather["best_months"]))
                if weather.get("shoulder_months"):
                    st.markdown("**Shoulder:** " + " · ".join(weather["shoulder_months"]))
                if weather.get("avoid_if_possible"):
                    st.markdown("**Avoid:** " + " · ".join(weather["avoid_if_possible"]))
                if weather.get("weather_warning") and weather["weather_warning"] != "null":
                    st.markdown(f'<div class="error-bar">⚠️ {weather["weather_warning"]}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">👗 What to Wear</div>', unsafe_allow_html=True)
            if weather.get("clothing_advice"):
                st.markdown(weather["clothing_advice"])
            meta = []
            if weather.get("umbrella_needed"): meta.append("☂️ Bring an umbrella")
            if weather.get("sun_protection"):  meta.append("🕶️ Sun protection needed")
            if meta:
                st.markdown(" · ".join(meta))
            st.markdown("</div>", unsafe_allow_html=True)

    # TAB 3 — Stays
    with tabs[2]:
        accs = result.get("accommodations", [])
        if not accs:
            st.info("No accommodation suggestions available.")
        else:
            for acc in accs:
                st.markdown(f"""
                <div class="card card-gold">
                  <div class="card-header">🏨 {acc.get('name','')}
                    <span class="dim-text" style="font-size:.85rem;font-family:DM Sans"> · {acc.get('type','')} · {'⭐'*int(acc.get('stars',3))}</span>
                  </div>
                  <div style="color:#c8a96e;font-size:.9rem;margin-bottom:.5rem">
                    {acc.get('price_range','')} &nbsp;·&nbsp; 📍 {acc.get('neighborhood','')}
                  </div>
                  <p style="color:#9a9080;font-size:.9rem;line-height:1.6">{acc.get('description','')}</p>
                  <div style="display:flex;gap:.8rem;flex-wrap:wrap;margin-top:.5rem;font-size:.83rem">
                    <span>✅ {acc.get('pros','')}</span>
                    <span style="color:#6a6055">⚠️ {acc.get('cons','')}</span>
                  </div>
                  <div class="tip-bar" style="margin-top:.6rem">💡 Booking tip: {acc.get('booking_tip','Book directly with the hotel for best rate')}</div>
                </div>""", unsafe_allow_html=True)

    # TAB 4 — Food
    with tabs[3]:
        food = result.get("food", {})
        if not food:
            st.info("No food guide available.")
        else:
            intro = food.get("culinary_intro","")
            if intro:
                st.markdown(f'<div class="summary-box"><p class="summary-text">"{intro}"</p></div>', unsafe_allow_html=True)

            fc1, fc2 = st.columns([1,1])
            with fc1:
                st.markdown('<div class="section-title" style="font-size:1.1rem">🍽️ Must-Try Dishes</div>', unsafe_allow_html=True)
                for dish in food.get("must_try_dishes",[]):
                    st.markdown(f"""
                    <div class="card" style="padding:.9rem 1rem;margin-bottom:.5rem">
                      <div style="font-weight:600;color:#f0ece4">{dish.get('name','')}</div>
                      <div style="color:#8a8070;font-size:.85rem;margin:.3rem 0">{dish.get('description','')}</div>
                      <div style="font-size:.78rem;color:#c8a96e">📍 {dish.get('find_at','')} · {dish.get('avg_cost','')}</div>
                    </div>""", unsafe_allow_html=True)

            with fc2:
                st.markdown('<div class="section-title" style="font-size:1.1rem">🏪 Food Markets</div>', unsafe_allow_html=True)
                for m in food.get("food_markets",[]):
                    if isinstance(m, dict):
                        st.markdown(f"""<div class="card" style="padding:.9rem 1rem;margin-bottom:.5rem">
                          <div style="font-weight:600;color:#f0ece4">{m.get('name','')}</div>
                          <div style="color:#8a8070;font-size:.85rem">{m.get('specialty','')} · Best time: {m.get('best_time','')}</div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="tip-bar">{m}</div>', unsafe_allow_html=True)

                if food.get("drink_culture"):
                    st.markdown(f'<div class="tip-bar">🥂 {food["drink_culture"]}</div>', unsafe_allow_html=True)
                if food.get("food_etiquette"):
                    st.markdown(f'<div class="tip-bar">🙏 {food["food_etiquette"]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-title" style="font-size:1.1rem">🍴 Recommended Restaurants</div>', unsafe_allow_html=True)
            rest_cols = st.columns(2)
            for ri, r in enumerate(food.get("restaurants",[])):
                with rest_cols[ri % 2]:
                    st.markdown(f"""
                    <div class="card" style="padding:.9rem 1rem;margin-bottom:.5rem">
                      <div style="font-weight:600;color:#f0ece4">{r.get('name','')}</div>
                      <div style="color:#c8a96e;font-size:.78rem;margin:.2rem 0">{r.get('price','')} · {r.get('vibe','')} · {r.get('neighborhood','')}</div>
                      <div style="color:#8a8070;font-size:.83rem">{r.get('why_go','')}</div>
                      <div style="color:#6a6055;font-size:.78rem;margin-top:.3rem">Order: {r.get('signature_dish','')}</div>
                    </div>""", unsafe_allow_html=True)

    # TAB 5 — Budget
    with tabs[4]:
        budget = result.get("budget", {})
        if not budget:
            st.info("No budget data available.")
        else:
            bc1, bc2 = st.columns([1.3, 1])
            with bc1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">💵 Per-Person Breakdown</div>', unsafe_allow_html=True)
                ppb = budget.get("per_person_breakdown", {})
                for k, v in ppb.items():
                    bold = "total" in k.lower()
                    color = "#c8a96e" if bold else "#f0ece4"
                    weight = "600" if bold else "400"
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;padding:.4rem 0;
                         border-bottom:1px solid #161620;font-size:.88rem">
                      <span style="color:#8a8070">{k}</span>
                      <span style="color:{color};font-weight:{weight}">{v}</span>
                    </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with bc2:
                gt  = budget.get("total_for_group","")
                da  = budget.get("daily_budget_target","")
                tip = budget.get("atm_card_tips","")
                tp  = budget.get("tipping_culture","")
                sw  = budget.get("splurge_worthy","")
                cur = budget.get("currency_info",{})

                if cur:
                    st.markdown(f"""<div class="card">
                      <div class="card-header">💱 Currency</div>
                      <div style="color:#8a8070;font-size:.88rem">{cur.get('local_currency','')} ({cur.get('symbol','')})</div>
                      <div style="color:#8a8070;font-size:.85rem">{cur.get('usd_rate','')}</div>
                    </div>""", unsafe_allow_html=True)

                if gt:
                    st.markdown(f'<div class="tip-bar">👥 Group total: <b>{gt}</b></div>', unsafe_allow_html=True)
                if da:
                    st.markdown(f'<div class="tip-bar">📅 Daily target: <b>{da}</b></div>', unsafe_allow_html=True)
                if sw:
                    st.markdown(f'<div class="tip-bar">✨ Splurge on: {sw}</div>', unsafe_allow_html=True)
                if tip:
                    st.markdown(f'<div class="tip-bar">💳 {tip}</div>', unsafe_allow_html=True)
                if tp:
                    st.markdown(f'<div class="tip-bar">🤝 Tipping: {tp}</div>', unsafe_allow_html=True)

            hacks = budget.get("money_saving_hacks",[])
            if hacks:
                st.markdown('<div class="section-title" style="font-size:1.1rem">💡 Money-Saving Hacks</div>', unsafe_allow_html=True)
                hcols = st.columns(2)
                for hi, h in enumerate(hacks):
                    with hcols[hi%2]:
                        st.markdown(f'<div class="tip-bar">• {h}</div>', unsafe_allow_html=True)

    # TAB 6 — Packing
    with tabs[5]:
        packing = result.get("packing", {})
        if not packing:
            st.info("No packing list available.")
        else:
            phil = packing.get("packing_philosophy","")
            bag  = packing.get("bag_recommendation","")
            if phil:
                st.markdown(f'<div class="summary-box"><p class="summary-text">"{phil}"</p></div>', unsafe_allow_html=True)
            if bag:
                st.markdown(f'<div class="tip-bar">👜 Recommended bag: {bag}</div>', unsafe_allow_html=True)

            pcols = st.columns(2)
            pack_sections = [
                ("✈️ Essentials",     packing.get("essentials",[])),
                ("💊 Health & Safety",packing.get("health_safety",[])),
                ("🔌 Electronics",    packing.get("electronics",[])),
                ("📄 Documents",      packing.get("documents_money",[])),
                ("🎒 Activity Gear",  packing.get("activity_gear",[])),
                ("🛍️ Buy There",      packing.get("buy_there",[])),
            ]
            for pi, (sec, items) in enumerate(pack_sections):
                with pcols[pi%2]:
                    if items:
                        items_html = "".join([f"<li style='color:#9a9080;font-size:.87rem;padding:.2rem 0'>{i}</li>" for i in items])
                        st.markdown(f"""<div class="card" style="margin-bottom:.6rem">
                          <div class="card-sub" style="margin-bottom:.5rem">{sec}</div>
                          <ul style="margin:0;padding-left:1.2rem">{items_html}</ul>
                        </div>""", unsafe_allow_html=True)

            clothing = packing.get("clothing",{})
            if clothing and isinstance(clothing, dict):
                st.markdown('<div class="section-title" style="font-size:1.1rem">👗 Clothing Breakdown</div>', unsafe_allow_html=True)
                cloth_cols = st.columns(3)
                cloth_items = list(clothing.items())
                for ci, (cat, items) in enumerate(cloth_items):
                    with cloth_cols[ci%3]:
                        if items:
                            items_html = "".join([f"<li style='color:#9a9080;font-size:.85rem;padding:.15rem 0'>{i}</li>" for i in items])
                            st.markdown(f"""<div class="card" style="margin-bottom:.5rem">
                              <div class="card-sub">{cat}</div>
                              <ul style="margin:.3rem 0;padding-left:1.2rem">{items_html}</ul>
                            </div>""", unsafe_allow_html=True)

            dont = packing.get("do_not_pack",[])
            if dont:
                st.markdown('<div class="section-title" style="font-size:1.1rem">🚫 Leave at Home</div>', unsafe_allow_html=True)
                st.markdown('<div class="card">' + " · ".join([f'<span style="color:#6a6055">{x}</span>' for x in dont]) + '</div>', unsafe_allow_html=True)

            wt = packing.get("weight_tip","")
            if wt:
                st.markdown(f'<div class="tip-bar" style="margin-top:.5rem">⚖️ {wt}</div>', unsafe_allow_html=True)

    # Agent log
    with st.expander("🔬 Agent execution log", expanded=False):
        for msg in result.get("agent_log",[]):
            st.markdown(f"`{msg}`")


# ─────────────────────────────────────────────
#  Helpers (defined at module level — no bug)
# ─────────────────────────────────────────────

def _build_txt(result: dict, trip_input: dict) -> str:
    dest = trip_input["destination"]
    dur  = trip_input["duration"]
    lines = [
        "="*65,
        f"  AI TRAVEL PLANNER — {dest.upper()}",
        f"  {dur} Days · {trip_input['budget']} · {trip_input['travelers']} Traveler(s)",
        "="*65, "",
    ]
    if result.get("summary"):
        lines += ["TRIP OVERVIEW", "-"*40, result["summary"], ""]

    lines += ["DAY-BY-DAY ITINERARY", "-"*40]
    for day in result.get("itinerary",[]):
        lines.append(f"\nDay {day.get('day')} — {day.get('title','')} {day.get('theme_emoji','')}")
        for act in day.get("activities",[]):
            lines.append(f"  {act.get('time',''):12}  {act.get('activity','')} — {act.get('description','')}")
            if act.get("pro_tip"):
                lines.append(f"  {'':14}  💡 {act['pro_tip']}")
        if day.get("estimated_daily_cost"):
            lines.append(f"  Est. cost: {day['estimated_daily_cost']}")

    lines += ["","ACCOMMODATION", "-"*40]
    for acc in result.get("accommodations",[]):
        lines.append(f"\n{acc.get('name','')} ({acc.get('type','')} · {acc.get('price_range','')})")
        lines.append(f"  📍 {acc.get('neighborhood','')}  |  {acc.get('description','')}")

    food = result.get("food",{})
    if food:
        lines += ["","FOOD GUIDE", "-"*40]
        for d in food.get("must_try_dishes",[]):
            lines.append(f"• {d.get('name','')} — {d.get('description','')}")
        for r in food.get("restaurants",[]):
            lines.append(f"• {r.get('name','')} ({r.get('price','')}) — Order: {r.get('signature_dish','')}")

    budget = result.get("budget",{})
    if budget:
        lines += ["","BUDGET BREAKDOWN", "-"*40]
        for k,v in budget.get("per_person_breakdown",{}).items():
            lines.append(f"  {k:<35} {v}")
        if budget.get("total_for_group"):
            lines.append(f"\n  TOTAL: {budget['total_for_group']}")

    lines += ["", "="*65, "Generated by AI Travel Planner · LangGraph + Ollama", "="*65]
    return "\n".join(lines)
