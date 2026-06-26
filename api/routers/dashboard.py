from datetime import datetime, timedelta

from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from api.database import get_db
from api.models import Alert, AudioSource, EnvironmentalData, Hive, User
from api.routers.auth import get_current_user
from api.schemas import (
    DashboardKeyMetrics,
    DashboardResponse,
    DashboardSilentHive,
    DashboardStatusCounts,
)

router = APIRouter(tags=["Dashboard"])

_ACTIVE_STATES = {"normal", "pre_swarm", "swarm",
                  "missing_queen", "queenbee_present", "pest_infested"}


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summary statistics for the logged-in farmer's dashboard screen."""
    hives = db.query(Hive).filter(
        Hive.owner_id == current_user.user_id,
        Hive.is_deleted == False,
    ).all()

    total_hives = len(hives)
    active_hives = sum(1 for h in hives if h.current_state in _ACTIVE_STATES)
    hive_ids = [h.hive_id for h in hives]

    # ── State counts from hive.current_state ─────────────────────────────
    counts = DashboardStatusCounts()
    for h in hives:
        state = h.current_state or "unknown"
        if state == "normal":
            counts.normal += 1
        elif state == "pre_swarm":
            counts.pre_swarm += 1
        elif state == "swarm":
            counts.swarm += 1
        elif state == "abscondment":
            counts.abscondment += 1
        elif state == "missing_queen":
            counts.missing_queen += 1
        elif state == "queenbee_present":
            counts.queenbee_present += 1
        elif state == "pest_infested":
            counts.pest_infested += 1
        elif state == "external_noise":
            counts.external_noise += 1
        elif state == "uncertain":
            counts.uncertain += 1
        else:
            counts.other += 1

    # ── Key metrics (avg of latest env reading per hive) ─────────────────
    metrics = DashboardKeyMetrics()
    if hive_ids:
        latest_per_hive = (
            db.query(
                EnvironmentalData.hive_id,
                func.max(EnvironmentalData.recorded_at).label("latest"),
            )
            .filter(EnvironmentalData.hive_id.in_(hive_ids))
            .group_by(EnvironmentalData.hive_id)
            .subquery()
        )
        env_records = (
            db.query(EnvironmentalData)
            .join(
                latest_per_hive,
                and_(
                    EnvironmentalData.hive_id == latest_per_hive.c.hive_id,
                    EnvironmentalData.recorded_at == latest_per_hive.c.latest,
                ),
            )
            .all()
        )

        def _avg(vals):
            filtered = [v for v in vals if v is not None]
            return round(sum(filtered) / len(filtered), 2) if filtered else None

        metrics = DashboardKeyMetrics(
            temperature_c=_avg(
                [float(r.temperature) if r.temperature else None for r in env_records]),
            humidity_percent=_avg(
                [float(r.humidity) if r.humidity else None for r in env_records]),
        )

    # ── Pending alerts count ──────────────────────────────────────────────
    pending_alerts = 0
    if hive_ids:
        pending_alerts = (
            db.query(func.count(Alert.alert_id))
            .filter(Alert.hive_id.in_(hive_ids), Alert.action_status == "pending")
            .scalar() or 0
        )

    # ── Recordings today ─────────────────────────────────────────────────
    # Use AT TIME ZONE 'Africa/Kampala' (EAT = UTC+3) so "today" matches
    # the farmer's local calendar day, not the server's UTC day.
    recordings_today = 0
    if hive_ids:
        recordings_today = (
            db.query(func.count(AudioSource.audio_id))
            .filter(
                AudioSource.hive_id.in_(hive_ids),
                func.date(
                    func.timezone("Africa/Kampala", AudioSource.ingestion_timestamp)
                ) == func.current_date(),
            )
            .scalar() or 0
        )

    # ── Silent hives (no audio received in the last 4 hours) ─────────────
    silent_hives: list[DashboardSilentHive] = []
    if hive_ids:
        four_hours_ago = datetime.utcnow() - timedelta(hours=4)

        # Latest ingestion timestamp per hive (NULL = never received audio)
        latest_audio_subq = (
            db.query(
                AudioSource.hive_id,
                func.max(AudioSource.ingestion_timestamp).label("last_audio_at"),
            )
            .filter(AudioSource.hive_id.in_(hive_ids))
            .group_by(AudioSource.hive_id)
            .subquery()
        )

        rows = (
            db.query(Hive, latest_audio_subq.c.last_audio_at)
            .outerjoin(
                latest_audio_subq,
                Hive.hive_id == latest_audio_subq.c.hive_id,
            )
            .filter(Hive.hive_id.in_(hive_ids))
            .all()
        )

        for hive, last_audio_at in rows:
            if last_audio_at is None or last_audio_at < four_hours_ago:
                hours_silent = None
                if last_audio_at is not None:
                    diff = datetime.utcnow() - last_audio_at
                    hours_silent = round(diff.total_seconds() / 3600, 1)
                silent_hives.append(
                    DashboardSilentHive(
                        hive_id=str(hive.hive_id),
                        hive_name=hive.hive_name or str(hive.hive_id),
                        last_audio_at=last_audio_at.isoformat() if last_audio_at else None,
                        hours_silent=hours_silent,
                    )
                )

    return DashboardResponse(
        total_hives=total_hives,
        active_hives=active_hives,
        status_counts=counts,
        key_metrics=metrics,
        recordings_today=recordings_today,
        silent_hives=silent_hives,
        pending_alerts=pending_alerts,
    )

