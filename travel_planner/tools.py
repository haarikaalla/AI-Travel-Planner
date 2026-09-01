"""
tools.py — real-world grounding.

An LLM asked "what is the weather in Reykjavik in March" will invent a number.
This module fetches the actual number first and injects it into the prompt, so
the model summarises facts instead of imagining them.

Every network source is free and keyless:

====================  ====================================================
Open-Meteo Geocoding  coordinates, country, timezone, population
Open-Meteo Archive    ERA5 reanalysis → real monthly climate normals
Frankfurter           live USD → local-currency exchange rate (ECB)
Wikipedia REST        encyclopaedic destination summary
====================  ====================================================

Currency, language and driving-side facts are resolved offline from
:mod:`travel_planner.countries`; REST Countries was dropped when v1-v4 were
retired and v5 began requiring an account.

Security notes: hosts are hard-allowlisted (no SSRF via destination names), all
user input is URL-encoded, every call is time-boxed, responses are size-capped,
and any failure degrades to ``None`` rather than raising.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import httpx

from travel_planner import countries
from travel_planner.config import get_settings
from travel_planner.schemas import GeoPoint

logger = logging.getLogger(__name__)

#: Requests may only ever be issued to these hosts.
ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "geocoding-api.open-meteo.com",
        "archive-api.open-meteo.com",
        "api.frankfurter.dev",
        "api.frankfurter.app",
        "en.wikipedia.org",
    }
)

#: Redirect targets are also permitted on these domains, because Frankfurter
#: 301-redirects between its own hosts and an exact-host allowlist alone would
#: break on every hop.
ALLOWED_SUFFIXES: tuple[str, ...] = (".frankfurter.dev", ".frankfurter.app")

MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 2_000_000
USER_AGENT = "AI-Travel-Planner/2.0 (+https://github.com/haarikaalla/AI-Travel-Planner)"


def _host_allowed(host: str | None) -> bool:
    """True only for the hard-coded public APIs this project talks to."""
    if not host:
        return False
    host = host.lower()
    return host in ALLOWED_HOSTS or host.endswith(ALLOWED_SUFFIXES)

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _get_json(url: str, params: dict[str, Any] | None = None) -> Any | None:
    """GET a JSON document from an allowlisted host. Never raises.

    Redirects are followed manually so that *every* hop is re-checked against
    the allowlist. Blindly setting ``follow_redirects=True`` would let a
    redirect walk the request onto an arbitrary host.
    """
    try:
        if not _host_allowed(httpx.URL(url).host):
            logger.warning("Blocked request to non-allowlisted host: %s", httpx.URL(url).host)
            return None

        timeout = get_settings().live_data_timeout_seconds
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ) as client:
            next_url, next_params = url, params
            for _ in range(MAX_REDIRECTS + 1):
                response = client.get(next_url, params=next_params)
                if response.is_redirect and response.headers.get("location"):
                    target = httpx.URL(response.headers["location"])
                    if not target.is_absolute_url:
                        target = httpx.URL(next_url).join(target)
                    if not _host_allowed(target.host):
                        logger.warning("Blocked redirect to %s", target.host)
                        return None
                    # Query parameters are already carried by the target URL.
                    next_url, next_params = str(target), None
                    continue

                response.raise_for_status()
                if len(response.content) > MAX_RESPONSE_BYTES:
                    logger.warning("Oversized response from %s", response.url.host)
                    return None
                return response.json()

            logger.warning("Too many redirects for %s", url)
            return None
    except Exception as exc:
        logger.info("Live data fetch failed for %s: %s", url, exc)
        return None


# ─────────────────────────────────────────────────────────────
#  Geocoding
# ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=256)
def geocode(destination: str) -> GeoPoint | None:
    """Resolve a free-text destination to coordinates, country and timezone."""
    data = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": destination[:120], "count": 1, "language": "en", "format": "json"},
    )
    results = (data or {}).get("results") or []
    if not results:
        return None
    hit = results[0]
    return GeoPoint(
        name=hit.get("name", destination),
        country=hit.get("country", ""),
        country_code=(hit.get("country_code") or "").upper(),
        latitude=float(hit.get("latitude", 0.0)),
        longitude=float(hit.get("longitude", 0.0)),
        timezone=hit.get("timezone", ""),
        population=int(hit.get("population") or 0),
    )


# ─────────────────────────────────────────────────────────────
#  Climate normals from ERA5 reanalysis
# ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=128)
def climate_normals(latitude: float, longitude: float) -> dict[str, Any] | None:
    """Twelve-month temperature and rainfall normals from real observations.

    Averages the two most recent complete years of ERA5 daily data, which is
    close enough to a climate normal for trip planning and needs no API key.
    """
    end = date.today().replace(day=1) - timedelta(days=1)
    start = date(end.year - 2, end.month, 1)

    data = _get_json(
        "https://archive-api.open-meteo.com/v1/archive",
        {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto",
        },
    )
    daily = (data or {}).get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        return None

    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_sum") or []

    buckets: dict[int, dict[str, list[float]]] = {
        m: {"high": [], "low": [], "rain": []} for m in range(1, 13)
    }
    for index, day in enumerate(dates):
        try:
            month = int(day[5:7])
        except (ValueError, IndexError):
            continue
        bucket = buckets[month]
        for key, series in (("high", highs), ("low", lows), ("rain", rain)):
            value = series[index] if index < len(series) else None
            if value is not None:
                bucket[key].append(float(value))

    def mean(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    months: list[dict[str, Any]] = []
    for number in range(1, 13):
        bucket = buckets[number]
        avg_high, avg_low = mean(bucket["high"]), mean(bucket["low"])
        if avg_high is None or avg_low is None:
            continue
        rain_days = sum(1 for value in bucket["rain"] if value >= 1.0)
        years = max(1, len(bucket["rain"]) // 28)
        months.append(
            {
                "month": MONTHS[number - 1],
                "avg_high_c": avg_high,
                "avg_low_c": avg_low,
                "avg_high_f": round(avg_high * 9 / 5 + 32),
                "avg_low_f": round(avg_low * 9 / 5 + 32),
                "rain_mm": round(sum(bucket["rain"]) / years, 1),
                "rainy_days": round(rain_days / years),
            }
        )

    if not months:
        return None

    comfort = sorted(months, key=lambda m: abs((m["avg_high_c"] + m["avg_low_c"]) / 2 - 21))
    return {
        "months": months,
        "annual_high_c": round(sum(m["avg_high_c"] for m in months) / len(months), 1),
        "annual_low_c": round(sum(m["avg_low_c"] for m in months) / len(months), 1),
        "best_months": [m["month"] for m in comfort[:3]],
        "wettest_month": max(months, key=lambda m: m["rain_mm"])["month"],
        "driest_month": min(months, key=lambda m: m["rain_mm"])["month"],
        "source": "Open-Meteo ERA5 reanalysis",
    }


# ─────────────────────────────────────────────────────────────
#  Country facts and money
# ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=256)
def country_facts(country: str, country_code: str = "") -> dict[str, Any] | None:
    """Currency, language and driving side for a destination's country.

    Resolved offline from :mod:`travel_planner.countries`. REST Countries used
    to serve this, but v1-v4 were retired and v5 requires an account, so a
    network call here would cost every user an API key for data that barely
    changes. Live exchange *rates* are still fetched over the network.
    """
    facts = countries.lookup(country_code)
    if not facts:
        return None
    languages = [facts["language"]] if facts.get("language") else []
    return {
        "country": country or facts["country_code"],
        "currency_code": facts["currency_code"],
        "currency_name": facts["currency_name"],
        "currency_symbol": facts["currency_symbol"],
        "languages": languages,
        "drives_on": facts["drives_on"],
        "source": facts["source"],
    }


@lru_cache(maxsize=256)
def exchange_rate(currency_code: str, base: str = "USD") -> dict[str, Any] | None:
    """Live ``base`` → ``currency_code`` rate from the ECB via Frankfurter."""
    code = (currency_code or "").strip().upper()
    if len(code) != 3 or not code.isalpha():
        return None
    if code == base:
        return {"rate": 1.0, "base": base, "code": code, "date": "", "source": "identity"}

    data = _get_json("https://api.frankfurter.dev/v1/latest", {"base": base, "symbols": code})
    rates = (data or {}).get("rates") or {}
    rate = rates.get(code)
    if rate is None:
        # Older deployments use the ``from``/``to`` parameter names.
        data = _get_json("https://api.frankfurter.dev/v1/latest", {"from": base, "to": code})
        rate = ((data or {}).get("rates") or {}).get(code)
    if rate is None:
        return None
    return {
        "rate": float(rate),
        "base": base,
        "code": code,
        "date": (data or {}).get("date", ""),
        "source": "Frankfurter / European Central Bank",
    }


# ─────────────────────────────────────────────────────────────
#  Encyclopaedic context
# ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=256)
def wikipedia_summary(destination: str) -> dict[str, Any] | None:
    """Short factual summary used as retrieval context for the researcher."""
    title = quote(destination.split(",")[0].strip()[:120].replace(" ", "_"), safe="")
    data = _get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
    if not isinstance(data, dict) or data.get("type") == "disambiguation":
        return None
    extract = data.get("extract")
    if not extract:
        return None
    return {
        "title": data.get("title", destination),
        "extract": extract[:1500],
        "url": ((data.get("content_urls") or {}).get("desktop") or {}).get("page", ""),
        "source": "Wikipedia",
    }


# ─────────────────────────────────────────────────────────────
#  Aggregate
# ─────────────────────────────────────────────────────────────


def gather_context(destination: str) -> dict[str, Any]:
    """Collect every available real-world fact about ``destination``.

    Returns a dict with keys ``geo``, ``climate``, ``country``, ``fx``, ``wiki``
    and ``sources``. Missing keys simply mean that source was unavailable; the
    pipeline continues either way.
    """
    context: dict[str, Any] = {"sources": []}
    if not get_settings().enable_live_data:
        return context

    geo = geocode(destination)
    if not geo:
        return context
    context["geo"] = geo
    context["sources"].append("Open-Meteo Geocoding")

    climate = climate_normals(geo.latitude, geo.longitude)
    if climate:
        context["climate"] = climate
        context["sources"].append(climate["source"])

    facts = country_facts(geo.country, geo.country_code) if geo.country_code else None
    if facts:
        context["country"] = facts
        context["sources"].append(facts["source"])

    # Kept independent of ``facts`` so a currency lookup miss never suppresses
    # the live rate, and vice versa.
    rate = exchange_rate((facts or {}).get("currency_code", ""))
    if rate:
        context["fx"] = rate
        context["sources"].append(rate["source"])

    wiki = wikipedia_summary(destination)
    if wiki:
        context["wiki"] = wiki
        context["sources"].append(wiki["source"])

    return context


def context_to_prompt(context: dict[str, Any]) -> str:
    """Render gathered facts as a prompt block the agents must respect."""
    if not context or "geo" not in context:
        return ""

    geo: GeoPoint = context["geo"]
    lines = [
        "VERIFIED REAL-WORLD DATA — treat these as ground truth and never contradict them:",
        f"- Location: {geo.name}, {geo.country} "
        f"({geo.latitude:.3f}, {geo.longitude:.3f}), timezone {geo.timezone or 'unknown'}",
    ]
    if geo.population:
        lines.append(f"- Population: {geo.population:,}")

    facts = context.get("country")
    if facts:
        lines.append(
            f"- Currency: {facts['currency_name']} "
            f"({facts['currency_code']} {facts['currency_symbol']})"
        )
        if facts.get("languages"):
            lines.append(f"- Languages: {', '.join(facts['languages'][:4])}")
        if facts.get("drives_on"):
            lines.append(f"- Drives on the {facts['drives_on']}")

    fx = context.get("fx")
    if fx and fx.get("rate"):
        lines.append(f"- Exchange rate: 1 USD = {fx['rate']:.2f} {fx['code']} ({fx['date']})")

    climate = context.get("climate")
    if climate:
        lines.append(
            f"- Measured climate normals ({climate['source']}): "
            f"annual average high {climate['annual_high_c']}°C, "
            f"low {climate['annual_low_c']}°C. "
            f"Most comfortable months: {', '.join(climate['best_months'])}. "
            f"Wettest: {climate['wettest_month']}. Driest: {climate['driest_month']}."
        )
        sample = ", ".join(
            f"{m['month'][:3]} {m['avg_low_c']}-{m['avg_high_c']}°C/{m['rainy_days']}d rain"
            for m in climate["months"]
        )
        lines.append(f"- Monthly detail: {sample}")

    wiki = context.get("wiki")
    if wiki:
        lines.append(f"- Encyclopedia context: {wiki['extract'][:700]}")

    return "\n".join(lines)


__all__ = [
    "ALLOWED_HOSTS",
    "ALLOWED_SUFFIXES",
    "climate_normals",
    "context_to_prompt",
    "country_facts",
    "exchange_rate",
    "gather_context",
    "geocode",
    "wikipedia_summary",
]
