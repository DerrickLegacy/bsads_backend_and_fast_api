"""
Weather API routes for testing and fetching weather data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from api.database import get_db
from api.models import Hive, User
from api.routers.auth import get_current_user
from api.weather_service import fetch_weather, get_weather_description
from pydantic import BaseModel


class WeatherResponse(BaseModel):
    """Weather data response for a specific hive or coordinates."""
    hive_id: Optional[str] = None
    hive_name: Optional[str] = None
    latitude: float
    longitude: float
    temperature: float
    humidity: float
    timestamp: str
    weather_description: Optional[str] = None


router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/test", response_model=WeatherResponse)
def test_weather_api(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
):
    """
    Test the Open-Meteo weather API with specific coordinates.
    
    Example: GET /weather/test?latitude=0.3476&longitude=32.5825
    
    This endpoint doesn't require authentication and is useful for testing
    the weather service integration.
    """
    weather = fetch_weather(latitude, longitude)
    
    if not weather:
        raise HTTPException(
            status_code=503,
            detail="Weather service unavailable. Please try again later."
        )
    
    return WeatherResponse(
        latitude=latitude,
        longitude=longitude,
        temperature=weather.temperature,
        humidity=weather.humidity,
        timestamp=weather.timestamp,
        weather_description=get_weather_description(weather.weather_code)
    )


@router.get("/hive/{hive_id}", response_model=WeatherResponse)
def get_hive_weather(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current weather data for a specific hive using its coordinates.
    
    Returns weather data based on the hive's latitude and longitude.
    If the hive doesn't have coordinates set, returns 400 error.
    """
    # Check if user has access to this hive
    q = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.is_deleted == False,
    )
    
    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)
    
    hive = q.first()
    
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")
    
    if hive.latitude is None or hive.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Hive does not have coordinates set. Please update the hive location."
        )
    
    weather = fetch_weather(float(hive.latitude), float(hive.longitude))
    
    if not weather:
        raise HTTPException(
            status_code=503,
            detail="Weather service unavailable. Please try again later."
        )
    
    return WeatherResponse(
        hive_id=str(hive.hive_id),
        hive_name=hive.hive_name,
        latitude=float(hive.latitude),
        longitude=float(hive.longitude),
        temperature=weather.temperature,
        humidity=weather.humidity,
        timestamp=weather.timestamp,
        weather_description=get_weather_description(weather.weather_code)
    )
