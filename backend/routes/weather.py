"""
Weather endpoint: fetches current + 24h forecast for Dhanbad, Jharkhand
Uses Open-Meteo (free, no API key needed).
"""

from fastapi import APIRouter
import requests
from datetime import datetime, timedelta

router = APIRouter()

DHANBAD_LAT = 23.7957
DHANBAD_LON = 86.4304

def fallback_weather():
    """Return synthetic seasonal weather if API is unavailable."""
    now = datetime.now()
    month = now.month
    # Seasonal temperature averages for Dhanbad
    temp_map = {1:14,2:17,3:23,4:29,5:33,6:30,7:28,8:28,9:28,10:26,11:21,12:15}
    hum_map  = {1:60,2:55,3:45,4:38,5:42,6:72,7:85,8:85,9:78,10:65,11:58,12:60}
    base_temp = temp_map.get(month, 25)
    base_hum  = hum_map.get(month, 60)
    hourly = []
    for h in range(24):
        # Diurnal variation
        t = base_temp + 5 * (h - 6) / 12 if 6 <= h <= 14 else base_temp - 2
        hourly.append({
            "hour": h,
            "time": (now.replace(hour=h, minute=0, second=0)).strftime("%Y-%m-%d %H:%M"),
            "temperature": round(t, 1),
            "humidity": base_hum + (5 if h < 8 else -3),
            "windspeed": 3.5,
            "cloudcover": 30,
            "description": "Partly cloudy (estimated)"
        })
    return {"source": "estimated", "hourly": hourly}

@router.get("/weather")
def get_weather():
    """
    Fetch 24-hour weather forecast for Dhanbad, Jharkhand.
    Returns temperature, humidity, wind speed, and cloud cover per hour.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": DHANBAD_LAT,
            "longitude": DHANBAD_LON,
            "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m,cloudcover,weathercode",
            "current_weather": True,
            "timezone": "Asia/Kolkata",
            "forecast_days": 2
        }
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current_weather", {})
        hourly = data["hourly"]

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Filter to next 24 hours
        times = hourly["time"]
        hourly_data = []
        for i, t in enumerate(times):
            dt = datetime.fromisoformat(t)
            if dt >= now and dt < now + timedelta(hours=25):
                # Map weather code to description
                wcode = hourly.get("weathercode", [0]*len(times))[i] if "weathercode" in hourly else 0
                desc = weather_code_to_desc(wcode)
                hourly_data.append({
                    "hour": dt.hour,
                    "time": t,
                    "temperature":  round(hourly["temperature_2m"][i], 1),
                    "humidity":     hourly["relativehumidity_2m"][i],
                    "windspeed":    round(hourly["windspeed_10m"][i], 1),
                    "cloudcover":   hourly["cloudcover"][i],
                    "description":  desc
                })

        return {
            "location":  "Dhanbad, Jharkhand, India",
            "latitude":  DHANBAD_LAT,
            "longitude": DHANBAD_LON,
            "source":    "Open-Meteo (open-meteo.com)",
            "current": {
                "temperature": current.get("temperature", 25),
                "windspeed":   current.get("windspeed", 3),
                "time":        current.get("time", now.strftime("%Y-%m-%dT%H:%M"))
            },
            "hourly": hourly_data[:25]
        }

    except Exception as e:
        # Return fallback data
        fallback = fallback_weather()
        fallback["error"] = f"API unavailable: {str(e)[:80]}"
        fallback["location"] = "Dhanbad, Jharkhand, India"
        return fallback


def weather_code_to_desc(code: int) -> str:
    mapping = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 61: "Light rain",
        63: "Moderate rain", 65: "Heavy rain", 71: "Light snow", 80: "Rain showers",
        95: "Thunderstorm", 99: "Thunderstorm with hail"
    }
    return mapping.get(code, f"Code {code}")
