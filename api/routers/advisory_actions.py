"""
Advisory Actions — inference-specific suggested actions for farmers.

These are the actual actions suggested for each hive inference based on
ML confidence scores. Farmers can view and update the status of these actions.

GET endpoints show suggested actions for inferences/hives.
PATCH endpoints allow farmers to update action status (completed, in_progress, skipped).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.models import AdvisoryAction, AdvisoryTemplate, Hive, InferenceResult, User
from api.routers.auth import get_current_user
from api.schemas import AdvisoryActionSuggestedResponse, AdvisoryActionUpdateStatus

router = APIRouter(prefix="/advisory-actions", tags=["Advisory Actions"])


def _get_user_hive(hive_id: str, current_user: User, db: Session) -> Hive:
    """Verify the hive belongs to the current user (or user is admin)."""
    hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
    
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")
    
    if current_user.role != "admin" and hive.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return hive


@router.get("/inference/{inference_id}", response_model=list[AdvisoryActionSuggestedResponse])
def get_actions_for_inference(
    inference_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all suggested actions for a specific inference.
    
    Returns the checklist of actions that were generated based on
    the ML confidence score for that inference.
    """
    # Verify inference exists and user has access
    inference = db.query(InferenceResult).filter(
        InferenceResult.inference_id == inference_id
    ).first()
    
    if not inference:
        raise HTTPException(status_code=404, detail="Inference not found")
    
    # Check hive ownership
    _get_user_hive(inference.hive_id, current_user, db)
    
    # Get actions with template info
    actions = db.query(AdvisoryAction).filter(
        AdvisoryAction.inference_id == inference_id
    ).order_by(
        AdvisoryAction.priority_level.desc(),
        AdvisoryAction.created_at
    ).all()
    
    # Manually add hive_state from template
    result = []
    for action in actions:
        template = db.query(AdvisoryTemplate).filter(
            AdvisoryTemplate.template_id == action.template_id
        ).first()
        
        action_dict = {
            "action_id": action.action_id,
            "inference_id": action.inference_id,
            "hive_id": action.hive_id,
            "template_id": action.template_id,
            "hive_state": template.hive_state if template else "unknown",
            "confidence_score": float(action.confidence_score),
            "action_title": action.action_title,
            "action_description": action.action_description,
            "priority_level": action.priority_level,
            "status": action.status,
            "completed_at": action.completed_at,
            "notes": action.notes,
            "created_at": action.created_at,
        }
        result.append(AdvisoryActionSuggestedResponse(**action_dict))
    
    return result


