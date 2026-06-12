"""
pdf_export.py — Generate beautiful PDF itinerary from travel plan data
Uses only reportlab (no external services needed)
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)


# ── Color palette ─────────────────────────────────────────────────────────────
GOLD       = colors.HexColor("#C8A96E")
DARK       = colors.HexColor("#1a1a2e")
DARK2      = colors.HexColor("#16213e")
MID_GRAY   = colors.HexColor("#4a4a5a")
LIGHT_GRAY = colors.HexColor("#f5f5f0")
WHITE      = colors.white
ACCENT     = colors.HexColor("#e8d5a3")


def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=32, textColor=WHITE, spaceAfter=6,
        fontName="Helvetica-Bold", alignment=TA_CENTER,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=13, textColor=ACCENT, spaceAfter=4,
        fontName="Helvetica", alignment=TA_CENTER,
    )
    styles["section_header"] = ParagraphStyle(
        "section_header", parent=base["Heading1"],
        fontSize=16, textColor=DARK, spaceAfter=8, spaceBefore=14,
        fontName="Helvetica-Bold", borderPad=4,
    )
    styles["day_header"] = ParagraphStyle(
        "day_header", parent=base["Heading2"],
        fontSize=13, textColor=DARK2, spaceAfter=6, spaceBefore=10,
        fontName="Helvetica-Bold",
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, textColor=MID_GRAY, spaceAfter=4,
        fontName="Helvetica", leading=15,
    )
    styles["body_bold"] = ParagraphStyle(
        "body_bold", parent=base["Normal"],
        fontSize=10, textColor=DARK, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    styles["tip"] = ParagraphStyle(
        "tip", parent=base["Normal"],
        fontSize=9, textColor=colors.HexColor("#7a6a40"),
        fontName="Helvetica-Oblique", spaceAfter=6, leftIndent=10,
    )
    styles["label"] = ParagraphStyle(
        "label", parent=base["Normal"],
        fontSize=8, textColor=GOLD, fontName="Helvetica-Bold",
        spaceAfter=2, spaceBefore=6,
    )
    styles["footer"] = ParagraphStyle(
        "footer", parent=base["Normal"],
        fontSize=8, textColor=colors.HexColor("#aaaaaa"),
        fontName="Helvetica", alignment=TA_CENTER,
    )

    return styles


def _chip_table(items: list, styles) -> Table:
    """Render a row of chips/tags."""
    if not items:
        return None
    data = [[Paragraph(str(i), ParagraphStyle(
        "chip", fontSize=8, textColor=DARK2,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )) for i in items]]
    t = Table(data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ACCENT),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 0.5, GOLD),
    ]))
    return t


def _section_rule(story, styles, title: str):
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=4))
    story.append(Paragraph(title, styles["section_header"]))


def _two_col_table(rows: list, styles) -> Table:
    """Render a two-column key/value table."""
    data = [[
        Paragraph(str(k), styles["label"]),
        Paragraph(str(v), styles["body"])
    ] for k, v in rows]
    t = Table(data, colWidths=[55*mm, 115*mm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LINEBELOW",     (0,0), (-1,-1), 0.3, colors.HexColor("#e0ddd5")),
    ]))
    return t


def generate_pdf(result: dict) -> bytes:
    """Generate full PDF and return bytes."""
    buf = io.BytesIO()
    overview = result.get("overview", {})
    destination = overview.get("Destination", "Your Destination")
    duration    = overview.get("Duration", "")
    travelers   = overview.get("Travelers", "")
    budget      = overview.get("Budget", "")

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )

    styles = build_styles()
    story  = []

    # ── Cover block ──────────────────────────────────────────────────────────
    cover_data = [[
        Paragraph("✈  AI TRAVEL PLANNER", styles["cover_sub"]),
        Paragraph(destination.upper(), styles["cover_title"]),
        Paragraph(f"{duration}  ·  {travelers} traveler(s)  ·  {budget}", styles["cover_sub"]),
        Spacer(1, 4*mm),
        Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')}", ParagraphStyle(
            "gen", fontSize=9, textColor=colors.HexColor("#aaaacc"),
            fontName="Helvetica", alignment=TA_CENTER
        )),
    ]]
    cover = Table(cover_data, colWidths=[170*mm])
    cover.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("ROUNDEDCORNERS",[8]),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(cover)
    story.append(Spacer(1, 6*mm))

    # ── Trip summary ─────────────────────────────────────────────────────────
    summary = result.get("summary", "")
    if summary:
        _section_rule(story, styles, "Trip Overview")
        story.append(Paragraph(summary, styles["body"]))

    # Overview chips
    ov = result.get("overview", {})
    chip_items = [f"{k}: {v}" for k, v in ov.items()]
    if chip_items:
        story.append(Spacer(1, 3*mm))
        t = _chip_table(chip_items, styles)
        if t:
            story.append(t)

    # ── Weather ──────────────────────────────────────────────────────────────
    weather = result.get("weather", {})
    if weather:
        _section_rule(story, styles, "🌤  Weather & Climate")
        rows = []
        if weather.get("season_overview"):
            rows.append(("Overview", weather["season_overview"]))
        if weather.get("temperature_range"):
            rows.append(("Temperature", weather["temperature_range"]))
        if weather.get("best_months"):
            rows.append(("Best months", ", ".join(weather["best_months"])))
        if weather.get("clothing_advice"):
            rows.append(("What to wear", weather["clothing_advice"]))
        if rows:
            story.append(_two_col_table(rows, styles))

    # ── Destination info ─────────────────────────────────────────────────────
    dest_info = result.get("destination_info", "")
    if dest_info and not dest_info.startswith("__ERROR__"):
        _section_rule(story, styles, "📍  Destination Guide")
        for line in dest_info.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 2*mm))
            elif line[0].isdigit() and "." in line[:3]:
                story.append(Paragraph(line, styles["body_bold"]))
            else:
                story.append(Paragraph(line, styles["body"]))

    # ── Day-by-day itinerary ─────────────────────────────────────────────────
    itinerary = result.get("itinerary", [])
    if itinerary:
        _section_rule(story, styles, "📅  Day-by-Day Itinerary")
        for day in itinerary:
            day_num   = day.get("day", "?")
            day_title = day.get("title", f"Day {day_num}")
            emoji     = day.get("theme_emoji", "🗺️")
            block = []
            block.append(Paragraph(f"{emoji}  Day {day_num} — {day_title}", styles["day_header"]))

            for act in day.get("activities", []):
                time_str  = act.get("time", "")
                act_name  = act.get("activity", "")
                desc      = act.get("description", "")
                cost      = act.get("cost", "")
                duration_ = act.get("duration", "")
                tip       = act.get("pro_tip", "")
                line = f"<b>{time_str}</b>  {act_name} — {desc}"
                if cost or duration_:
                    line += f"  <font color='#c8a96e' size='8'>[{cost} · {duration_}]</font>"
                block.append(Paragraph(line, styles["body"]))
                if tip:
                    block.append(Paragraph(f"💡 {tip}", styles["tip"]))

            daily_cost = day.get("estimated_daily_cost","")
            transport  = day.get("transport_for_day","")
            if daily_cost or transport:
                meta = []
                if transport: meta.append(f"🚌 {transport}")
                if daily_cost: meta.append(f"💵 Est. {daily_cost}")
                block.append(Paragraph("  ·  ".join(meta), styles["tip"]))

            block.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0ddd5"), spaceAfter=4))
            story.append(KeepTogether(block))

    # ── Accommodation ────────────────────────────────────────────────────────
    accommodations = result.get("accommodations", [])
    if accommodations:
        _section_rule(story, styles, "🏨  Where to Stay")
        for acc in accommodations:
            name      = acc.get("name","")
            atype     = acc.get("type","")
            price     = acc.get("price_range","")
            hood      = acc.get("neighborhood","")
            desc      = acc.get("description","")
            pros      = acc.get("pros","")
            cons      = acc.get("cons","")
            best_for  = acc.get("best_for","")
            tip       = acc.get("booking_tip","")
            block = []
            block.append(Paragraph(f"<b>{name}</b>  <font color='#c8a96e'>{atype} · {price}</font>  <font color='#8a8070'>{hood}</font>", styles["body"]))
            if desc:
                block.append(Paragraph(desc, styles["body"]))
            info = []
            if pros:    info.append(f"✅ {pros}")
            if cons:    info.append(f"⚠️ {cons}")
            if best_for: info.append(f"👤 Best for: {best_for}")
            if tip:     info.append(f"💡 Booking tip: {tip}")
            for i in info:
                block.append(Paragraph(i, styles["tip"]))
            block.append(Spacer(1, 3*mm))
            story.append(KeepTogether(block))

    # ── Food guide ───────────────────────────────────────────────────────────
    food = result.get("food", {})
    if food:
        _section_rule(story, styles, "🍜  Food & Dining Guide")
        intro = food.get("culinary_intro","")
        if intro:
            story.append(Paragraph(intro, styles["body"]))

        dishes = food.get("must_try_dishes", [])
        if dishes:
            story.append(Paragraph("Must-Try Dishes", styles["label"]))
            for dish in dishes:
                story.append(Paragraph(f"<b>{dish.get('name','')}</b> — {dish.get('description','')}  <font color='#c8a96e'>({dish.get('avg_cost','')})</font>", styles["body"]))
                if dish.get("find_at"):
                    story.append(Paragraph(f"📍 {dish['find_at']}", styles["tip"]))

        restaurants = food.get("restaurants", [])
        if restaurants:
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph("Recommended Restaurants", styles["label"]))
            for r in restaurants:
                story.append(Paragraph(
                    f"<b>{r.get('name','')}</b>  <font color='#c8a96e'>{r.get('price','')} · {r.get('vibe','')}</font>  <font color='#8a8070'>{r.get('neighborhood','')}</font>",
                    styles["body"]
                ))
                story.append(Paragraph(f"Order: {r.get('signature_dish','')}  ·  {r.get('why_go','')}", styles["tip"]))

        food_tip = food.get("food_etiquette","")
        if food_tip:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(f"🍽️  Etiquette: {food_tip}", styles["tip"]))

    # ── Budget ───────────────────────────────────────────────────────────────
    budget = result.get("budget", {})
    if budget:
        _section_rule(story, styles, "💰  Budget Breakdown")
        ppb = budget.get("per_person_breakdown", {})
        if ppb:
            rows = [(k, v) for k, v in ppb.items()]
            story.append(_two_col_table(rows, styles))

        totals = []
        if budget.get("total_for_group"):
            totals.append(("Group total", budget["total_for_group"]))
        if budget.get("daily_budget_target"):
            totals.append(("Daily target", budget["daily_budget_target"]))
        if totals:
            story.append(Spacer(1, 2*mm))
            story.append(_two_col_table(totals, styles))

        hacks = budget.get("money_saving_hacks", [])
        if hacks:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph("Money-Saving Tips", styles["label"]))
            for h in hacks:
                story.append(Paragraph(f"• {h}", styles["body"]))

        tipping = budget.get("tipping_culture","")
        if tipping:
            story.append(Paragraph(f"🤝  Tipping: {tipping}", styles["tip"]))

    # ── Packing list ─────────────────────────────────────────────────────────
    packing = result.get("packing", {})
    if packing:
        _section_rule(story, styles, "🧳  Smart Packing List")
        bag = packing.get("bag_recommendation","")
        phil = packing.get("packing_philosophy","")
        if phil:
            story.append(Paragraph(phil, styles["body"]))
        if bag:
            story.append(Paragraph(f"👜 Recommended bag: {bag}", styles["tip"]))

        sections = [
            ("Essentials",       packing.get("essentials",[])),
            ("Health & Safety",  packing.get("health_safety",[])),
            ("Electronics",      packing.get("electronics",[])),
            ("Documents/Money",  packing.get("documents_money",[])),
            ("Activity Gear",    packing.get("activity_gear",[])),
            ("Leave at Home",    packing.get("do_not_pack",[])),
            ("Buy There",        packing.get("buy_there",[])),
        ]
        for sec_title, items in sections:
            if items:
                story.append(Paragraph(sec_title, styles["label"]))
                clothing_val = packing.get("clothing", {})
                cols = [items[i:i+2] for i in range(0, len(items), 2)]
                for row in cols:
                    row_data = [Paragraph(f"• {x}", styles["body"]) for x in row]
                    while len(row_data) < 2:
                        row_data.append(Paragraph("", styles["body"]))
                    t = Table([row_data], colWidths=[85*mm, 85*mm])
                    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"), ("TOPPADDING",(0,0),(-1,-1),1), ("BOTTOMPADDING",(0,0),(-1,-1),1)]))
                    story.append(t)

        clothing = packing.get("clothing", {})
        if clothing and isinstance(clothing, dict):
            story.append(Paragraph("Clothing Details", styles["label"]))
            for cat, items in clothing.items():
                if items:
                    story.append(Paragraph(f"{cat.title()}: {', '.join(items)}", styles["body"]))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f"Generated by AI Travel Planner  ·  LangGraph + Ollama  ·  {datetime.now().strftime('%B %Y')}",
        styles["footer"]
    ))

    doc.build(story)
    return buf.getvalue()
