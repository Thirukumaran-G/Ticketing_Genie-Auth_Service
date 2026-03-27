from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Shared password validator ─────────────────────────────────────────────────

def _check_password_strength(v: str) -> str:
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one number.")
    return v


# ── Registration ──────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email:     EmailStr
    password:  str           = Field(min_length=8, max_length=128)
    full_name: str           = Field(min_length=1, max_length=255)
    ph_no:     str | None = Field(default=None, max_length=20)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)

    @field_validator("ph_no")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) != 10:
            raise ValueError("Phone number must be exactly 10 digits.")
        if digits[0] not in ("6", "7", "8", "9"):
            raise ValueError("Phone number must start with 6, 7, 8, or 9.")
        return digits


class RegisterResponse(BaseModel):
    id:         uuid.UUID
    email:      str
    full_name:  str | None
    role:       str
    company_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=1)


# ── Tokens ────────────────────────────────────────────────────────────────────

class ProductTierInfo(BaseModel):
    tier_id:   str
    tier_name: str
    code:      str


class TokenPair(BaseModel):
    access_token:  str
    refresh_token: str
    expires_in:    int


class RefreshTokenRequest(BaseModel):
    refresh_token: str = ""


class LogoutRequest(BaseModel):
    refresh_token: str = ""


class TokenValidationResponse(BaseModel):
    valid:         bool
    actor_id:      str
    role:          str
    scopes:        list[str]
    email:         str | None                         = None
    company_id:    str | None                         = None
    product_tiers: dict[str, ProductTierInfo] | None = None


# ── Me ────────────────────────────────────────────────────────────────────────

class MeResponse(BaseModel):
    actor_id:          uuid.UUID
    email:             str
    full_name:         str | None
    role:              str
    preferred_contact: str | None                        = None
    company_id:        uuid.UUID | None                  = None
    product_tiers:     dict[str, ProductTierInfo] | None = None
    is_active:         bool

    model_config = {"from_attributes": True}


# ── Change password ───────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password:     str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


# ── Forgot / Reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:        str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


# ── Internal staff creation ───────────────────────────────────────────────────

class InternalUserCreateRequest(BaseModel):
    email:     EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role:      str = Field(min_length=1, max_length=20)


class InternalUserCreateResponse(BaseModel):
    user_id:       uuid.UUID
    email:         str
    full_name:     str | None
    role:          str
    temp_password: str

    model_config = {"from_attributes": True}


# ── Internal lookups ──────────────────────────────────────────────────────────

class UserEmailResponse(BaseModel):
    user_id: uuid.UUID
    email:   str

    model_config = {"from_attributes": True}


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ProductListResponse(BaseModel):
    products: list[dict[str, Any]]


class CompanyByDomainResponse(BaseModel):
    company_id:   str
    company_name: str
    domain:       str


class InternalCustomerCreateRequest(BaseModel):
    email:             str
    full_name:         str
    company_id:        str
    preferred_contact: str = "email"


class InternalCustomerCreateResponse(BaseModel):
    user_id:       str
    email:         str
    full_name:     str
    temp_password: str
    is_new:        bool

class PreferredContactUpdate(BaseModel):
    preferred_contact: str
