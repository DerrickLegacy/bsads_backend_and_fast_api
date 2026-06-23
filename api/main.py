"""
Bee Swarming & Abscondment Detection System — FastAPI entry point.

Start locally:
    uvicorn api.main:app --reload --port 8000

Interactive API docs:
    http://localhost:8000/docs
"""

from api.routers.weather import router as weather_router
from api.routers.users import router as users_router
from api.routers.logs import router as logs_router
from api.routers.dashboard import router as dashboard_router
from api.routers.audio_stream import router as audio_stream_router
from api.routers.alerts import hive_alerts_router, mobile_alerts_router
from api.routers.advisory_actions import router as advisory_actions_router
from api.routers.advisory_library import router as advisory_library_router
from api.routers.advisory_templates import router as advisory_templates_router
from api.routers.admin_views import router as admin_views_router
from api.routers.admin_keys import router as admin_keys_router
from api.routers.notifications import router as notifications_router
from api.routers.device_upload import router as device_upload_router
from api.routers import audio, auth, hives, inferences
from api.seed import seed_initial_data
from api.poller_concurrent import (
    process_pending_sources_concurrent as process_pending_sources,
    scan_all_sources_concurrent as scan_all_sources,
    recover_stuck_records,
)
from api.conditions_poller import poll_and_process_conditions
from api.queen_absence_watcher import check_queen_absence
from api.database import Base, SessionLocal, engine
import logging
import sys
import traceback
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from api.config import ROOT, settings

# ---------------------------------------------------------------------------
# Enhanced logging configuration for production visibility
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bsads")

# ---------------------------------------------------------------------------
# Background scheduler — scans farmer data source folders concurrently
# ---------------------------------------------------------------------------
_scheduler = BackgroundScheduler()

# Job 1 — discover new files via HTTP API, register as pending (CONCURRENT)
_scheduler.add_job(
    scan_all_sources,
    trigger="interval",
    seconds=settings.poll_interval_seconds,
    id="discovery_poller",
    replace_existing=True,
    max_instances=1,  # Prevent overlapping executions
    coalesce=True,    # If multiple runs are pending, combine them into one
)

# Job 2 — pick up pending records, fetch bytes, call HuggingFace Inference API (CONCURRENT + BATCHED)
_scheduler.add_job(
    process_pending_sources,
    trigger="interval",
    seconds=settings.poll_interval_seconds,
    start_date=f"2000-01-01 00:00:{settings.poll_offset_seconds:02d}",
    id="inference_poller",
    replace_existing=True,
    max_instances=1,  # Prevent overlapping executions
    coalesce=True,    # If multiple runs are pending, combine them into one
)

# Job 3 — recover stuck 'processing' records (runs every 5 minutes)
_scheduler.add_job(
    recover_stuck_records,
    trigger="interval",
    minutes=settings.recovery_interval_minutes,
    id="recovery_job",
    replace_existing=True,
    max_instances=1,
)

# Job 4 — poll and process CSV condition data (runs every 2 minutes)
_scheduler.add_job(
    poll_and_process_conditions,
    trigger="interval",
    minutes=2,
    id="conditions_poller",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
)

# Job 5 — queen absence watcher (runs every 6 hours)
# Raises an alert if no queenbee_present inference in the last 48 hours
_scheduler.add_job(
    check_queen_absence,
    trigger="interval",
    hours=6,
    id="queen_absence_watcher",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    logger.info("=" * 60)
    logger.info("🐝 BSADS API Starting Up...")
    logger.info("=" * 60)

    # Check if database reset is enabled
    if settings.reset_database:
        from api.db_reset import reset_database
        reset_database()
    else:
        # Normal startup - create tables if they don't exist
        Base.metadata.create_all(bind=engine)

        # Seed initial data
        db = SessionLocal()
        try:
            logger.info("Seeding initial data...")
            seed_initial_data(db)
            logger.info("✓ Initial data seeded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to seed data: {e}")
            logger.info(
                "💡 Tip: Set RESET_DATABASE=true in .env to drop and recreate all tables")
            raise
        finally:
            db.close()

    (ROOT / settings.upload_dir).mkdir(parents=True, exist_ok=True)

    _scheduler.start()

    logger.info("✓ Database tables ready")
    logger.info("✓ Upload directory ready")
    logger.info(f"✓ HuggingFace Space: {settings.hf_space_name}")
    logger.info(
        f"✓ Discovery poller started (CONCURRENT) — scanning every {settings.poll_interval_seconds}s")
    logger.info(
        f"✓ Inference poller started (CONCURRENT + BATCHED) — processing every {settings.poll_interval_seconds}s")
    logger.info(
        f"✓ Recovery job started — checking for stuck records every {settings.recovery_interval_minutes} minutes")
    logger.info("=" * 60)
    logger.info("🚀 BSADS API Ready!")
    logger.info("=" * 60)

    yield

    # --- shutdown ---
    logger.info("Shutting down background scheduler...")
    _scheduler.shutdown(wait=False)
    logger.info("✓ Shutdown complete")

app = FastAPI(
    title="Bee Swarming & Abscondment Detection API",
    description=(
        "Classifies hive audio recordings into five states: "
        "active_colony | swarming | missing_queen | queenbee_present | external_noise | pest infested s. "
        "Generates alerts and advisory checklists for farmers."
    ),
    version="1.1.0",
    lifespan=lifespan,
    root_path="/bsads-api-db",
    # Disable default docs so we can serve them with reliable CDN fallbacks
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_logger = logging.getLogger("bsads.api")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, exc: IntegrityError):
    """Map unique-constraint violations to 400 instead of opaque 500."""
    orig = getattr(exc, "orig", None)
    detail = str(orig) if orig else str(exc)
    if "email" in detail.lower():
        msg = "Email already registered"
    elif "phone" in detail.lower():
        msg = "Phone number already registered"
    else:
        msg = "A record with these details already exists"
    logger.warning(
        f"IntegrityError on {_request.method} {_request.url.path}: {detail}")
    return JSONResponse(status_code=400, content={"detail": msg})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    """Log full trace server-side; return message in JSON for debugging."""
    logger.exception(
        f"Unhandled error on {_request.method} {_request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "path": _request.url.path,
        },
    )


# Log incoming requests for production debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(
        f"← {request.method} {request.url.path} - {response.status_code}")
    return response


app.include_router(auth.router)
app.include_router(hives.router)
app.include_router(audio.router)
app.include_router(audio_stream_router)
app.include_router(inferences.router)
app.include_router(hive_alerts_router)
app.include_router(mobile_alerts_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(advisory_templates_router)
app.include_router(advisory_library_router)
app.include_router(advisory_actions_router)
app.include_router(admin_views_router)
app.include_router(admin_keys_router)
app.include_router(device_upload_router)
app.include_router(logs_router)
app.include_router(weather_router)
app.include_router(notifications_router)
app.include_router(admin_keys_router)
app.include_router(logs_router)
app.include_router(weather_router)
app.include_router(notifications_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "BSADS API"}


@app.get("/", tags=["Health"])
def health():
    return {
        "status": "ok",
        "service": "BSADS API v1.1.0",
        "docs": "http://localhost:8000/docs",
        "redoc": "http://localhost:8000/redoc",
    }


# ---------------------------------------------------------------------------
# Self-hosted interactive docs — no CDN required, works offline
# Swagger UI assets are served directly by FastAPI from unpkg CDN with
# a fallback version pinned so it never breaks on CDN changes.
# ---------------------------------------------------------------------------
@app.get("/docs", include_in_schema=False)
async def swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="BSADS API — Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_ui() -> HTMLResponse:
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="BSADS API — ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    )
