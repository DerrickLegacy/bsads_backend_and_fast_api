"""
Advisory Action Library CRUD — managed by admins via beehive-app.

This is the reusable action library (advisories table) that defines
all possible actions for each classification with confidence thresholds.

GET endpoints are open to authenticated users.
Write operations (POST, PUT, DELETE) require admin role.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Advisory, AdvisoryTemplate, User
from api.routers.auth import get_current_user
from api.schemas import (
    AdvisoryLibraryCreate,
    AdvisoryLibraryResponse,
    AdvisoryLibraryUpdate,
)

router = APIRouter(prefix="/advisory-library", tags=["Advisory Library"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=list[AdvisoryLibraryResponse])
def list_all_actions(
    template_id: int = Query(None, description="Filter by template_id (hive state)"),
    is_active: bool = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    List all actions in the library.
    
    Optionally filter by template_id (to see all actions for a specific classification)
    or is_active (to see only active actions).
    """
    query = db.query(Advisory)
    
    if template_id is not None:
        query = query.filter(Advisory.template_id == template_id)
    
    if is_active is not None:
        query = query.filter(Advisory.is_active == is_active)
    
    return query.order_by(
        Advisory.template_id, 
        Advisory.action_order
    ).all()


@router.get("/by-classification/{hive_state}", response_model=list[AdvisoryLibraryResponse])
def list_actions_by_classification(
    hive_state: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    List all actions for a specific classification (hive state).
    
    Example: GET /advisory-library/by-classification/swarm
    Returns all actions defined for swarm events.
    """
    template = db.query(AdvisoryTemplate).filter(
        AdvisoryTemplate.hive_state == hive_state
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404, 
            detail=f"No template found for hive_state: {hive_state}"
        )
    
    return db.query(Advisory).filter(
        Advisory.template_id == template.template_id
    ).order_by(Advisory.action_order).all()


@router.get("/{advisory_id}", response_model=AdvisoryLibraryResponse)
def get_action(
    advisory_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a specific action from the library."""
    action = db.query(Advisory).filter(
        Advisory.advisory_id == advisory_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    return action


@router.post("", response_model=AdvisoryLibraryResponse, status_code=status.HTTP_201_CREATED)
def create_action(
    body: AdvisoryLibraryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Create a new action in the library.
    
    Admin only. Used to add new actions for a classification.
    """
    # Verify template exists
    template = db.query(AdvisoryTemplate).filter(
        AdvisoryTemplate.template_id == body.template_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404, 
            detail=f"Template with id {body.template_id} not found"
        )
    
    # Validate threshold range
    if body.confidence_threshold_min > body.confidence_threshold_max:
        raise HTTPException(
            status_code=400,
            detail="confidence_threshold_min cannot be greater than confidence_threshold_max"
        )
    
    action = Advisory(**body.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


@router.put("/{advisory_id}", response_model=AdvisoryLibraryResponse)
def update_action(
    advisory_id: str,
    body: AdvisoryLibraryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Update an existing action in the library.
    
    Admin only. Changes apply to future inferences only.
    """
    action = db.query(Advisory).filter(
        Advisory.advisory_id == advisory_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Validate threshold range if being updated
    update_data = body.model_dump(exclude_none=True)
    
    if "confidence_threshold_min" in update_data or "confidence_threshold_max" in update_data:
        new_min = update_data.get("confidence_threshold_min", action.confidence_threshold_min)
        new_max = update_data.get("confidence_threshold_max", action.confidence_threshold_max)
        
        if new_min > new_max:
            raise HTTPException(
                status_code=400,
                detail="confidence_threshold_min cannot be greater than confidence_threshold_max"
            )
    
    for field, value in update_data.items():
        setattr(action, field, value)
    
    db.commit()
    db.refresh(action)
    return action


@router.delete("/{advisory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(
    advisory_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Delete an action from the library.
    
    Admin only. This will not affect already-created advisory_actions records.
    """
    action = db.query(Advisory).filter(
        Advisory.advisory_id == advisory_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    db.delete(action)
    db.commit()


@router.patch("/{advisory_id}/toggle", response_model=AdvisoryLibraryResponse)
def toggle_action_active(
    advisory_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Toggle the is_active status of an action.
    
    Admin only. Deactivated actions won't be suggested in future inferences.
    """
    action = db.query(Advisory).filter(
        Advisory.advisory_id == advisory_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action.is_active = not action.is_active
    db.commit()
    db.refresh(action)
    return action
