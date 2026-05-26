# Automatic Hive Folder Creation Guide

## Overview

When a hive is created in BSADS, the system **automatically creates the corresponding folder** on the farmer's external server. This ensures the folder structure is ready for audio recordings.

## How It Works

### 1. Folder Structure

The farmer's server organizes recordings using this structure:
```
/home/farmer/recordings/
  └── <api_key>/
      └── <hive_name>/
          ├── hive1_2026-05-25_10-30.wav
          ├── hive1_2026-05-25_11-00.wav
          └── ...
```

### 2. Automatic Creation Process

When you create a hive via the BSADS API:

1. **BSADS receives the hive creation request** with hive details (name, location, etc.)
2. **BSADS creates the hive record** in its database
3. **BSADS determines the folder name**:
   - Uses `hive_name` if provided (e.g., "Hive 001")
   - Falls back to `hive_id` if no name is provided
4. **BSADS calls the farmer's server** via HTTP API:
   ```
   POST https://farmer-server.com/folders/Hive%20001
   Headers: X-API-Key: <your-api-key>
   ```
5. **Farmer's server creates the folder** at:
   ```
   /home/farmer/recordings/<api_key>/Hive 001/
   ```
6. **BSADS returns the suggested path** in the response:
   ```json
   {
     "hive_id": "...",
     "hive_name": "Hive 001",
     "suggested_remote_folder": "/home/farmer/recordings/<api_key>/Hive 001"
   }
   ```

### 3. Why Use an API Endpoint?

**You cannot create folders on a remote server via HTTP without an API endpoint.** This is a fundamental limitation of HTTP:

- ❌ **Not possible**: Direct filesystem access via HTTP
- ✅ **Correct approach**: API endpoint that creates folders server-side

The farmer's server provides the `/folders/{hive_folder}` endpoint specifically for this purpose.

## Implementation Details

### Farmer's Server Endpoint

**File**: `bsads_farmer_external_data_source_simulation/main.py`

```python
@app.post("/folders/{hive_folder}", status_code=201)
def create_hive_folder(hive_folder: str, x_api_key: str = Header(...)):
    """
    Create a hive folder for organizing recordings.
    Path: recordings/<api_key>/<hive_folder>/
    """
    api_key = _require_api_key(x_api_key)
    user_dir = _get_user_recordings_dir(api_key)
    hive_dir = user_dir / hive_folder
    
    # Security: Ensure the path is within the user's directory
    if not hive_dir.resolve().is_relative_to(user_dir.resolve()):
        raise HTTPException(status_code=403, detail="Invalid folder name")
    
    # Create the folder if it doesn't exist
    hive_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "folder_path": f"/home/farmer/recordings/{api_key}/{hive_folder}",
        "created": True
    }
```

### BSADS HTTP Connector

**File**: `bsads_backend_and_fast_api/api/http_connector.py`

```python
def create_hive_folder(config: dict, hive_folder: str) -> dict:
    """
    Create a hive folder on the farmer's server for organizing recordings.
    """
    base_url = config.get("api_base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    
    session = _build_session(api_key)
    response = session.post(
        f"{base_url}/folders/{hive_folder}",
        timeout=30
    )
    response.raise_for_status()
    
    return response.json()
```

### BSADS Hive Creation

**File**: `bsads_backend_and_fast_api/api/routers/hives.py`

```python
# Determine folder name: use hive_name if provided, otherwise use hive_id
folder_name = hive.hive_name if hive.hive_name else str(hive.hive_id)

# Auto-configure HTTP API data source if user has credentials
if current_user.server_url and current_user.api_key:
    api_config = {
        "api_base_url": current_user.server_url.rstrip("/"),
        "api_key": current_user.api_key,
        "hive_folder": folder_name,
    }
    
    # Test connection
    connection_test = test_connection(api_config)
    
    # Create the hive folder on the farmer's server
    if connection_test.get("ok"):
        try:
            create_hive_folder(api_config, folder_name)
        except Exception as e:
            # Log but don't fail - folder might already exist
            logger.warning(f"Could not create folder: {e}")
```

## Testing the Flow

### 1. Start Both Servers

**Terminal 1 - Farmer's Server**:
```bash
cd bsads_farmer_external_data_source_simulation
source venv/bin/activate
uvicorn main:app --reload --port 8001
```

**Terminal 2 - BSADS API**:
```bash
cd bsads_backend_and_fast_api
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

### 2. Register a User with Server Credentials

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "farmer1",
    "email": "farmer1@example.com",
    "password": "password123",
    "role": "farmer",
    "server_url": "http://localhost:8001",
    "api_key": "your-api-key-from-farmer-server"
  }'
```

### 3. Login to Get Token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "farmer1",
    "password": "password123"
  }'
```

### 4. Create a Hive

```bash
curl -X POST "http://localhost:8000/hives" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_name": "Hive 001",
    "hive_location": "Kampala",
    "hive_type": "Langstroth",
    "installation_date": "2026-05-25",
    "latitude": 0.332068,
    "longitude": 32.570436
  }'
```

**Expected Response**:
```json
{
  "hive_id": "814a8709-a39d-452a-a1fb-1d61c05f803c",
  "owner_id": "01117f89-2fbc-424c-9d44-bb4724c96979",
  "hive_name": "Hive 001",
  "hive_location": "Kampala",
  "hive_type": "Langstroth",
  "installation_date": "2026-05-25",
  "current_state": "unknown",
  "latitude": 0.332068,
  "longitude": 32.570436,
  "suggested_remote_folder": "/home/farmer/recordings/961424ec-94b1-4a00-b9a0-04d948ebd60c/Hive 001"
}
```

### 5. Verify Folder Creation

Check the farmer's server filesystem:
```bash
ls -la bsads_farmer_external_data_source_simulation/data/recordings/<api-key>/
```

You should see:
```
drwxr-xr-x  2 user user 4096 May 25 10:30 Hive 001/
```

## Troubleshooting

### Folder Not Created

**Symptom**: The hive is created but the folder doesn't exist on the farmer's server.

**Possible Causes**:
1. **Connection test failed**: Check if the farmer's server is running and accessible
2. **Invalid API key**: Verify the API key is correct
3. **Permission issues**: Ensure the farmer's server has write permissions

**Check Logs**:
```bash
# BSADS logs will show warnings if folder creation fails
tail -f bsads_backend_and_fast_api/logs/app.log
```

### Wrong Folder Name

**Symptom**: Folder is created with hive_id instead of hive_name.

**Cause**: No `hive_name` was provided during hive creation.

**Solution**: Always provide `hive_name` when creating hives:
```json
{
  "hive_name": "Hive 001",  // ← Include this
  "hive_location": "Kampala",
  ...
}
```

### Folder Already Exists

**Symptom**: Error message about folder already existing.

**Cause**: The folder was created in a previous attempt.

**Solution**: This is not an error - the endpoint uses `mkdir(exist_ok=True)` so it's safe to call multiple times.

## Security Considerations

1. **Path Traversal Protection**: The farmer's server validates that the folder path is within the user's directory
2. **API Key Authentication**: All folder creation requests require a valid API key
3. **User Isolation**: Each user's recordings are stored in their own `<api_key>` folder

## Summary

✅ **Automatic**: Folders are created automatically when hives are created  
✅ **Secure**: API key authentication and path validation  
✅ **Human-readable**: Uses hive names instead of UUIDs  
✅ **Organized**: Clear folder structure by user and hive  
✅ **Reliable**: Handles existing folders gracefully  

The system uses HTTP API endpoints because **direct filesystem access is not possible via HTTP**. This is the standard, secure way to manage remote folders.
