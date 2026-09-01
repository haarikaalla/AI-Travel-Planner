"""
documents.py — plain-text, Markdown and calendar renderers.

All three take the same dict that the composer produces, so they stay in sync
with the PDF renderer without a shared base class.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

RULE = "=" * 68
THIN = "-" * 44


def _get(source: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or a Pydantic model interchangeably."""
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _destination_lines(brief: Any) -> list[str]:
    if not brief:
        return []
    lines: list[str] = []
    essence = _get(brief, "essence", "")
    if essence:
        lines.append(essence)
    for label, key in (
        ("Where to stay", "best_neighborhoods"),
        ("Do not miss", "iconic_attractions"),
        ("Local customs", "culture_customs"),
        ("Safety", "safety_notes"),
        ("Useful phrases", "language_phrases"),
    ):
        items = _get(brief, key, []) or []
        if items:
            lines.append(f"\n{label}:")
            lines.extend(f"  • {item}" for item in items)
    for label, key in (("Getting around", "getting_around"), ("Best timing", "ideal_timing")):
        value = _get(brief, key, "")
        if value:
            lines.append(f"\n{label}: {value}")
    return lines


# ─────────────────────────────────────────────────────────────
#  Plain text
# ─────────────────────────────────────────────────────────────


def generate_text(plan: dict[str, Any]) -> str:
    """Render the whole plan as a monospace-friendly text document."""
    overview = plan.get("overview", {})
    destination = overview.get("Destination", "Your Trip")

    out: list[str] = [
        RULE,
        f"  AI TRAVEL PLANNER — {destination.upper()}",
        "  " + "  ·  ".join(f"{k}: {v}" for k, v in overview.items() if k != "Destination"),
        RULE,
        "",
    ]

    if plan.get("summary"):
        out += ["TRIP OVERVIEW", THIN, plan["summary"], ""]

    sources = plan.get("live_sources") or []
    if sources:
        out += [f"Grounded by live data from: {', '.join(sources)}", ""]

    brief_lines = _destination_lines(plan.get("destination"))
    if brief_lines:
        out += ["DESTINATION BRIEF", THIN, *brief_lines, ""]

    weather = plan.get("weather") or {}
    if weather:
        out += [
            "WEATHER & CLIMATE",
            THIN,
            _get(weather, "season_overview", ""),
            f"Temperature: {_get(weather, 'temperature_range', 'n/a')}",
            f"Best months: {', '.join(_get(weather, 'best_months', []) or []) or 'n/a'}",
            f"What to wear: {_get(weather, 'clothing_advice', 'n/a')}",
            "",
        ]

    out += ["DAY-BY-DAY ITINERARY", THIN]
    for day in plan.get("itinerary", []):
        out.append(
            f"\nDay {_get(day, 'day')} — {_get(day, 'title', '')} {_get(day, 'theme_emoji', '')}"
        )
        for activity in _get(day, "activities", []) or []:
            out.append(
                f"  {_get(activity, 'time', ''):>9}  {_get(activity, 'activity', '')}"
                f" — {_get(activity, 'description', '')}"
            )
            tip = _get(activity, "pro_tip", "")
            if tip:
                out.append(f"  {'':>9}  tip: {tip}")
        cost = _get(day, "estimated_daily_cost", "")
        if cost:
            out.append(f"  {'':>9}  Estimated cost: {cost}")

    out += ["", "WHERE TO STAY", THIN]
    for stay in plan.get("accommodations", []):
        out.append(
            f"\n{_get(stay, 'name', '')} ({_get(stay, 'type', '')} · "
            f"{_get(stay, 'price_range', '')})"
        )
        out.append(f"  {_get(stay, 'neighborhood', '')} | {_get(stay, 'description', '')}")
        out.append(f"  Booking tip: {_get(stay, 'booking_tip', '')}")

    food = plan.get("food") or {}
    if food:
        out += ["", "FOOD GUIDE", THIN, _get(food, "culinary_intro", "")]
        for dish in _get(food, "must_try_dishes", []) or []:
            out.append(f"  • {_get(dish, 'name', '')} — {_get(dish, 'description', '')}")
        for restaurant in _get(food, "restaurants", []) or []:
            out.append(
                f"  • {_get(restaurant, 'name', '')} ({_get(restaurant, 'price', '')}) — "
                f"order the {_get(restaurant, 'signature_dish', '')}"
            )

    budget = plan.get("budget") or {}
    if budget:
        out += ["", "BUDGET", THIN]
        for key, value in (_get(budget, "per_person_breakdown", {}) or {}).items():
            out.append(f"  {key.replace('_', ' ').title():<28} {value}")
        if _get(budget, "total_for_group", ""):
            out.append(f"\n  GROUP TOTAL: {_get(budget, 'total_for_group')}")

    packing = plan.get("packing") or {}
    if packing:
        out += ["", "PACKING LIST", THIN]
        for label, key in (
            ("Essentials", "essentials"),
            ("Documents & money", "documents_money"),
            ("Electronics", "electronics"),
            ("Health & safety", "health_safety"),
            ("Leave at home", "do_not_pack"),
        ):
            items = _get(packing, key, []) or []
            if items:
                out.append(f"\n{label}:")
                out.extend(f"  [ ] {item}" for item in items)

    review = plan.get("review") or {}
    if review:
        out += ["", "PLAN REVIEW", THIN, f"Score: {_get(review, 'overall_score', '?')}/100"]
        for risk in _get(review, "risks", []) or []:
            out.append(f"  ! {risk}")
        for fix in _get(review, "fixes", []) or []:
            out.append(f"  > {fix}")

    out += ["", RULE, "Generated by AI Travel Planner · LangGraph multi-agent system", RULE]
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────
#  Markdown
# ─────────────────────────────────────────────────────────────


