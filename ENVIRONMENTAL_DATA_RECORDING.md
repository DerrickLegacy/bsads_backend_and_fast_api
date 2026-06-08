# Automatic Environmental Data Recording

## Overview

The system now **automatically records environmental data (weather conditions) at the exact moment audio is captured**. This provides critical context for understanding hive behavior and enables accurate correlation between acoustic patterns and environmental factors.

## How It Works

### Automatic Recording Flow

1. **Audio Recording Received** → Audio file is added to `audio_sources` table with `status='pending'`
   - **🌡️ Environmental data is recorded at this exact moment** (temperature, humidity)
   - Data is saved to `environmental_data` table with matching timestamp
   
2. **Audio Processing Begins** → Poller picks up the audio and processes it

3. **Inference Complete** → ML model classifies the hive state

4. **Advisory Generated** → Alerts and advisories created if needed

### Why Record at Capture Time?

Recording environmental data **at the moment audio is captured** (not during processing) ensures:
- **Accurate correlation**: Temperature/humidity matches the exact conditions when bees made the sounds
- **No time lag**: Processing can take 30+ seconds; weather conditions may change
- **Historical accuracy**: Even if processing is delayed, environmental data reflects the true capture moment

### Two Entry Points

Environmental data recording happens in two places:

#### 1. Automatic Poller Discovery
When the poller discovers new audio files from farmer data sources, it:
- Registers the audio file as `pending` in `audio_sources`
- Immediately fetches weather data using hive coordinates
- Saves to `environmental_data` table

**Code location**: `api/poller_concurrent.py` → `_register_pending()`

#### 2. Manual Audio Upload
When farmers upload audio files via the API, it:
- Saves the audio file to disk
- Registers it as `pending` in `audio_sources`
- Immediately fetches weather data using hive coordinates
- Saves to `environmental_data` table
- Queues background processing

**Code location**: `api/routers/audio.py` → `upload_audio()` → `_record_environmental_data_on_upload()`

### Data Recorded

For each audio recording captured, the system records:
- **Temperature** (°C) - current air temperature at hive location
- **Humidity** (%) - relative humidity at hive location
- **Timestamp** (`recorded_at`) - when the data was captured (auto-set to current time)
- **Hive ID** - links the environmental data to the specific hive

### Weather API Providers

The system supports two weather data providers:

#### 1. Open-Meteo API (Default)
- **Free** and requires **no API key**
- Automatically used if no OpenWeather API key is configured
- Provides accurate temperature and humidity data
- Endpoint: `https://api.open-meteo.com/v1/forecast`

