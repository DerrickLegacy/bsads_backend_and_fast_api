"""
Weather API routes for testing and fetching weather data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from api.database import get_db
from api.models import Hive, User, EnvironmentalData
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


class EnvironmentalDataPoint(BaseModel):
    """Single environmental data point for time series."""
    temperature: float
    humidity: float
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class EnvironmentalTimeSeriesResponse(BaseModel):
    """Time series environmental data for a hive."""
    hive_id: str
    hive_name: Optional[str]
    data_points: List[EnvironmentalDataPoint]
    total_records: int
    period_start: Optional[datetime]
    period_end: Optional[datetime]


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


@router.get("/hive/{hive_id}/history", response_model=EnvironmentalTimeSeriesResponse)
def get_hive_environmental_history(
    hive_id: str,
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back (1-720, default 24)"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of data points to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get historical temperature and humidity data for a specific hive.
    
    This endpoint returns time series environmental data perfect for charts and graphs.
    
    **Parameters:**
    - `hours`: Number of hours to look back (default: 24, max: 720 = 30 days)
    - `limit`: Maximum number of data points to return (default: all, max: 1000)
    
    **Use Cases:**
    - Display temperature/humidity charts on mobile app
    - Analyze environmental trends over time
    - Correlate weather patterns with hive behavior
    
    **Example:**
    - Last 24 hours: `GET /weather/hive/{hive_id}/history`
    - Last 7 days: `GET /weather/hive/{hive_id}/history?hours=168`
    - Last 30 days, max 100 points: `GET /weather/hive/{hive_id}/history?hours=720&limit=100`
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
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # Query environmental data
    query = (
        db.query(EnvironmentalData)
        .filter(
            EnvironmentalData.hive_id == hive_id,
            EnvironmentalData.recorded_at >= start_time,
            EnvironmentalData.recorded_at <= end_time
        )
        .order_by(EnvironmentalData.recorded_at.desc())
    )
    
    # Apply limit if specified
    if limit:
        query = query.limit(limit)
    
    data_points = query.all()
    
    # Reverse to get chronological order (oldest first)
    data_points.reverse()
    
    # Calculate period bounds
    period_start = data_points[0].recorded_at if data_points else None
    period_end = data_points[-1].recorded_at if data_points else None
    
    return EnvironmentalTimeSeriesResponse(
        hive_id=str(hive.hive_id),
        hive_name=hive.hive_name,
        data_points=[
            EnvironmentalDataPoint(
                temperature=float(point.temperature) if point.temperature else 0.0,
                humidity=float(point.humidity) if point.humidity else 0.0,
                recorded_at=point.recorded_at
            )
            for point in data_points
        ],
        total_records=len(data_points),
        period_start=period_start,
        period_end=period_end
    )


@router.get("/hive/{hive_id}/summary", response_model=dict)
def get_hive_environmental_summary(
    hive_id: str,
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back (1-720, default 24)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistical summary of environmental data for a hive.
    
    Returns min, max, average temperature and humidity over the specified time period.
    Useful for dashboard summary cards and quick insights.
    
    **Parameters:**
    - `hours`: Number of hours to look back (default: 24, max: 720 = 30 days)
    
    **Returns:**
    - Average, min, max temperature and humidity
    - Data point count
    - Time range
    
    **Example:**
    - Last 24 hours summary: `GET /weather/hive/{hive_id}/summary`
    - Last week summary: `GET /weather/hive/{hive_id}/summary?hours=168`
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
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # Query environmental data
    data_points = (
        db.query(EnvironmentalData)
        .filter(
            EnvironmentalData.hive_id == hive_id,
            EnvironmentalData.recorded_at >= start_time,
            EnvironmentalData.recorded_at <= end_time
        )
        .all()
    )
    
    if not data_points:
        raise HTTPException(
            status_code=404, 
            detail=f"No environmental data found for this hive in the last {hours} hours"
        )
    
    # Calculate statistics
    temperatures = [float(p.temperature) for p in data_points if p.temperature is not None]
    humidities = [float(p.humidity) for p in data_points if p.humidity is not None]
    
    return {
        "hive_id": str(hive.hive_id),
        "hive_name": hive.hive_name,
        "period_hours": hours,
        "period_start": min(p.recorded_at for p in data_points),
        "period_end": max(p.recorded_at for p in data_points),
        "data_point_count": len(data_points),
        "temperature": {
            "average": round(sum(temperatures) / len(temperatures), 2) if temperatures else None,
            "min": round(min(temperatures), 2) if temperatures else None,
            "max": round(max(temperatures), 2) if temperatures else None,
            "unit": "°C"
        },
        "humidity": {
            "average": round(sum(humidities) / len(humidities), 2) if humidities else None,
            "min": round(min(humidities), 2) if humidities else None,
            "max": round(max(humidities), 2) if humidities else None,
            "unit": "%"
        }
    }
