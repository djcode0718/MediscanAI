# backend/schemas/auth.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128, description="Password must be at least 6 characters.")
    full_name: Optional[str] = Field(None, max_length=255)


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    """Public safe user representation (never exposes password or password_hash)."""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class TokenResponse(BaseModel):
    """JWT access token response alongside safe user identity."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
