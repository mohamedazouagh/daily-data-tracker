"""Fetch daily data from free public APIs (no keys needed)."""
from __future__ import annotations

import json
import urllib.request

BREDA = {"latitude": 51.5719, "longitude": 4.7683}
USER_AGENT = "daily-data-tracker (github.com/mohamedazouagh)"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def weather_url(day: str) -> str:
    return (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={BREDA['latitude']}&longitude={BREDA['longitude']}"
        f"&start_date={day}&end_date={day}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration"
        "&timezone=Europe%2FAmsterdam"
    )


def parse_weather(payload: dict) -> dict:
    """Turn an Open-Meteo daily payload into one flat row."""
    d = payload["daily"]
    sunshine_s = d["sunshine_duration"][0]
    return {
        "date": d["time"][0],
        "temp_max_c": d["temperature_2m_max"][0],
        "temp_min_c": d["temperature_2m_min"][0],
        "precip_mm": d["precipitation_sum"][0],
        "sunshine_h": None if sunshine_s is None else round(sunshine_s / 3600, 2),
    }


def fx_url(day: str) -> str:
    return f"https://api.frankfurter.app/{day}?from=EUR&to=USD,GBP,CHF,TRY"


def parse_fx(payload: dict) -> dict:
    """Frankfurter returns the last business day's rates for weekends/holidays."""
    rates = payload["rates"]
    return {
        "date": payload["date"],
        "usd": rates.get("USD"),
        "gbp": rates.get("GBP"),
        "chf": rates.get("CHF"),
        "try": rates.get("TRY"),
    }


def fetch_weather(day: str) -> dict:
    return parse_weather(_get_json(weather_url(day)))


def fetch_fx(day: str) -> dict:
    return parse_fx(_get_json(fx_url(day)))
