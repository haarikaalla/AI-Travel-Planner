"""The JSON salvage parser is the last line of defence against messy models."""

from __future__ import annotations

import pytest

from travel_planner.llm import salvage_json


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('Sure! Here you go:\n{"a": 1}\nHope that helps.', {"a": 1}),
        ("[1, 2, 3]", [1, 2, 3]),
        ('```\n[{"x": true}]\n```', [{"x": True}]),
    ],
)
def test_salvages_valid_payloads(raw: str, expected: object) -> None:
    assert salvage_json(raw) == expected


def test_braces_inside_strings_do_not_break_depth_tracking() -> None:
    assert salvage_json('prefix {"note": "a } brace", "n": 2} suffix') == {
        "note": "a } brace",
        "n": 2,
    }


def test_escaped_quotes_are_handled() -> None:
    assert salvage_json(r'{"q": "say \"hi\""}') == {"q": 'say "hi"'}


@pytest.mark.parametrize("raw", ["", "   ", "no json at all", "{unclosed: "])
def test_returns_none_when_nothing_is_recoverable(raw: str) -> None:
    assert salvage_json(raw) is None
