"""Every exporter must survive real-world model output, including hostile input."""

from __future__ import annotations

from datetime import date

from travel_planner.exporters import (
    generate_ics,
    generate_markdown,
    generate_pdf,
    generate_text,
)
from travel_planner.exporters.pdf import _safe


def test_pdf_is_a_valid_document(plan: dict) -> None:
    data = generate_pdf(plan)
    assert data.startswith(b"%PDF")
    assert len(data) > 5000


def test_pdf_escapes_markup_that_would_corrupt_reportlab() -> None:
    assert _safe("<b>bold</b> & <script>") == "&lt;b&gt;bold&lt;/b&gt; &amp; &lt;script&gt;"


def test_pdf_strips_emoji_the_base_fonts_cannot_render() -> None:
    assert _safe("Day 1 🗺️ trip ✈️") == "Day 1 trip"


def test_pdf_handles_injected_markup_end_to_end(plan: dict) -> None:
    plan["summary"] = "<font color='red'>unclosed & broken <b>"
    plan["itinerary"][0]["title"] = "A & B <not a tag>"
    assert generate_pdf(plan).startswith(b"%PDF")


def test_text_export_covers_every_section(plan: dict) -> None:
    text = generate_text(plan)
    for heading in (
        "TRIP OVERVIEW",
        "DESTINATION BRIEF",
        "WEATHER & CLIMATE",
        "DAY-BY-DAY ITINERARY",
        "WHERE TO STAY",
        "FOOD GUIDE",
        "BUDGET",
        "PACKING LIST",
        "PLAN REVIEW",
    ):
        assert heading in text


def test_markdown_export_is_well_formed(plan: dict) -> None:
    markdown = generate_markdown(plan)
    assert markdown.startswith("# ")
    assert "## Itinerary" in markdown
    assert "| Time | Activity | Cost | Tip |" in markdown
    assert "- [ ] " in markdown


def test_ics_is_valid_and_dated_from_departure(plan: dict) -> None:
    calendar = generate_ics(plan, date(2026, 5, 1))
    assert calendar.startswith("BEGIN:VCALENDAR")
    assert calendar.rstrip().endswith("END:VCALENDAR")
    assert calendar.count("BEGIN:VEVENT") == calendar.count("END:VEVENT")
    assert calendar.count("BEGIN:VEVENT") == sum(
        len(day["activities"]) for day in plan["itinerary"]
    )
    assert "DTSTART:20260501T" in calendar
    assert "DTSTART:20260504T" in calendar  # day 4 of a 4-day trip


def test_ics_escapes_special_characters(plan: dict) -> None:
    plan["itinerary"][0]["activities"][0]["activity"] = "Lunch; then, a walk"
    calendar = generate_ics(plan, date(2026, 5, 1))
    assert "SUMMARY:Lunch\\; then\\, a walk" in calendar


def test_exporters_tolerate_an_empty_plan() -> None:
    assert generate_pdf({}).startswith(b"%PDF")
    assert generate_text({})
    assert generate_markdown({})
    assert "BEGIN:VCALENDAR" in generate_ics({})
