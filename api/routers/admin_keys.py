from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import AdminKey, User
from api.routers.auth import get_current_user
from api.schemas import AdminKeyResponse, AdminKeyCreate, AdminKeyUpdate

router = APIRouter(prefix="/admin/keys", tags=["Admin Keys"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("", response_model=List[AdminKeyResponse])
def list_admin_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """List all admin keys for external data source servers."""
    keys = db.query(AdminKey).all()
    return keys


@router.get("/{admin_key_id}", response_model=AdminKeyResponse)
def get_admin_key(
    admin_key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """Get a specific admin key by ID."""
    key = db.query(AdminKey).filter(AdminKey.admin_key_id == admin_key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin key not found"
        )
    return key


@router.post("", response_model=AdminKeyResponse, status_code=status.HTTP_201_CREATED)
def create_admin_key(
    body: AdminKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """Create a new admin key for an external data source server."""
    # Check if admin key already exists
    existing = db.query(AdminKey).filter(AdminKey.admin_key == body.admin_key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin key already exists"
        )
    
    key = AdminKey(
        server_name=body.server_name,
        server_url=body.server_url,
        admin_key=body.admin_key,
        description=body.description,
        is_active=body.is_active,
        created_by=current_user.user_id
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


@router.put("/{admin_key_id}", response_model=AdminKeyResponse)
def update_admin_key(
    admin_key_id: str,
    body: AdminKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """Update an existing admin key."""
    key = db.query(AdminKey).filter(AdminKey.admin_key_id == admin_key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin key not found"
        )
    
    # Update fields if provided
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(key, field, value)
    
    db.commit()
    db.refresh(key)
    return key


@router.delete("/{admin_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_key(
    admin_key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """Delete an admin key."""
    key = db.query(AdminKey).filter(AdminKey.admin_key_id == admin_key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin key not found"
        )
    
    db.delete(key)
    db.commit()
    return None


@router.get("/server/{server_name}", response_model=AdminKeyResponse)
def get_admin_key_by_server(
    server_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """Get admin key for a specific server by server name."""
    key = db.query(AdminKey).filter(
        AdminKey.server_name == server_name,
        AdminKey.is_active == True
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active admin key found for server: {server_name}"
        )
    
    return key
