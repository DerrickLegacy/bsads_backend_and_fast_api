# BSADS FastAPI — Consumer Guide

**Bee Swarming & Abscondment Detection System**
How to connect to, authenticate with, and consume this API from any client.

---

## Table of Contents

1. [Domain URL — Where to Access the API](#1-domain-url--where-to-access-the-api)
2. [Sessions — Does the API Remember You?](#2-sessions--does-the-api-remember-you)
3. [CORS — Can Your Frontend Call This API?](#3-cors--can-your-frontend-call-this-api)
4. [Security Model — How Auth and Roles Work](#4-security-model--how-auth-and-roles-work)
5. [Authentication Flow — Step by Step](#5-authentication-flow--step-by-step)
6. [All Endpoints at a Glance](#6-all-endpoints-at-a-glance)
7. [Full Request / Response Examples](#7-full-request--response-examples)
8. [Flutter / Dart Usage Examples](#8-flutter--dart-usage-examples)
9. [Error Reference](#9-error-reference)
10. [Quick Reference Card](#10-quick-reference-card)

---

## 1. Domain URL — Where to Access the API

| Environment | Base URL |
|---|---|
| **Local development** | `http://localhost:8000` |
| **Interactive docs (Swagger UI)** | `http://localhost:8000/docs` |
| **Alternative docs (ReDoc)** | `http://localhost:8000/redoc` |
| **OpenAPI JSON schema** | `http://localhost:8000/openapi.json` |
| **Health check** | `http://localhost:8000/health` |

Start the server locally with:
```bash
cd bsads_backend_and_fast_api
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

To make the server reachable on your local network (e.g., from a phone on the same Wi-Fi):
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
# Then use your machine's local IP, e.g.: http://192.168.x.x:8000
```

---

## 2. Sessions — Does the API Remember You?

**No. The API is completely stateless — it does not maintain server-side sessions.**

There is no session table, no cookies, no server memory between requests. Every request is independent.

Instead, the API uses **JWT (JSON Web Tokens)**:

```
┌──────────────┐      POST /auth/login       ┌──────────────┐
│  Your App    │  ─────────────────────────► │  FastAPI     │
│              │  { email, password }         │              │
│              │  ◄──────────────────────── │              │
│              │  { access_token: "eyJ..." } │              │
└──────────────┘                             └──────────────┘

On every future request:
┌──────────────┐   GET /hives                ┌──────────────┐
│  Your App    │   Authorization: Bearer eyJ │  FastAPI     │
│              │  ─────────────────────────► │              │
│              │  ◄──────────────────────── │   decodes    │
│              │  { hive list... }           │   the JWT,   │
└──────────────┘                             │   finds user │
                                             └──────────────┘
```

**What the JWT contains:**
- `sub` — the `user_id` (UUID) of the logged-in user
- `exp` — expiry timestamp (24 hours from login)

**Your app's responsibility:**
- Store the token after login (e.g., `SharedPreferences`, `SecureStorage`, `AsyncStorage`)
- Attach it to every request as `Authorization: Bearer <token>`
- When you receive a `401` response, the token has expired — call `/auth/login` again to get a new one

**Token lifetime:** 24 hours (1440 minutes, set via `ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`)

---

## 3. CORS — Can Your Frontend Call This API?

**Yes — CORS is fully open in the current configuration.**

The API is configured with:

```python
# From api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # any domain can call this API
    allow_credentials=True,    # Authorization headers are allowed
    allow_methods=["*"],       # GET, POST, PUT, PATCH, DELETE — all allowed
    allow_headers=["*"],       # Content-Type, Authorization — all allowed
)
```

**What this means for you:**

| Client type | Can it call the API? |
|---|---|
| Flutter mobile app | Yes |
| React / Vue / Angular web app | Yes |
| Postman / Insomnia | Yes |
| curl from terminal | Yes |
| Any other HTTP client | Yes |

**Preflight requests (OPTIONS):** The middleware automatically handles browser preflight requests. You do not need to do anything special.

**In production:** The `allow_origins=["*"]` should be tightened to only your app's domain:
```python
allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
```

---

## 4. Security Model — How Auth and Roles Work

### Password Security

Passwords are **never stored in plain text**. When you register, your password is immediately hashed with bcrypt before being saved:

```
"mypassword123"  →  bcrypt hash  →  "$2b$12$abc...xyz"  (stored in DB)
```

On login, bcrypt compares the plain password against the stored hash. The original password is never recoverable.

### JWT Security

- **Algorithm:** HS256 (HMAC-SHA256)
- **Signing key:** `SECRET_KEY` from the `.env` file — must be kept secret
- **Expiry:** 24 hours
- If someone tampers with a token, the signature check fails → `401 Unauthorized`
- If a token has expired, the expiry check fails → `401 Unauthorized`

### Role-Based Access Control

Every user has a `role` field. There are two roles:

| Role | Access |
|---|---|
| `farmer` | Can only see and manage their own hives, audio, inferences, and alerts |
| `admin` | Can see and manage all data system-wide; access to `/users` management endpoints |

**Data isolation:** A farmer can never see another farmer's data. Every database query for hives/alerts/inferences is automatically filtered by `owner_id == current_user.user_id`.

### How Protected Endpoints Work

Any endpoint that requires login uses `Depends(get_current_user)`. This dependency:
1. Reads the `Authorization: Bearer <token>` header
2. Decodes and validates the JWT
3. Loads the full `User` object from the database
4. Returns the user object — or raises `401 Unauthorized`

Endpoints that also require `admin` additionally check `current_user.role != "admin"` and raise `403 Forbidden`.

---

## 5. Authentication Flow — Step by Step

### Register (first time)

```
POST /auth/register
Content-Type: application/json

{
  "full_name": "Derrick Ahaabwe",
  "email": "derrick@bees.ug",
  "password": "mypassword123",
  "phone": "+256700000000",
  "address": "Kampala, Uganda",
  "role": "farmer"
}
```

**Response `201 Created`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "3e4f5a6b-...",
    "full_name": "Derrick Ahaabwe",
    "email": "derrick@bees.ug",
    "role": "farmer",
    "created_at": "2026-05-09T10:00:00"
  }
}
```

Save the `access_token`. You are already logged in.

---

### Login (returning user)

```
POST /auth/login
Content-Type: application/json

{
  "email": "derrick@bees.ug",
  "password": "mypassword123"
}
```

**Response `200 OK`:** Same structure as register above.

---

### Using the token on every request

Add this header to every protected request:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### Get your own profile

```
GET /auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "3e4f5a6b-...",
  "full_name": "Derrick Ahaabwe",
  "email": "derrick@bees.ug",
  "role": "farmer",
  "created_at": "2026-05-09T10:00:00"
}
```

---

### Update your profile

```
PUT /auth/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "Derrick A. Ahaabwe",
  "phone": "+256711111111",
  "address": "Entebbe, Uganda"
}
```

---

### Change your password

```
PUT /auth/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "mypassword123",
  "new_password": "newstrongerpassword456"
}
```

**Response `200 OK`:**
```json
{ "detail": "Password updated successfully" }
```

---

## 6. All Endpoints at a Glance

**Legend:** 🔓 No auth required | 🔑 JWT required | 👑 Admin role required

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | 🔓 | API status and version |
| GET | `/health` | 🔓 | Health check |

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | 🔓 | Create farmer account, returns token |
| POST | `/auth/login` | 🔓 | Login, returns token |
| GET | `/auth/me` | 🔑 | Get own profile |
| PUT | `/auth/me` | 🔑 | Update own profile (name, phone, address) |
| PUT | `/auth/password` | 🔑 | Change own password |

### Hives

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/hives` | 🔑 | Register a new hive |
| GET | `/hives` | 🔑 | List my hives (admin: all hives). Optional `?search=` |
| GET | `/hives/{hive_id}` | 🔑 | Hive detail with latest alert + env metrics |
| PUT | `/hives/{hive_id}` | 🔑 | Update hive fields |
| DELETE | `/hives/{hive_id}` | 🔑 | Delete a hive |
| POST | `/hives/{hive_id}/acknowledge` | 🔑 | Acknowledge latest pending alert for the hive |

### Audio

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/audio/upload` | 🔑 | Upload WAV/MP3/FLAC — inference runs in background, returns 202 |

### Inference Results

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/hives/{hive_id}/inferences` | 🔑 | Last 20 inference results for a hive |
| GET | `/hives/{hive_id}/inferences/latest` | 🔑 | Most recent result only — poll here after upload |
| GET | `/inferences` | 🔑 | All inferences (admin: all; farmer: own hives). Optional `?hive_id=&limit=` |
| GET | `/inferences/{inference_id}` | 🔑 | Single inference result by ID |

### Alerts

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/hives/{hive_id}/alerts` | 🔑 | Pending alerts for a hive. `?only_pending=false` for all |
| PATCH | `/hives/{hive_id}/alerts/{alert_id}/acknowledge` | 🔑 | Mark a specific alert acknowledged |

### Mobile Alerts (top-level, used by mobile app)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/alerts` | 🔑 | All alerts for my hives. Optional `?hive_id=` |
| GET | `/alerts/{alert_id}` | 🔑 | Alert detail |
| POST | `/alerts/{alert_id}/acknowledge` | 🔑 | Acknowledge an alert |
| PATCH | `/alerts/{alert_id}/notify` | 👑 | Mark alert as sent (admin only) |

### Advisories

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/advisories` | 🔑 | All advisories (admin: all; farmer: own). Optional `?hive_id=&limit=` |
| GET | `/advisories/{advisory_id}` | 🔑 | Single advisory detail |

### Dashboard

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/dashboard` | 🔑 | Summary stats for mobile home screen |

### Data Sources (SSH / Folder config)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/hives/{hive_id}/data-source` | 🔑 | Get data source config for a hive |
| POST | `/hives/{hive_id}/data-source/configure` | 🔑 | Configure SSH remote audio source |

### Advisory Templates (Admin panel)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/advisory-templates` | 🔑 | List all templates (any logged-in user) |
| POST | `/advisory-templates` | 👑 | Create a new template |
| PUT | `/advisory-templates/{template_id}` | 👑 | Update a template |
| DELETE | `/advisory-templates/{template_id}` | 👑 | Delete a template |

### User Management (Admin only)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users` | 👑 | List all users. Optional `?role=farmer\|admin` |
| POST | `/users` | 👑 | Create a user account |
| GET | `/users/{user_id}` | 👑 | Get one user |
| PUT | `/users/{user_id}` | 👑 | Update user fields |
| DELETE | `/users/{user_id}` | 👑 | Delete a user |

---

## 7. Full Request / Response Examples

### Register a hive

```
POST /hives
Authorization: Bearer <token>
Content-Type: application/json

{
  "hive_name": "Hive Alpha",
  "hive_location": "Kampala, Nakawa",
  "hive_type": "Langstroth",
  "installation_date": "2026-01-15",
  "latitude": 0.3476,
  "longitude": 32.5825
}
```

**Response `201 Created`:**
```json
{
  "hive_id": "7c8d9e0f-...",
  "owner_id": "3e4f5a6b-...",
  "hive_name": "Hive Alpha",
  "hive_location": "Kampala, Nakawa",
  "hive_type": "Langstroth",
  "installation_date": "2026-01-15",
  "current_state": "unknown",
  "latitude": 0.3476,
  "longitude": 32.5825,
  "suggested_remote_folder": "farmer_3e4f5a6b-.../hive_7c8d9e0f-..."
}
```

`suggested_remote_folder` is the path to create on the farmer's external audio server if using SSH-based audio ingestion.

---

### Upload audio for inference

```
POST /audio/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@hive_recording.wav
hive_id=7c8d9e0f-...
```

**Response `202 Accepted` (immediate — inference runs in background):**
```json
{
  "audio_id": "1a2b3c4d-...",
  "hive_id": "7c8d9e0f-...",
  "message": "File received. Inference is running in the background."
}
```

Accepted audio formats: `.wav`, `.mp3`, `.flac`

---

### Poll for the inference result

Call this every 2–3 seconds after uploading audio:

```
GET /hives/7c8d9e0f-.../inferences/latest
Authorization: Bearer <token>
```

**Normal hive — no alert:**
```json
{
  "inference_id": "a1b2c3d4-...",
  "hive_id": "7c8d9e0f-...",
  "hive_state": "active_colony",
  "confidence_score": 0.9966,
  "inference_latency_ms": 2341,
  "created_at": "2026-05-09T10:05:23",
  "alert": null,
  "advisory": null
}
```

**Swarming detected — with alert and advisory:**
```json
{
  "inference_id": "a1b2c3d4-...",
  "hive_id": "7c8d9e0f-...",
  "hive_state": "swarming",
  "confidence_score": 0.9830,
  "inference_latency_ms": 2105,
  "created_at": "2026-05-09T10:05:23",
  "alert": {
    "alert_id": "x1y2z3a4-...",
    "hive_id": "7c8d9e0f-...",
    "severity_level": "High",
    "recommended_action": "Immediate hive inspection required — swarm event detected",
    "action_status": "pending",
    "alert_timestamp": "2026-05-09T10:05:24"
  },
  "advisory": {
    "advisory_id": "p1q2r3s4-...",
    "advisory_type": "Reactive",
    "condition_label": "Swarming Detected",
    "advisory_text": "Your hive is showing swarming behaviour...",
    "severity": "High",
    "actions": [
      {
        "action_id": "a1-...",
        "action_description": "Inspect the hive immediately to confirm swarming activity",
        "priority_level": "High",
        "status": "pending"
      },
      {
        "action_id": "a2-...",
        "action_description": "Prepare a swarm trap or empty hive box nearby",
        "priority_level": "High",
        "status": "pending"
      },
      {
        "action_id": "a3-...",
        "action_description": "Remove or destroy swarm cells to prevent secondary swarms",
        "priority_level": "Medium",
        "status": "pending"
      }
    ]
  }
}
```

**Possible `hive_state` values:**

| Value | Meaning | Alert generated? |
|---|---|---|
| `active_colony` | Healthy, active hive | No |
| `queenbee_present` | Queen detected | No |
| `swarming` | Swarm event — urgent | Yes (High) |
| `missing_queen` | Queen absent | Yes (Medium) |
| `pest_infested` | Pest activity detected | Yes |
| `external_noise` | Recording noise — low confidence | No |
| `unknown` | Not yet analysed | No |

---

### Get the dashboard summary

```
GET /dashboard
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_hives": 3,
  "active_hives": 2,
  "status_counts": {
    "normal": 2,
    "pre_swarm": 0,
    "swarm": 1,
    "abscondment": 0,
    "other": 0
  },
  "key_metrics": {
    "temperature_c": 34.5,
    "humidity_percent": 62.3,
    "population_k_bees": 15.2,
    "nectar_flow_kg_per_day": 0.8
  }
}
```

---

### Get all my alerts (mobile screen)

```
GET /alerts
Authorization: Bearer <token>
```

Optional filter by hive: `GET /alerts?hive_id=7c8d9e0f-...`

**Response:**
```json
[
  {
    "id": "x1y2z3a4-...",
    "hive_id": "7c8d9e0f-...",
    "severity": "High",
    "title": "Swarming Detected",
    "date": "2026-05-09T10:05:24",
    "summary": "Immediate hive inspection required"
  }
]
```

---

### Acknowledge an alert

```
POST /alerts/x1y2z3a4-.../acknowledge
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "x1y2z3a4-...",
  "hive_id": "7c8d9e0f-...",
  "severity": "High",
  "title": "Swarming Detected",
  "time": "2026-05-09T10:05:24",
  "details": "Your hive is showing swarming behaviour...",
  "acknowledged": true
}
```

---

### Get hive detail (mobile hive screen)

```
GET /hives/7c8d9e0f-...
Authorization: Bearer <token>
```

**Response:**
```json
{
  "hive_id": "7c8d9e0f-...",
  "owner_id": "3e4f5a6b-...",
  "hive_name": "Hive Alpha",
  "hive_location": "Kampala, Nakawa",
  "hive_type": "Langstroth",
  "installation_date": "2026-01-15",
  "current_state": "swarming",
  "latitude": 0.3476,
  "longitude": 32.5825,
  "alert_title": "Swarming Detected",
  "alert_message": "Your hive is showing swarming behaviour...",
  "acknowledged": false,
  "metric_series": [
    { "time_label": "08:00", "temperature_c": 33.5, "humidity_percent": 61.0 },
    { "time_label": "09:00", "temperature_c": 34.1, "humidity_percent": 62.3 },
    { "time_label": "10:00", "temperature_c": 34.5, "humidity_percent": 63.1 }
  ]
}
```

`metric_series` contains the last 7 environmental readings — ready to render as a chart.

---

## 8. Flutter / Dart Usage Examples

### Store and retrieve the token

```dart
import 'package:shared_preferences/shared_preferences.dart';

// Save token after login
Future<void> saveToken(String token) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('auth_token', token);
}

// Load token for requests
Future<String?> getToken() async {
  final prefs = await SharedPreferences.getInstance();
  return prefs.getString('auth_token');
}
```

### Login

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

const String baseUrl = 'http://localhost:8000';

Future<Map<String, dynamic>> login(String email, String password) async {
  final response = await http.post(
    Uri.parse('$baseUrl/auth/login'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'email': email, 'password': password}),
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    await saveToken(data['access_token']);
    return data;
  } else {
    throw Exception('Login failed: ${response.body}');
  }
}
```

### Authenticated GET request

```dart
Future<Map<String, dynamic>> getLatestInference(String hiveId) async {
  final token = await getToken();
  final response = await http.get(
    Uri.parse('$baseUrl/hives/$hiveId/inferences/latest'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  );

  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  } else if (response.statusCode == 401) {
    // Token expired — redirect to login screen
    throw Exception('Session expired — please log in again');
  } else {
    throw Exception('Request failed: ${response.body}');
  }
}
```

### Upload audio file

```dart
import 'dart:io';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> uploadAudio(String hiveId, File audioFile) async {
  final token = await getToken();
  final uri = Uri.parse('$baseUrl/audio/upload');

  final request = http.MultipartRequest('POST', uri)
    ..headers['Authorization'] = 'Bearer $token'
    ..fields['hive_id'] = hiveId
    ..files.add(await http.MultipartFile.fromPath('file', audioFile.path));

  final streamedResponse = await request.send();
  final response = await http.Response.fromStream(streamedResponse);

  if (response.statusCode == 202) {
    return jsonDecode(response.body);
    // { audio_id: "...", message: "File received. Inference is running..." }
  } else {
    throw Exception('Upload failed: ${response.body}');
  }
}
```

### Poll for inference result after upload

```dart
Future<Map<String, dynamic>> pollForInference(String hiveId) async {
  for (int attempt = 0; attempt < 15; attempt++) {
    await Future.delayed(const Duration(seconds: 3));

    final result = await getLatestInference(hiveId);
    if (result['hive_state'] != 'unknown') {
      return result; // inference is complete
    }
  }
  throw Exception('Inference timed out after 45 seconds');
}
```

---

## 9. Error Reference

| HTTP Status | Meaning | Common cause |
|---|---|---|
| `400 Bad Request` | Invalid request body | Missing required field, email already registered, wrong password |
| `401 Unauthorized` | Not logged in or token expired | Missing or invalid `Authorization` header |
| `403 Forbidden` | Logged in but not allowed | Farmer trying to access another farmer's data, or admin-only endpoint |
| `404 Not Found` | Resource does not exist | Wrong `hive_id`, `alert_id`, or the item belongs to another user |
| `422 Unprocessable Entity` | Request schema validation failed | Wrong data type, missing required field in JSON body |
| `500 Internal Server Error` | Something crashed server-side | Check the server logs |

**Error response body format:**
```json
{
  "detail": "Human-readable message explaining what went wrong"
}
```

---

## 10. Quick Reference Card

```
Base URL          http://localhost:8000
Interactive docs  http://localhost:8000/docs
ReDoc             http://localhost:8000/redoc

Sessions?         No — stateless JWT, 24-hour tokens
CORS?             Yes — all origins allowed (allow_origins=["*"])
Auth header       Authorization: Bearer <your_token>

Register          POST  /auth/register        (no auth)
Login             POST  /auth/login           (no auth)
My profile        GET   /auth/me
Update profile    PUT   /auth/me
Change password   PUT   /auth/password

List my hives     GET   /hives
Create hive       POST  /hives
Hive detail       GET   /hives/{hive_id}
Update hive       PUT   /hives/{hive_id}
Delete hive       DELETE /hives/{hive_id}

Upload audio      POST  /audio/upload         (multipart: file + hive_id)
Latest inference  GET   /hives/{hive_id}/inferences/latest
All inferences    GET   /hives/{hive_id}/inferences

All my alerts     GET   /alerts
Alert detail      GET   /alerts/{alert_id}
Acknowledge       POST  /alerts/{alert_id}/acknowledge

Dashboard         GET   /dashboard

Health check      GET   /health               (no auth)
```
