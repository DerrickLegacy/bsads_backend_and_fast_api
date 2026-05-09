"""
Admin-only user management endpoints.
All routes require role == 'admin'.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import User
from api.routers.auth import _hash, get_current_user
from api.schemas import AdminUserCreate, AdminUserUpdate, UserDetailResponse

router = APIRouter(prefix="/users", tags=["Admin – Users"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("", response_model=list[UserDetailResponse])
def list_users(
    role: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """List all users, optionally filtered by role (farmer | admin)."""
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.order_by(User.created_at.desc()).all()


@router.post("", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """Admin creates a farmer account (used by the beehive-app admin panel)."""
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=body.full_name,
        email=body.email,
        password_hash=_hash(body.password),
        phone=body.phone,
        address=body.address,
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserDetailResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: str,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