@router.get("/hive/{hive_id}", response_model=list[AdvisoryActionSuggestedResponse])
def get_actions_for_hive(
    hive_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, in_progress, completed, skipped"),
    limit: int = Query(50, description="Maximum number of actions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all suggested actions for a hive, optionally filtered by status.
    
    Returns recent actions across all inferences for this hive.
    Useful for showing pending tasks for a farmer.
    """
    # Check hive ownership
    _get_user_hive(hive_id, current_user, db)
    
    query = db.query(AdvisoryAction).filter(
        AdvisoryAction.hive_id == hive_id
    )
    
    if status_filter:
        query = query.filter(AdvisoryAction.status == status_filter)
    
    actions = query.order_by(
        AdvisoryAction.created_at.desc()
    ).limit(limit).all()
    
    # Manually add hive_state from template
    result = []
    for action in actions:
        template = db.query(AdvisoryTemplate).filter(
            AdvisoryTemplate.template_id == action.template_id
        ).first()
        
        action_dict = {
            "action_id": action.action_id,
            "inference_id": action.inference_id,
            "hive_id": action.hive_id,
            "template_id": action.template_id,
            "hive_state": template.hive_state if template else "unknown",
            "confidence_score": float(action.confidence_score),
            "action_title": action.action_title,
            "action_description": action.action_description,
            "priority_level": action.priority_level,
            "status": action.status,
            "completed_at": action.completed_at,
            "notes": action.notes,
            "created_at": action.created_at,
        }
        result.append(AdvisoryActionSuggestedResponse(**action_dict))
    
    return result


@router.get("/hive/{hive_id}/pending-count")
def get_pending_count(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get count of pending actions for a hive.
    
    Useful for dashboard badges showing how many tasks are pending.
    """
    # Check hive ownership
    _get_user_hive(hive_id, current_user, db)
    
    pending_count = db.query(AdvisoryAction).filter(
        and_(
            AdvisoryAction.hive_id == hive_id,
            AdvisoryAction.status == "pending"
        )
    ).count()
    
    return {
        "hive_id": hive_id,
        "pending_count": pending_count
    }


@router.patch("/{action_id}/status", response_model=AdvisoryActionSuggestedResponse)
def update_action_status(
    action_id: str,
    body: AdvisoryActionUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the status of a specific action.
    
    Farmers use this to mark actions as:
    - in_progress: Started working on it
    - completed: Finished the action
    - skipped: Decided not to do this action
    - pending: Reset to pending
    """
    action = db.query(AdvisoryAction).filter(
        AdvisoryAction.action_id == action_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Check hive ownership
    _get_user_hive(action.hive_id, current_user, db)
    
    # Validate status
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update status
    action.status = body.status
    if body.notes:
        action.notes = body.notes
    
    # Set completed_at timestamp if status is completed
    if body.status == "completed":
        action.completed_at = datetime.utcnow()
    elif action.completed_at and body.status != "completed":
        # Clear completed_at if status changed from completed to something else
        action.completed_at = None
    
    db.commit()
    db.refresh(action)
    
    # Get template for response
    template = db.query(AdvisoryTemplate).filter(
        AdvisoryTemplate.template_id == action.template_id
    ).first()
    
    action_dict = {
        "action_id": action.action_id,
        "inference_id": action.inference_id,
        "hive_id": action.hive_id,
        "template_id": action.template_id,
        "hive_state": template.hive_state if template else "unknown",
        "confidence_score": float(action.confidence_score),
        "action_title": action.action_title,
        "action_description": action.action_description,
        "priority_level": action.priority_level,
        "status": action.status,
        "completed_at": action.completed_at,
        "notes": action.notes,
        "created_at": action.created_at,
    }
    
    return AdvisoryActionSuggestedResponse(**action_dict)


@router.get("/user/pending", response_model=list[AdvisoryActionSuggestedResponse])
def get_all_pending_actions_for_user(
    limit: int = Query(100, description="Maximum number of actions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all pending actions across all of the user's hives.
    
    Useful for showing a farmer their complete to-do list.
    """
    # Get all hives for this user
    hives = db.query(Hive).filter(Hive.owner_id == current_user.user_id).all()
    hive_ids = [h.hive_id for h in hives]
    
    if not hive_ids:
        return []
    
    actions = db.query(AdvisoryAction).filter(
        and_(
            AdvisoryAction.hive_id.in_(hive_ids),
            AdvisoryAction.status == "pending"
        )
    ).order_by(
        AdvisoryAction.priority_level.desc(),
        AdvisoryAction.created_at.desc()
    ).limit(limit).all()
    
    # Manually add hive_state from template
    result = []
    for action in actions:
        template = db.query(AdvisoryTemplate).filter(
            AdvisoryTemplate.template_id == action.template_id
        ).first()
        
        action_dict = {
            "action_id": action.action_id,
            "inference_id": action.inference_id,
            "hive_id": action.hive_id,
            "template_id": action.template_id,
            "hive_state": template.hive_state if template else "unknown",
            "confidence_score": float(action.confidence_score),
            "action_title": action.action_title,
            "action_description": action.action_description,
            "priority_level": action.priority_level,
            "status": action.status,
            "completed_at": action.completed_at,
            "notes": action.notes,
            "created_at": action.created_at,
        }
        result.append(AdvisoryActionSuggestedResponse(**action_dict))
    
    return result
