"""
Weather service for fetching current weather data from Open-Meteo API.
Uses hive coordinates to get real-time temperature and humidity.
"""
import requests
from typing import Optional
from datetime import datetime


class WeatherData:
    """Weather data model for Open-Meteo response."""
    
    def __init__(
        self,
        temperature: float,
        humidity: float,
        timestamp: str,
        weather_code: Optional[int] = None
    ):
        self.temperature = temperature
        self.humidity = humidity
        self.timestamp = timestamp
        self.weather_code = weather_code


def fetch_weather(latitude: float, longitude: float) -> Optional[WeatherData]:
    """
    Fetch current weather data from Open-Meteo API.
    
    Args:
        latitude: Hive latitude coordinate
        longitude: Hive longitude coordinate
        
    Returns:
        WeatherData object or None if request fails
    """
    try:
        # Open-Meteo API endpoint with current weather
        url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code"],
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        current = data.get("current", {})
        
        if not current:
            return None
        
        return WeatherData(
            temperature=current.get("temperature_2m", 0.0),
            humidity=current.get("relative_humidity_2m", 0.0),
            timestamp=current.get("time", datetime.utcnow().isoformat()),
            weather_code=current.get("weather_code")
        )
        
    except requests.exceptions.RequestException as e:
        # Log the error but don't fail the request
        print(f"Weather API error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching weather: {e}")
        return None


def get_weather_description(weather_code: Optional[int]) -> str:
    """
    Convert WMO weather code to human-readable description.
    https://www.noaa.gov/weather
    """
    if weather_code is None:
        return "Unknown"
    
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Foggy",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail",
    }
    
    return weather_codes.get(weather_code, "Unknown")
