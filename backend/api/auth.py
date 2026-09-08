# backend/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.core.security import hash_password, verify_password, create_access_token
from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse
)
from backend.api.deps import get_current_active_user
from backend.core.audit import record_audit_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
def register(
    payload: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user, hash their password with bcrypt, and return an access token.
    """
    normalized_email = payload.email.strip().lower()

    # Check duplicate email
    existing_user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()

    if existing_user:
        record_audit_event(
            event_type="AUTH_REGISTER_FAILED",
            user_id=None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"reason": "email_already_exists"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )

    # Hash password securely
    hashed_pwd = hash_password(payload.password)

    # Create new User
    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip() if payload.full_name else None,
        password_hash=hashed_pwd,
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate access token
    access_token = create_access_token(subject=user.id)

    # Record audit event
    record_audit_event(
        event_type="AUTH_REGISTER",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        db=db
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT access token"
)
def login(
    payload: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user credentials and issue a signed JWT access token.
    Uses generic error responses to prevent user enumeration.
    """
    normalized_email = payload.email.strip().lower()

    user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()

    # Generic failure response for both missing account and incorrect password
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        record_audit_event(
            event_type="AUTH_LOGIN_FAILURE",
            user_id=user.id if user else None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"reason": "invalid_credentials"},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        record_audit_event(
            event_type="AUTH_LOGIN_FAILURE",
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"reason": "account_inactive"},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account."
        )

    access_token = create_access_token(subject=user.id)

    # Record login audit event
    record_audit_event(
        event_type="AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        db=db
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve profile of current authenticated user"
)
def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Return the identity profile for the bearer token holder.
    """
    return UserResponse.model_validate(current_user)