#### 2. OpenWeatherMap API (Optional)
- Requires API key (get one at https://openweathermap.org/api)
- Set `OPENWEATHER_API_KEY` in your `.env` file to enable
- Provides additional weather metadata
- Endpoint: `https://api.openweathermap.org/data/2.5/weather`

## Configuration

### Using Open-Meteo (Default)
No configuration needed! Just ensure your hives have latitude and longitude set.

### Using OpenWeatherMap (Optional)

1. Get an API key from https://openweathermap.org/api
2. Add to your `.env` file:
   ```env
   OPENWEATHER_API_KEY=your_api_key_here
   ```
3. Restart the application

## Requirements

### Hive Coordinates Required

For environmental data recording to work, each hive **must have**:
- `latitude` (numeric, 9 digits, 6 decimal places)
- `longitude` (numeric, 9 digits, 6 decimal places)

**Example:**
```sql
UPDATE hives 
SET latitude = 0.3476, longitude = 32.5825 
WHERE hive_id = 'your-hive-id';
```

If a hive doesn't have coordinates:
- ⚠️ A warning is logged
- Environmental data recording is skipped for that audio file
- Audio processing continues normally

## Database Schema

### environmental_data Table

```sql
CREATE TABLE environmental_data (
    env_record_id UUID PRIMARY KEY,
    hive_id UUID REFERENCES hives(hive_id) ON DELETE CASCADE,
    temperature NUMERIC(5,2),      -- Temperature in Celsius
    humidity NUMERIC(5,2),         -- Relative humidity (%)
    recorded_at TIMESTAMP DEFAULT NOW(),  -- When the data was recorded
);
```

### Relationship to audio_sources

```
audio_sources (audio captured at time T)
    ↓
environmental_data (weather at time T)
    ↓
inference_results (ML classification)
    ↓
advisories + alerts (farmer notifications)
```

## Querying Environmental Data

### Get Recent Environmental Data for a Hive

```sql
SELECT 
    temperature,
    humidity,
    recorded_at
FROM environmental_data
WHERE hive_id = 'your-hive-id'
ORDER BY recorded_at DESC
LIMIT 10;
```

### Correlate Environmental Data with Audio Recordings

Since environmental data is recorded at the exact same time as audio capture, correlation is straightforward:

```sql
SELECT 
    a.audio_id,
    a.captured_at as audio_time,
    a.status as audio_status,
    e.temperature,
    e.humidity,
    e.recorded_at as env_recorded_time,
    i.hive_state,
    i.confidence_score
FROM audio_sources a
LEFT JOIN environmental_data e ON e.hive_id = a.hive_id 
    AND e.recorded_at BETWEEN a.ingestion_timestamp - INTERVAL '2 minutes' 
                          AND a.ingestion_timestamp + INTERVAL '2 minutes'
LEFT JOIN inference_results i ON i.audio_id = a.audio_id
WHERE a.hive_id = 'your-hive-id'
ORDER BY a.ingestion_timestamp DESC
LIMIT 20;
```

### Find Patterns: Temperature vs Hive State

```sql
SELECT 
    i.hive_state,
    ROUND(AVG(e.temperature), 2) as avg_temperature,
    ROUND(AVG(e.humidity), 2) as avg_humidity,
    COUNT(*) as occurrences
FROM inference_results i
JOIN audio_sources a ON a.audio_id = i.audio_id
JOIN environmental_data e ON e.hive_id = i.hive_id 
    AND e.recorded_at BETWEEN a.ingestion_timestamp - INTERVAL '2 minutes'
                          AND a.ingestion_timestamp + INTERVAL '2 minutes'
WHERE i.hive_id = 'your-hive-id'
GROUP BY i.hive_state
ORDER BY occurrences DESC;
```

## Error Handling

The system is designed to be resilient:

- **No Coordinates**: ⚠️ Warning logged, environmental recording skipped, audio processing continues
- **Weather API Unavailable**: ⚠️ Warning logged, environmental recording skipped, audio processing continues
- **API Timeout**: ❌ Error logged, environmental recording skipped, audio processing continues
- **Invalid Response**: ❌ Error logged, environmental recording skipped, audio processing continues

**Important**: Environmental data recording **never blocks** audio registration or processing. If weather data can't be fetched, the audio file is still registered and will be processed normally.

## Monitoring

### Check System Logs for Environmental Data

```sql
SELECT 
    level,
    message,
    hive_id,
    details,
    created_at
FROM system_logs
WHERE event_type = 'environmental_data'
ORDER BY created_at DESC
LIMIT 20;
```

### Verify Data Recording Rate

```sql
-- Count environmental records per hive (last 24 hours)
SELECT 
    h.hive_name,
    h.hive_id,
    COUNT(e.env_record_id) as records_last_24h,
    MAX(e.recorded_at) as last_recorded
FROM hives h
LEFT JOIN environmental_data e ON e.hive_id = h.hive_id 
    AND e.recorded_at > NOW() - INTERVAL '24 hours'
GROUP BY h.hive_id, h.hive_name
ORDER BY records_last_24h DESC;
```

### Check for Missing Coordinates

```sql
SELECT 
    hive_id, 
    hive_name, 
    hive_location,
    owner_id
FROM hives 
WHERE (latitude IS NULL OR longitude IS NULL)
  AND is_deleted = FALSE;
```

## Benefits

1. **Accurate Correlation**: Environmental data matches exact audio capture time
2. **Pattern Recognition**: Identify correlations between temperature/humidity and hive states
3. **Seasonal Insights**: Track environmental trends and bee behavior over time
4. **Research Data**: Build datasets for scientific analysis of bee behavior vs weather
5. **Predictive Analytics**: Use historical patterns to predict future hive states

## API Endpoints

### Test Weather API

```bash
GET /weather/test?latitude=0.3476&longitude=32.5825
```

Response:
```json
{
  "latitude": 0.3476,
  "longitude": 32.5825,
  "temperature": 24.5,
  "humidity": 65.2,
  "timestamp": "2026-06-08T14:30:00",
  "weather_description": "Partly cloudy"
}
```

### Get Hive Weather

```bash
GET /weather/hive/{hive_id}
Authorization: Bearer <token>
```

Response:
```json
{
  "hive_id": "123e4567-e89b-12d3-a456-426614174000",
  "hive_name": "Hive Alpha",
  "latitude": 0.3476,
  "longitude": 32.5825,
  "temperature": 24.5,
  "humidity": 65.2,
  "timestamp": "2026-06-08T14:30:00",
  "weather_description": "Partly cloudy"
}
```

## Future Enhancements

Potential additions to the environmental data system:

- ☁️ Additional weather metrics (atmospheric pressure, wind speed, precipitation)
- 📊 Historical weather data backfilling for existing audio records
- 🔔 Weather-based predictive alerts (e.g., "High swarm risk: temperature >30°C")
- 📈 Environmental trend analysis dashboard
- 🔄 Automatic retry logic with exponential backoff for failed API calls
- 💾 Weather data caching to reduce API calls and improve performance
- 🌍 Support for additional weather providers (WeatherAPI, Visual Crossing, etc.)

## Troubleshooting

### No Environmental Data Being Recorded

#### 1. Check hive coordinates
```sql
SELECT hive_id, hive_name, latitude, longitude 
FROM hives 
WHERE latitude IS NULL OR longitude IS NULL;
```

**Fix**: Update hive coordinates
```sql
UPDATE hives 
SET latitude = 0.3476, longitude = 32.5825 
WHERE hive_id = 'your-hive-id';
```

#### 2. Check system logs for errors
```sql
SELECT * FROM system_logs 
WHERE event_type = 'environmental_data' 
AND level IN ('warning', 'error')
ORDER BY created_at DESC 
LIMIT 10;
```

#### 3. Test weather service manually
```bash
curl "http://localhost:8000/weather/test?latitude=0.3476&longitude=32.5825"
```

If this fails:
- Check internet connectivity
- Verify DNS resolution
- Check firewall rules
- Test weather API directly

#### 4. Verify API configuration
If using OpenWeatherMap:
```bash
# Check if API key is set
grep OPENWEATHER_API_KEY .env

# Test API key directly
curl "https://api.openweathermap.org/data/2.5/weather?lat=0.3476&lon=32.5825&appid=YOUR_API_KEY"
```

### Weather API Rate Limits

- **Open-Meteo (default)**: No rate limits for reasonable use (~10,000 requests/day)
- **OpenWeatherMap Free Tier**: 
  - 60 calls/minute
  - 1,000,000 calls/month

If you hit rate limits:
- **Reduce polling frequency**: Increase `POLL_INTERVAL_SECONDS` in `.env`
- **Implement caching**: Cache weather data for 10-15 minutes per location
- **Upgrade plan**: Consider OpenWeatherMap paid tier
- **Switch providers**: Use Open-Meteo (default) which has higher limits

### Environmental Data Not Matching Audio Time

If you notice environmental data timestamps don't match audio capture times:

1. **Check system time synchronization**:
   ```bash
   timedatectl status
   ```

2. **Verify database timezone**:
   ```sql
   SHOW timezone;
   SELECT NOW();
   ```

3. **Check recorded_at timestamps**:
   ```sql
   SELECT 
       a.audio_id,
       a.ingestion_timestamp as audio_time,
       e.recorded_at as env_time,
       e.recorded_at - a.ingestion_timestamp as time_diff
   FROM audio_sources a
   JOIN environmental_data e ON e.hive_id = a.hive_id
   WHERE a.hive_id = 'your-hive-id'
   ORDER BY a.ingestion_timestamp DESC
   LIMIT 10;
   ```

Expected behavior: `time_diff` should be within 1-2 seconds.

## Summary

✅ **Environmental data is automatically recorded when audio is captured**  
✅ **No additional farmer action required**  
✅ **Works with both manual uploads and automatic polling**  
✅ **Resilient error handling - never blocks audio processing**  
✅ **Supports multiple weather API providers**  
✅ **Enables accurate correlation between weather and hive behavior**

For questions or issues, check the `system_logs` table or contact support.
