"""
Admin-only user management endpoints.
All routes require role == 'admin'.
"""
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import User, AdminKey
from api.routers.auth import _hash, get_current_user
from api.schemas import (
    AdminUserCreate, 
    AdminUserUpdate, 
    UserDetailResponse,
    AssignFarmerTokenRequest,
    AssignFarmerTokenResponse
)

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
        server_url=body.server_url,
        api_key=body.api_key,
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


@router.post("/{user_id}/assign-token", response_model=AssignFarmerTokenResponse)
async def assign_farmer_token(
    user_id: str,
    body: AssignFarmerTokenRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Admin assigns an API token to a farmer by calling the simulation server.
    
    Admin directly provides the admin key and server URL to use.
    
    This endpoint:
    1. Gets the user from the database
    2. Uses the admin-provided admin_key and server_url
    3. Calls the simulation server to generate an API token
    4. Updates the user's server_url and api_key fields
    5. Returns the updated user information
    """
    # 1. Get the user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already has a token
    if user.api_key:
        raise HTTPException(
            status_code=400,
            detail=f"User already has an API key assigned. Current server: {user.server_url}"
        )
    
    # 2. Use the admin-provided admin key and server URL
    admin_key = body.admin_key.strip()
    simulation_url = body.server_url.strip().rstrip('/')
    
    if not admin_key:
        raise HTTPException(
            status_code=400,
            detail="Admin key is required"
        )
    
    if not simulation_url:
        raise HTTPException(
            status_code=400,
            detail="Server URL is required"
        )
    
    # 3. Call the simulation server to generate an API token
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{simulation_url}/admin/keys",
                headers={
                    "X-Admin-Key": admin_key,
                    "Content-Type": "application/json"
                },
                json={"client_name": user.full_name}
            )
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid admin key. The simulation server rejected the admin key provided."
                )
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate API key from simulation server: {response.text}"
                )
            
            result = response.json()
            generated_api_key = result.get("api_key")
            
            if not generated_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="Simulation server did not return an API key"
                )
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to simulation server at {simulation_url}. Please check if the server is running."
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to simulation server at {simulation_url}: {str(e)}"
        )
    
    # 4. Update the user's server_url and api_key
    user.server_url = simulation_url
    user.api_key = generated_api_key
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    # 5. Return the updated user information
    return AssignFarmerTokenResponse(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        server_url=user.server_url,
        api_key=user.api_key,
        assigned_at=user.updated_at
    )
