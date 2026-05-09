from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from api.database import get_db
from api.models import EnvironmentalData, Hive, User
from api.routers.auth import get_current_user
from api.schemas import (
    DashboardKeyMetrics,
    DashboardResponse,
    DashboardStatusCounts,
)

router = APIRouter(tags=["Dashboard"])

_ACTIVE_STATES = {"normal", "pre_swarm", "swarm", "missing_queen", "queenbee_present", "pest_infested"}


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summary statistics for the logged-in farmer's dashboard screen."""
    hives = db.query(Hive).filter(Hive.owner_id == current_user.user_id).all()

    total_hives = len(hives)
    active_hives = sum(1 for h in hives if h.current_state in _ACTIVE_STATES)

    # State counts
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
        else:
            counts.other += 1

    # Latest environmental data — one record per hive, then average
    hive_ids = [h.hive_id for h in hives]
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
            temperature_c=_avg([float(r.temperature) if r.temperature else None for r in env_records]),
            humidity_percent=_avg([float(r.humidity) if r.humidity else None for r in env_records]),
            population_k_bees=_avg([float(r.population_k_bees) if r.population_k_bees else None for r in env_records]),
            nectar_flow_kg_per_day=_avg([float(r.nectar_flow_kg_per_day) if r.nectar_flow_kg_per_day else None for r in env_records]),
        )

    return DashboardResponse(
        total_hives=total_hives,
        active_hives=active_hives,
        status_counts=counts,
        key_metrics=metrics,
    )
