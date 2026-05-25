# Option 2: OAuth2 Password Flow (Alternative Implementation)

This option makes the Swagger UI OAuth2 form work by creating a separate endpoint that accepts `username` and `password` in the OAuth2 format.

## Changes needed:

### 1. Add OAuth2PasswordRequestForm endpoint

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

@router.post("/token", response_model=Token)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint for Swagger UI.
    Username field accepts email address.
    """
    # Use username field as email
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not _verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return Token(
        access_token=create_token(user.user_id),
        user=UserResponse.model_validate(user)
    )

# Keep the original /login endpoint for mobile app
@router.post("/login", response_model=Token)
def login(body: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password (for mobile app)."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    return Token(
        access_token=create_token(user.user_id),
        user=UserResponse.model_validate(user)
    )

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validates JWT and returns the logged-in user."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = str(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

## How it works:

1. **Two login endpoints**:
   - `POST /auth/token` - OAuth2 form (username=email, password)
   - `POST /auth/login` - JSON body (email, password)

2. **Swagger UI OAuth2 form**:
   - Click "Authorize"
   - Enter email in "username" field
   - Enter password in "password" field
   - Click "Authorize"
   - Token is automatically added to all requests

3. **Mobile app** continues using `POST /auth/login` with JSON

## Pros:
- ✅ Native OAuth2 flow in Swagger UI
- ✅ Automatic token management in Swagger
- ✅ Standard OAuth2 pattern
- ✅ Mobile app keeps using simple JSON endpoint

## Cons:
- ❌ Confusing "username" field (it's actually email)
- ❌ Two endpoints doing the same thing
- ❌ More code to maintain

---

## Comparison:

| Feature | Option 1 (HTTPBearer) | Option 2 (OAuth2) |
|---------|----------------------|-------------------|
| **Swagger UI** | Paste token manually | Form with username/password |
| **Token management** | Manual | Automatic |
| **Clarity** | Very clear | "username" is confusing |
| **Endpoints** | 1 login endpoint | 2 login endpoints |
| **Mobile app** | Same endpoint | Same endpoint |
| **Simplicity** | ✅ Simpler | ❌ More complex |

---

## Your idea about storing tokens:

If you want to store tokens in the database for tracking/revocation:

```python
# Add to User model
class User(Base):
    # ... existing fields ...
    current_token = Column(Text, nullable=True)
    token_created_at = Column(DateTime, nullable=True)

# Update login to store token
@router.post("/login", response_model=Token)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Generate and store token
    token = create_token(user.user_id)
    user.current_token = token
    user.token_created_at = datetime.utcnow()
    db.commit()
    
    return Token(access_token=token, user=UserResponse.model_validate(user))

# Update get_current_user to check database
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    
    # Decode JWT
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = str(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check if token matches stored token (optional - for revocation)
    if user.current_token != token:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    return user

# Add logout endpoint to revoke token
@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout and revoke current token."""
    current_user.current_token = None
    current_user.token_created_at = None
    db.commit()
    return {"detail": "Logged out successfully"}
```

### Pros of storing tokens:
- ✅ Can revoke tokens (logout)
- ✅ Track active sessions
- ✅ Force logout from server side

### Cons of storing tokens:
- ❌ Database query on every request (slower)
- ❌ Defeats JWT stateless design
- ❌ More complex
- ❌ Need to clean up expired tokens

---

## My Recommendation:

**Stick with Option 1 (HTTPBearer - what I implemented)** because:
1. ✅ Simpler and clearer
2. ✅ Faster (no DB lookup for token validation)
3. ✅ Standard JWT pattern
4. ✅ Easy to use in Swagger UI
5. ✅ Works perfectly with curl/mobile apps

If you need token revocation later, you can add a `token_blacklist` table instead of storing tokens in the user table.
