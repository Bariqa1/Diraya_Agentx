"""Weather and Geocoding Service for DIRAYA.

Fetches live atmospheric conditions from Open-Meteo API (free, no API key required)
and reverse geocodes facility/worker coordinates using OpenStreetMap Nominatim.
Includes fallback support for Jubail Industrial City if network is offline.
"""
import logging
import os
from typing import Dict, Optional
import requests

LOG = logging.getLogger(__name__)

# Default facility location: Jubail Industrial City, Eastern Province, Saudi Arabia
DEFAULT_LATITUDE = float(os.getenv("FACILITY_LATITUDE", "27.0046"))
DEFAULT_LONGITUDE = float(os.getenv("FACILITY_LONGITUDE", "49.6586"))
DEFAULT_CITY = os.getenv("FACILITY_CITY", "Jubail Industrial City")


class WeatherService:
    def __init__(self, timeout: float = 8.0):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.geocoding_url = "https://nominatim.openstreetmap.org/reverse"
        self.timeout = timeout

    def get_current_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        """
        Fetch real-time atmospheric measurements:
          - temperature_2m (°C)
          - relative_humidity_2m (%)
          - wind_speed_10m (m/s)
          - weather_code (WMO code)
          - is_day (1 = day, 0 = night)
        """
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lon = longitude if longitude is not None else DEFAULT_LONGITUDE

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "wind_speed_10m,"
                "weather_code,"
                "is_day"
            ),
            "wind_speed_unit": "ms",
            "timezone": "auto",
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            current = resp.json()["current"]

            return {
                "temperature_c": float(current["temperature_2m"]),
                "humidity_percent": float(current["relative_humidity_2m"]),
                "wind_speed_mps": float(current["wind_speed_10m"]),
                "weather_code": int(current["weather_code"]),
                "is_day": bool(current["is_day"]),
                "time": str(current["time"]),
                "source": "open-meteo",
            }
        except Exception as exc:
            LOG.warning("Live weather fetch failed (%s), using industrial baseline.", exc)
            return {
                "temperature_c": 37.5,
                "humidity_percent": 55.0,
                "wind_speed_mps": 2.4,
                "weather_code": 0,
                "is_day": True,
                "time": "simulated_baseline",
                "source": "industrial_baseline_fallback",
            }

    def get_location(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        """Reverse geocodes latitude/longitude to human-readable address."""
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lon = longitude if longitude is not None else DEFAULT_LONGITUDE

        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
            "zoom": 18,
        }
        headers = {"User-Agent": "DIRAYA-Safety-Agent/1.0"}

        try:
            resp = requests.get(self.geocoding_url, params=params, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            address = data.get("address", {})

            return {
                "display_name": data.get("display_name", f"{DEFAULT_CITY}, Saudi Arabia"),
                "road": address.get("road"),
                "neighbourhood": (
                    address.get("neighbourhood")
                    or address.get("suburb")
                    or address.get("quarter")
                ),
                "city": (
                    address.get("city")
                    or address.get("town")
                    or address.get("municipality")
                    or DEFAULT_CITY
                ),
                "state": address.get("state", "Eastern Province"),
                "country": address.get("country", "Saudi Arabia"),
                "postcode": address.get("postcode"),
                "latitude": lat,
                "longitude": lon,
                "source": "nominatim",
            }
        except Exception as exc:
            LOG.warning("Reverse geocoding failed (%s), using default facility location.", exc)
            return {
                "display_name": f"{DEFAULT_CITY}, Eastern Province, Saudi Arabia",
                "road": "Industrial Park Road 1",
                "neighbourhood": "Support Industrial Area",
                "city": DEFAULT_CITY,
                "state": "Eastern Province",
                "country": "Saudi Arabia",
                "postcode": "31961",
                "latitude": lat,
                "longitude": lon,
                "source": "default_fallback",
            }
