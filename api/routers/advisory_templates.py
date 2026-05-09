"""
Advisory template CRUD — managed by the beehive-app admin panel.
GET is open to any authenticated user; write operations require admin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import AdvisoryTemplate, User
from api.routers.auth import get_current_user
from api.schemas import (
    AdvisoryTemplateCreate,
    AdvisoryTemplateResponse,
    AdvisoryTemplateUpdate,
)

router = APIRouter(prefix="/advisory-templates", tags=["Advisory Templates"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=list[AdvisoryTemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(AdvisoryTemplate).order_by(AdvisoryTemplate.prediction_code).all()


@router.post("", response_model=AdvisoryTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    body: AdvisoryTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    if db.query(AdvisoryTemplate).filter(AdvisoryTemplate.hive_state == body.hive_state).first():
        raise HTTPException(status_code=400, detail="Template for this hive_state already exists")

    tmpl = AdvisoryTemplate(**body.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.put("/{template_id}", response_model=AdvisoryTemplateResponse)
def update_template(
    template_id: int,
    body: AdvisoryTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    tmpl = db.query(AdvisoryTemplate).filter(AdvisoryTemplate.template_id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tmpl, field, value)

    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    tmpl = db.query(AdvisoryTemplate).filter(AdvisoryTemplate.template_id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()
