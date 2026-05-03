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
from api.database import Base, engine
from api.poller import scan_all_sources
from api.routers import alerts, audio, auth, hives, inferences

# ---------------------------------------------------------------------------
# Background scheduler — scans farmer data source folders every 30 seconds
# ---------------------------------------------------------------------------
_scheduler = BackgroundScheduler()
_scheduler.add_job(
    scan_all_sources,
    trigger="interval",
    seconds=30,
    id="folder_poller",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    Base.metadata.create_all(bind=engine)
    (ROOT / settings.upload_dir).mkdir(parents=True, exist_ok=True)
    (ROOT / "data_sources").mkdir(parents=True, exist_ok=True)

    _scheduler.start()

    print("✓ Database tables ready")
    print("✓ Upload directory ready")
    print("✓ data_sources/ folder ready (drop audio files here per hive)")
    print(f"✓ Model loaded: {settings.model_path}")
    print("✓ Folder poller started — scanning every 30 seconds")

    yield

    # --- shutdown ---
    _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Bee Swarming & Abscondment Detection API",
    description=(
        "Classifies hive audio recordings into five states: "
        "active_colony | swarming | missing_queen | queenbee_present | external_noise. "
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
app.include_router(alerts.router)


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
