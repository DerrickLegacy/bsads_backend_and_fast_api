"""
Top-level read endpoints for inferences and advisories.
Admin sees all records; farmers see only their own hives' records.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.models import Advisory, Hive, InferenceResult, User
from api.routers.auth import get_current_user
from api.schemas import AdminAdvisoryResponse, InferenceResponse

router = APIRouter(tags=["Inferences & Advisories"])


def _hive_ids_for(user: User, db: Session) -> list[str] | None:
    """Return hive_id list for non-admin, or None meaning 'all hives'."""
    if user.role == "admin":
        return None
    return [r.hive_id for r in db.query(Hive.hive_id).filter(Hive.owner_id == user.user_id).all()]


# ---------------------------------------------------------------------------
# Inferences
# ---------------------------------------------------------------------------
@router.get("/inferences", response_model=list[InferenceResponse])
def list_inferences(
    hive_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All inference results. Admin sees everything; farmers see their own hives."""
    allowed_ids = _hive_ids_for(current_user, db)

    q = (
        db.query(InferenceResult)
        .options(
            joinedload(InferenceResult.alert),
            joinedload(InferenceResult.advisory).joinedload(Advisory.actions),
        )
    )

    if hive_id:
        # If farmer, validate they own this hive
        if allowed_ids is not None and hive_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Access denied")
        q = q.filter(InferenceResult.hive_id == hive_id)
    elif allowed_ids is not None:
        q = q.filter(InferenceResult.hive_id.in_(allowed_ids))

    return q.order_by(InferenceResult.created_at.desc()).limit(limit).all()


@router.get("/inferences/{inference_id}", response_model=InferenceResponse)
def get_inference(
    inference_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_ids = _hive_ids_for(current_user, db)

    result = (
        db.query(InferenceResult)
        .options(
            joinedload(InferenceResult.alert),
            joinedload(InferenceResult.advisory).joinedload(Advisory.actions),
        )
        .filter(InferenceResult.inference_id == inference_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Inference not found")

    if allowed_ids is not None and result.hive_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    return result


# ---------------------------------------------------------------------------
# Advisories
# ---------------------------------------------------------------------------
@router.get("/advisories", response_model=list[AdminAdvisoryResponse])
def list_advisories(
    hive_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All generated advisories. Admin sees everything; farmers see their own."""
    allowed_ids = _hive_ids_for(current_user, db)

    q = db.query(Advisory)

    if hive_id:
        if allowed_ids is not None and hive_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Access denied")
        q = q.filter(Advisory.hive_id == hive_id)
    elif allowed_ids is not None:
        q = q.filter(Advisory.hive_id.in_(allowed_ids))

    return q.order_by(Advisory.created_at.desc()).limit(limit).all()


@router.get("/advisories/{advisory_id}", response_model=AdminAdvisoryResponse)
def get_advisory(
    advisory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_ids = _hive_ids_for(current_user, db)

    advisory = db.query(Advisory).filter(Advisory.advisory_id == advisory_id).first()
    if not advisory:
        raise HTTPException(status_code=404, detail="Advisory not found")

    if allowed_ids is not None and advisory.hive_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    return advisory
