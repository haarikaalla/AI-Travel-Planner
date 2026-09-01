"""Live-data helpers: SSRF guard, parsing, and prompt rendering."""

from __future__ import annotations

import pytest

from travel_planner import tools
from travel_planner.schemas import GeoPoint
from travel_planner.tools import ALLOWED_HOSTS, context_to_prompt


def test_requests_to_unlisted_hosts_are_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """A destination name must never be able to steer an outbound request."""
    called = False

    def tripwire(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("network call should not have been attempted")

    monkeypatch.setattr(tools.httpx, "Client", tripwire)
    assert tools._get_json("http://169.254.169.254/latest/meta-data/") is None
    assert tools._get_json("https://evil.example.com/steal") is None
    assert called is False


def test_allowlist_is_limited_to_known_public_apis() -> None:
    assert frozenset(
        {
            "geocoding-api.open-meteo.com",
            "archive-api.open-meteo.com",
            "api.frankfurter.dev",
            "api.frankfurter.app",
            "en.wikipedia.org",
        }
    ) == ALLOWED_HOSTS


def test_host_check_accepts_allowed_subdomains_only() -> None:
    """Redirect hops may land on a sibling host, but never off-domain."""
    assert tools._host_allowed("api.frankfurter.dev")
    assert tools._host_allowed("fallback.frankfurter.dev")
    assert not tools._host_allowed("frankfurter.dev.evil.com")
    assert not tools._host_allowed("evil.com")
    assert not tools._host_allowed("")
    assert not tools._host_allowed(None)


def test_country_facts_resolve_offline() -> None:
    """Currency data must survive with no network at all."""
    japan = tools.country_facts("Japan", "JP")
    assert japan is not None
    assert japan["currency_code"] == "JPY"
    assert japan["drives_on"] == "left"
    assert japan["languages"] == ["Japanese"]
    assert tools.country_facts("Atlantis", "ZZ") is None


def test_context_prompt_is_empty_without_geo() -> None:
    assert context_to_prompt({}) == ""
    assert context_to_prompt({"sources": []}) == ""


def test_context_prompt_renders_every_available_fact() -> None:
    prompt = context_to_prompt(
        {
            "geo": GeoPoint(
                name="Kyoto", country="Japan", latitude=35.01, longitude=135.76,
                timezone="Asia/Tokyo", population=1_463_723,
            ),
            "country": {
                "currency_name": "Japanese yen", "currency_code": "JPY",
                "currency_symbol": "¥", "languages": ["Japanese"], "drives_on": "left",
            },
            "fx": {"rate": 155.42, "code": "JPY", "date": "2026-08-31"},
            "climate": {
                "annual_high_c": 20.4, "annual_low_c": 10.9,
                "best_months": ["April", "May", "October"],
                "wettest_month": "June", "driest_month": "December",
                "source": "Open-Meteo ERA5 reanalysis",
                "months": [
                    {"month": "January", "avg_low_c": 1.0, "avg_high_c": 9.0, "rainy_days": 6}
                ],
            },
            "wiki": {"extract": "Kyoto is a city on Honshu."},
            "sources": ["Open-Meteo Geocoding"],
        }
    )
    for fragment in (
        "ground truth", "Kyoto, Japan", "Asia/Tokyo", "1,463,723",
        "Japanese yen", "1 USD = 155.42 JPY", "20.4", "April, May, October",
        "Kyoto is a city on Honshu.",
    ):
        assert fragment in prompt


def test_exchange_rate_rejects_malformed_codes() -> None:
    assert tools.exchange_rate("") is None
    assert tools.exchange_rate("TOOLONG") is None
    assert tools.exchange_rate("1$X") is None
    assert tools.exchange_rate("USD")["rate"] == 1.0


@pytest.mark.integration
def test_geocode_against_the_live_api() -> None:
    point = tools.geocode("Kyoto, Japan")
    assert point is not None
    assert point.country == "Japan"
    assert point.country_code == "JP"
    assert 34 < point.latitude < 36
