from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.models import Advisory, Hive, InferenceResult, User
from api.routers.auth import get_current_user
from api.schemas import InferenceResponse

router = APIRouter(prefix="/hives", tags=["Inference Results"])


@router.get("/{hive_id}/inferences", response_model=list[InferenceResponse])
def get_inferences(
    hive_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the latest inference results for a hive.
    Only the hive owner can query this.
    """
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    results = (
        db.query(InferenceResult)
        .options(
            joinedload(InferenceResult.alert),
            joinedload(InferenceResult.advisory_actions),
        )
        .filter(InferenceResult.hive_id == hive_id)
        .order_by(InferenceResult.created_at.desc())
        .limit(limit)
        .all()
    )
    return results


@router.get("/{hive_id}/inferences/latest", response_model=InferenceResponse)
def get_latest_inference(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return only the most recent inference for quick status checks on mobile."""
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    result = (
        db.query(InferenceResult)
        .options(
            joinedload(InferenceResult.alert),
            joinedload(InferenceResult.advisory_actions),
        )
        .filter(InferenceResult.hive_id == hive_id)
        .order_by(InferenceResult.created_at.desc())
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="No inference results yet for this hive")
    return result
