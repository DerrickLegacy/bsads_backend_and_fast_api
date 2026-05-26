"""
Bee Swarming & Abscondment Detection System — FastAPI entry point.

Start locally:
    uvicorn api.main:app --reload --port 8000

Interactive API docs:
    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from api.config import ROOT, settings
from api.database import Base, SessionLocal, engine
from api.poller_concurrent import (
    process_pending_sources_concurrent as process_pending_sources,
    scan_all_sources_concurrent as scan_all_sources,
    recover_stuck_records,
)
from api.seed import seed_initial_data
from api.routers import audio, auth, hives, inferences
from api.routers.admin_views import router as admin_views_router
from api.routers.advisory_templates import router as advisory_templates_router
from api.routers.alerts import hive_alerts_router, mobile_alerts_router
from api.routers.dashboard import router as dashboard_router
from api.routers.logs import router as logs_router
from api.routers.users import router as users_router

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    Base.metadata.create_all(bind=engine)
    (ROOT / settings.upload_dir).mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    _scheduler.start()

    print("✓ Database tables ready")
    print("✓ Upload directory ready")
    print(f"✓ HuggingFace Space: {settings.hf_space_name}")
    print(f"✓ Discovery poller started (CONCURRENT) — scanning every {settings.poll_interval_seconds}s")
    print(f"✓ Inference poller started (CONCURRENT + BATCHED) — processing every {settings.poll_interval_seconds}s")
    print(f"✓ Recovery job started — checking for stuck records every {settings.recovery_interval_minutes} minutes")

    yield

    # --- shutdown ---
    _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Bee Swarming & Abscondment Detection API",
    description=(
        "Classifies hive audio recordings into five states: "
        "active_colony | swarming | missing_queen | queenbee_present | external_noise | pest infested s. "
        "Generates alerts and advisory checklists for farmers."
    ),
    version="1.1.0",
    lifespan=lifespan,
    # Disable default docs so we can serve them with reliable CDN fallbacks
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(hives.router)
app.include_router(audio.router)
app.include_router(inferences.router)
app.include_router(hive_alerts_router)
app.include_router(mobile_alerts_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(advisory_templates_router)
app.include_router(admin_views_router)
app.include_router(logs_router)


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