def generate_markdown(plan: dict[str, Any]) -> str:
    """Render the plan as GitHub-flavoured Markdown (great for Notion/Obsidian)."""
    overview = plan.get("overview", {})
    destination = overview.get("Destination", "Your Trip")

    out: list[str] = [f"# {destination} — Travel Plan", ""]
    if plan.get("summary"):
        out += [f"> {plan['summary']}", ""]

    out += ["| Field | Value |", "| --- | --- |"]
    out += [f"| {key} | {value} |" for key, value in overview.items()]
    out.append("")

    sources = plan.get("live_sources") or []
    if sources:
        out += [f"*Grounded by live data from: {', '.join(sources)}*", ""]

    weather = plan.get("weather") or {}
    if weather:
        out += [
            "## Weather",
            "",
            _get(weather, "season_overview", ""),
            "",
            f"- **Temperature:** {_get(weather, 'temperature_range', 'n/a')}",
            f"- **Best months:** {', '.join(_get(weather, 'best_months', []) or []) or 'n/a'}",
            f"- **What to wear:** {_get(weather, 'clothing_advice', 'n/a')}",
            "",
        ]

    out += ["## Itinerary", ""]
    for day in plan.get("itinerary", []):
        out += [
            f"### {_get(day, 'theme_emoji', '')} Day {_get(day, 'day')} — {_get(day, 'title', '')}",
            "",
            "| Time | Activity | Cost | Tip |",
            "| --- | --- | --- | --- |",
        ]
        for activity in _get(day, "activities", []) or []:
            out.append(
                f"| {_get(activity, 'time', '')} | **{_get(activity, 'activity', '')}** — "
                f"{_get(activity, 'description', '')} | {_get(activity, 'cost', '')} | "
                f"{_get(activity, 'pro_tip', '')} |"
            )
        out += ["", f"_{_get(day, 'day_highlights', '')}_", ""]

    out += ["## Where to Stay", ""]
    for stay in plan.get("accommodations", []):
        out += [
            f"### {_get(stay, 'name', '')}",
            f"`{_get(stay, 'type', '')}` · `{_get(stay, 'price_range', '')}` · "
            f"`{_get(stay, 'neighborhood', '')}`",
            "",
            _get(stay, "description", ""),
            "",
            f"- Pro: {_get(stay, 'pros', '')}",
            f"- Con: {_get(stay, 'cons', '')}",
            f"- Booking tip: {_get(stay, 'booking_tip', '')}",
            "",
        ]

    budget = plan.get("budget") or {}
    if budget:
        out += ["## Budget", "", "| Item | Cost |", "| --- | --- |"]
        for key, value in (_get(budget, "per_person_breakdown", {}) or {}).items():
            out.append(f"| {key.replace('_', ' ').title()} | {value} |")
        out += ["", f"**Group total:** {_get(budget, 'total_for_group', '')}", ""]

    packing = plan.get("packing") or {}
    if packing:
        out += ["## Packing Checklist", ""]
        for label, key in (
            ("Essentials", "essentials"),
            ("Documents & money", "documents_money"),
            ("Electronics", "electronics"),
            ("Activity gear", "activity_gear"),
        ):
            items = _get(packing, key, []) or []
            if items:
                out += [f"**{label}**", ""]
                out += [f"- [ ] {item}" for item in items]
                out.append("")

    review = plan.get("review") or {}
    if review:
        out += [
            "## Plan Review",
            "",
            f"**Score: {_get(review, 'overall_score', '?')}/100** — "
            f"{_get(review, 'pacing_verdict', '')}",
            "",
        ]
        for risk in _get(review, "risks", []) or []:
            out.append(f"- ⚠️ {risk}")
        for fix in _get(review, "fixes", []) or []:
            out.append(f"- ✅ {fix}")
        out.append("")

    out += ["---", "", "*Generated by AI Travel Planner — LangGraph multi-agent system*"]
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────
#  Calendar
# ─────────────────────────────────────────────────────────────

_DEFAULT_HOUR = 9


def _parse_clock(value: str) -> time:
    """Parse '9:00 AM' / '14:30' / '9 AM' loosely; fall back to 09:00."""
    text = (value or "").strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return time(hour=_DEFAULT_HOUR)


def generate_ics(plan: dict[str, Any], start_date: date | None = None) -> str:
    """Render the itinerary as an RFC 5545 calendar importable anywhere.

    Written by hand rather than via a dependency so the export path has no
    runtime requirements beyond the standard library.
    """
    start = start_date or (date.today() + timedelta(days=30))
    destination = (plan.get("overview") or {}).get("Destination", "Trip")
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def escape(text: str) -> str:
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Travel Planner//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape(destination)} itinerary",
    ]

    for day in plan.get("itinerary", []):
        day_number = int(_get(day, "day", 1) or 1)
        day_date = start + timedelta(days=day_number - 1)
        for index, activity in enumerate(_get(day, "activities", []) or []):
            begin = datetime.combine(day_date, _parse_clock(_get(activity, "time", "")))
            finish = begin + timedelta(hours=2)
            description = " | ".join(
                part
                for part in (
                    _get(activity, "description", ""),
                    f"Cost: {_get(activity, 'cost', '')}" if _get(activity, "cost") else "",
                    f"Tip: {_get(activity, 'pro_tip', '')}" if _get(activity, "pro_tip") else "",
                )
                if part
            )
            lines += [
                "BEGIN:VEVENT",
                f"UID:travelplanner-{day_number}-{index}-{stamp}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{begin.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{finish.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{escape(_get(activity, 'activity', 'Activity'))}",
                f"DESCRIPTION:{escape(description)}",
                f"LOCATION:{escape(destination)}",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


__all__ = ["generate_ics", "generate_markdown", "generate_text"]
