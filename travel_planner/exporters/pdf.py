"""
pdf.py — ReportLab renderer for the travel plan.

Two details that matter and are easy to get wrong:

* **Escaping.** ReportLab ``Paragraph`` parses a mini-HTML dialect, so raw model
  output containing ``<``, ``>`` or ``&`` corrupts the document. Everything is
  escaped through :func:`_safe` before it reaches a paragraph.
* **Fonts.** The built-in Type 1 fonts have no emoji glyphs, so emoji render as
  black boxes. They are stripped for PDF output only.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from travel_planner.exporters.documents import _get

# ── Palette ──────────────────────────────────────────────────────────────────
GOLD = colors.HexColor("#C8A96E")
DARK = colors.HexColor("#1A1A2E")
DARK2 = colors.HexColor("#16213E")
MID_GRAY = colors.HexColor("#4A4A5A")
HAIRLINE = colors.HexColor("#E0DDD5")
ACCENT = colors.HexColor("#E8D5A3")

_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff\u2b00-\u2bff\ufe0f]"
)


def _safe(value: Any) -> str:
    """Escape mini-HTML metacharacters and drop glyphs the base fonts lack."""
    text = _EMOJI.sub("", str(value if value is not None else ""))
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return " ".join(text.split())


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontSize=30, textColor=colors.white,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"], fontSize=12, textColor=ACCENT,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4,
        ),
        "section_header": ParagraphStyle(
            "section_header", parent=base["Heading1"], fontSize=15, textColor=DARK,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=8,
        ),
        "day_header": ParagraphStyle(
            "day_header", parent=base["Heading2"], fontSize=12.5, textColor=DARK2,
            fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=9.5, textColor=MID_GRAY,
            fontName="Helvetica", leading=14.5, spaceAfter=4,
        ),
        "tip": ParagraphStyle(
            "tip", parent=base["Normal"], fontSize=8.5,
            textColor=colors.HexColor("#7A6A40"), fontName="Helvetica-Oblique",
            leftIndent=10, spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "label", parent=base["Normal"], fontSize=8, textColor=GOLD,
            fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontSize=8,
            textColor=colors.HexColor("#AAAAAA"), fontName="Helvetica",
            alignment=TA_CENTER,
        ),
    }


def _rule(story: list[Any], styles: dict[str, ParagraphStyle], title: str) -> None:
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=1.4, color=GOLD, spaceAfter=4))
    story.append(Paragraph(_safe(title), styles["section_header"]))


def _kv_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [Paragraph(_safe(key), styles["label"]), Paragraph(_safe(value), styles["body"])]
        for key, value in rows
    ]
    table = Table(data, colWidths=[52 * mm, 118 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, HAIRLINE),
            ]
        )
    )
    return table


def _bullets(story: list[Any], styles: dict[str, ParagraphStyle], items: list[str]) -> None:
    for item in items:
        story.append(Paragraph(f"&bull;&nbsp;{_safe(item)}", styles["body"]))


def generate_pdf(plan: dict[str, Any]) -> bytes:
    """Render ``plan`` to an A4 PDF and return the raw bytes."""
    buffer = io.BytesIO()
    styles = build_styles()
    overview = plan.get("overview") or {}
    destination = overview.get("Destination", "Your Destination")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{destination} Travel Plan",
        author="AI Travel Planner",
    )
    story: list[Any] = []

    # ── Cover ────────────────────────────────────────────────────────────
    subtitle = "  ·  ".join(
        f"{key}: {value}" for key, value in overview.items() if key != "Destination"
    )
    cover = Table(
        [
            [
                Paragraph("AI TRAVEL PLANNER", styles["cover_sub"]),
                Paragraph(_safe(destination).upper(), styles["cover_title"]),
                Paragraph(_safe(subtitle), styles["cover_sub"]),
                Spacer(1, 3 * mm),
                Paragraph(
                    f"Generated {datetime.now().strftime('%d %B %Y')}", styles["cover_sub"]
                ),
            ]
        ],
        colWidths=[170 * mm],
    )
    cover.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story += [cover, Spacer(1, 6 * mm)]

    if plan.get("summary"):
        story.append(Paragraph(_safe(plan["summary"]), styles["body"]))

    sources = plan.get("live_sources") or []
    if sources:
        story.append(
            Paragraph(f"Grounded by live data from: {_safe(', '.join(sources))}", styles["tip"])
        )

    # ── Destination brief ────────────────────────────────────────────────
    brief = plan.get("destination") or {}
    if brief:
        _rule(story, styles, "Destination Brief")
        if _get(brief, "essence"):
            story.append(Paragraph(_safe(_get(brief, "essence")), styles["body"]))
        for label, key in (
            ("Best neighbourhoods", "best_neighborhoods"),
            ("Iconic attractions", "iconic_attractions"),
            ("Culture & customs", "culture_customs"),
            ("Safety notes", "safety_notes"),
            ("Useful phrases", "language_phrases"),
        ):
            items = _get(brief, key, []) or []
            if items:
                story.append(Paragraph(label, styles["label"]))
                _bullets(story, styles, items)
        rows = [
            (label, _get(brief, key, ""))
            for label, key in (("Getting around", "getting_around"), ("Ideal timing", "ideal_timing"))
            if _get(brief, key, "")
        ]
        if rows:
            story.append(_kv_table(rows, styles))

    # ── Weather ──────────────────────────────────────────────────────────
    weather = plan.get("weather") or {}
    if weather:
        _rule(story, styles, "Weather & Climate")
        rows = [
            (label, value)
            for label, value in (
                ("Overview", _get(weather, "season_overview", "")),
                ("Temperature", _get(weather, "temperature_range", "")),
                ("Humidity", _get(weather, "humidity", "")),
                ("Rainfall", _get(weather, "rainfall", "")),
                ("Best months", ", ".join(_get(weather, "best_months", []) or [])),
                ("Avoid", ", ".join(_get(weather, "avoid_if_possible", []) or [])),
                ("What to wear", _get(weather, "clothing_advice", "")),
            )
            if value
        ]
        if rows:
            story.append(_kv_table(rows, styles))
        if _get(weather, "weather_warning"):
            story.append(
                Paragraph(f"Warning: {_safe(_get(weather, 'weather_warning'))}", styles["tip"])
            )

    # ── Itinerary ────────────────────────────────────────────────────────
    itinerary = plan.get("itinerary") or []
    if itinerary:
        story.append(PageBreak())
        _rule(story, styles, "Day-by-Day Itinerary")
        for day in itinerary:
            block: list[Any] = [
                Paragraph(
                    f"Day {_get(day, 'day', '?')} — {_safe(_get(day, 'title', ''))}",
                    styles["day_header"],
                )
            ]
            if _get(day, "day_highlights"):
                block.append(Paragraph(_safe(_get(day, "day_highlights")), styles["tip"]))
            for activity in _get(day, "activities", []) or []:
                meta = " · ".join(
                    part
                    for part in (_get(activity, "cost", ""), _get(activity, "duration", ""))
                    if part
                )
                line = (
                    f"<b>{_safe(_get(activity, 'time', ''))}</b>&nbsp;&nbsp;"
                    f"{_safe(_get(activity, 'activity', ''))} — "
                    f"{_safe(_get(activity, 'description', ''))}"
                )
                if meta:
                    line += f"  <font color='#C8A96E' size='8'>[{_safe(meta)}]</font>"
                block.append(Paragraph(line, styles["body"]))
                if _get(activity, "pro_tip"):
                    block.append(
                        Paragraph(f"Tip: {_safe(_get(activity, 'pro_tip'))}", styles["tip"])
                    )
            footer_bits = [
                part
                for part in (
                    _get(day, "transport_for_day", ""),
                    f"Estimated {_get(day, 'estimated_daily_cost', '')}"
                    if _get(day, "estimated_daily_cost")
                    else "",
                    f"~{_get(day, 'walking_distance_km', 0)} km on foot"
                    if _get(day, "walking_distance_km")
                    else "",
                )
                if part
            ]
            if footer_bits:
                block.append(Paragraph(_safe("  ·  ".join(footer_bits)), styles["tip"]))
            block.append(HRFlowable(width="100%", thickness=0.5, color=HAIRLINE, spaceAfter=4))
            story.append(KeepTogether(block))

    # ── Accommodation ────────────────────────────────────────────────────
    stays = plan.get("accommodations") or []
    if stays:
        _rule(story, styles, "Where to Stay")
    for stay in stays:
        block = [
            Paragraph(
                f"<b>{_safe(_get(stay, 'name', ''))}</b>  "
                f"<font color='#C8A96E'>{_safe(_get(stay, 'type', ''))} · "
                f"{_safe(_get(stay, 'price_range', ''))}</font>  "
                f"<font color='#8A8070'>{_safe(_get(stay, 'neighborhood', ''))}</font>",
                styles["body"],
            ),
            Paragraph(_safe(_get(stay, "description", "")), styles["body"]),
        ]
        for prefix, key in (
            ("Pro", "pros"),
            ("Con", "cons"),
            ("Best for", "best_for"),
            ("Booking tip", "booking_tip"),
        ):
            if _get(stay, key):
                block.append(Paragraph(f"{prefix}: {_safe(_get(stay, key))}", styles["tip"]))
        block.append(Spacer(1, 3 * mm))
        story.append(KeepTogether(block))

    # ── Food ─────────────────────────────────────────────────────────────
    food = plan.get("food") or {}
    if food:
        _rule(story, styles, "Food & Dining")
        if _get(food, "culinary_intro"):
            story.append(Paragraph(_safe(_get(food, "culinary_intro")), styles["body"]))
        dishes = _get(food, "must_try_dishes", []) or []
        if dishes:
            story.append(Paragraph("Must-try dishes", styles["label"]))
            for dish in dishes:
                story.append(
                    Paragraph(
                        f"<b>{_safe(_get(dish, 'name', ''))}</b> — "
                        f"{_safe(_get(dish, 'description', ''))} "
                        f"<font color='#C8A96E'>({_safe(_get(dish, 'avg_cost', ''))})</font>",
                        styles["body"],
                    )
                )
                if _get(dish, "find_at"):
                    story.append(
                        Paragraph(f"Find it at {_safe(_get(dish, 'find_at'))}", styles["tip"])
                    )
        restaurants = _get(food, "restaurants", []) or []
        if restaurants:
            story.append(Paragraph("Recommended restaurants", styles["label"]))
            for restaurant in restaurants:
                story.append(
                    Paragraph(
                        f"<b>{_safe(_get(restaurant, 'name', ''))}</b>  "
                        f"<font color='#C8A96E'>{_safe(_get(restaurant, 'price', ''))} · "
                        f"{_safe(_get(restaurant, 'vibe', ''))}</font>  "
                        f"<font color='#8A8070'>{_safe(_get(restaurant, 'neighborhood', ''))}</font>",
                        styles["body"],
                    )
                )
                story.append(
                    Paragraph(
                        f"Order the {_safe(_get(restaurant, 'signature_dish', ''))} — "
                        f"{_safe(_get(restaurant, 'why_go', ''))}",
                        styles["tip"],
                    )
                )
        for label, key in (
            ("Drinks", "drink_culture"),
            ("Etiquette", "food_etiquette"),
            ("Dietary advice", "dietary_advice"),
        ):
            if _get(food, key):
                story.append(Paragraph(f"{label}: {_safe(_get(food, key))}", styles["tip"]))

    # ── Budget ───────────────────────────────────────────────────────────
    budget = plan.get("budget") or {}
    if budget:
        _rule(story, styles, "Budget")
        breakdown = _get(budget, "per_person_breakdown", {}) or {}
        if breakdown:
            story.append(
                _kv_table(
                    [(key.replace("_", " ").title(), value) for key, value in breakdown.items()],
                    styles,
                )
            )
        currency = _get(budget, "currency_info", {}) or {}
        totals = [
            (label, value)
            for label, value in (
                ("Group total", _get(budget, "total_for_group", "")),
                ("Daily target", _get(budget, "daily_budget_target", "")),
                ("Currency", _get(currency, "usd_rate", "")),
            )
            if value
        ]
        if totals:
            story += [Spacer(1, 2 * mm), _kv_table(totals, styles)]
        hacks = _get(budget, "money_saving_hacks", []) or []
        if hacks:
            story.append(Paragraph("Money-saving tips", styles["label"]))
            _bullets(story, styles, hacks)
        if _get(budget, "tipping_culture"):
            story.append(
                Paragraph(f"Tipping: {_safe(_get(budget, 'tipping_culture'))}", styles["tip"])
            )

    # ── Packing ──────────────────────────────────────────────────────────
    packing = plan.get("packing") or {}
    if packing:
        story.append(PageBreak())
        _rule(story, styles, "Packing Checklist")
        if _get(packing, "packing_philosophy"):
            story.append(Paragraph(_safe(_get(packing, "packing_philosophy")), styles["body"]))
        if _get(packing, "bag_recommendation"):
            story.append(
                Paragraph(f"Bag: {_safe(_get(packing, 'bag_recommendation'))}", styles["tip"])
            )
        for label, key in (
            ("Essentials", "essentials"),
            ("Documents & money", "documents_money"),
            ("Toiletries", "toiletries"),
            ("Health & safety", "health_safety"),
            ("Electronics", "electronics"),
            ("Activity gear", "activity_gear"),
            ("Leave at home", "do_not_pack"),
            ("Buy on arrival", "buy_there"),
        ):
            items = _get(packing, key, []) or []
            if items:
                story.append(Paragraph(label, styles["label"]))
                story.append(
                    _checklist_table([str(item) for item in items], styles)
                )
        clothing = _get(packing, "clothing", {}) or {}
        if isinstance(clothing, dict) and any(clothing.values()):
            story.append(Paragraph("Clothing", styles["label"]))
            for category, items in clothing.items():
                if items:
                    story.append(
                        Paragraph(
                            f"{_safe(category.title())}: {_safe(', '.join(items))}",
                            styles["body"],
                        )
                    )

    # ── Review ───────────────────────────────────────────────────────────
    review = plan.get("review") or {}
    if review:
        _rule(story, styles, "Plan Review")
        story.append(
            Paragraph(
                f"<b>Confidence score: {_get(review, 'overall_score', '?')}/100</b>",
                styles["body"],
            )
        )
        for label, key in (
            ("Pacing", "pacing_verdict"),
            ("Budget realism", "budget_realism"),
        ):
            if _get(review, key):
                story.append(Paragraph(f"{label}: {_safe(_get(review, key))}", styles["body"]))
        for label, key in (("Risks to manage", "risks"), ("Recommended fixes", "fixes")):
            items = _get(review, key, []) or []
            if items:
                story.append(Paragraph(label, styles["label"]))
                _bullets(story, styles, items)

    # ── Footer ───────────────────────────────────────────────────────────
    story += [
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=1, color=GOLD),
        Spacer(1, 3 * mm),
        Paragraph(
            "Generated by AI Travel Planner  ·  LangGraph multi-agent system  ·  "
            f"{datetime.now().strftime('%B %Y')}",
            styles["footer"],
        ),
    ]

    doc.build(story)
    return buffer.getvalue()


def _checklist_table(items: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    """Two-column tickable checklist."""
    rows = []
    for index in range(0, len(items), 2):
        pair = items[index : index + 2]
        cells = [Paragraph(f"[ ]&nbsp;{_safe(item)}", styles["body"]) for item in pair]
        while len(cells) < 2:
            cells.append(Paragraph("", styles["body"]))
        rows.append(cells)
    table = Table(rows, colWidths=[85 * mm, 85 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return table


__all__ = ["build_styles", "generate_pdf"]
