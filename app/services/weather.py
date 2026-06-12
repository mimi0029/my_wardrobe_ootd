from __future__ import annotations

import os
import urllib.parse
import urllib.request
from typing import Any


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_context(
    city: str | None = None,
    temperature: float | None = None,
    weather: str | None = None,
    uv_index: float | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if city and api_key:
        remote = _fetch_openweather(city, api_key)
        if remote:
            if uv_index is not None:
                remote["uv_index"] = uv_index
            return remote

    return {
        "city": city or "手动输入",
        "temperature": temperature if temperature is not None else 24,
        "weather": weather or "晴",
        "uv_index": uv_index if uv_index is not None else 4,
        "source": "manual",
    }


def _fetch_openweather(city: str, api_key: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "zh_cn",
        }
    )
    try:
        with urllib.request.urlopen(f"{OPENWEATHER_URL}?{query}", timeout=8) as response:
            payload = response.read().decode("utf-8")
    except Exception:
        return None

    import json

    data = json.loads(payload)
    return {
        "city": data.get("name") or city,
        "temperature": float(data["main"]["temp"]),
        "weather": data["weather"][0]["description"],
        "uv_index": 4,
        "source": "openweather",
    }
