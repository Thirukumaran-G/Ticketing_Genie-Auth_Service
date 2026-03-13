from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic import BaseModel, EmailStr


# ── Company ───────────────────────────────────────────────────────────────────

class CompanyCreateRequest(BaseModel):
    name:   str           = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=255)


class CompanyUpdateRequest(BaseModel):
    name:      Optional[str]  = Field(default=None, min_length=1, max_length=255)
    domain:    Optional[str]  = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         uuid.UUID
    name:       str
    domain:     Optional[str]
    is_active:  bool
    created_at: datetime


# ── Product ───────────────────────────────────────────────────────────────────

class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)


class ProductUpdateRequest(BaseModel):
    name:      Optional[str]  = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         uuid.UUID
    name:       str
    code:       str
    is_active:  bool
    created_at: datetime


# ── Subscription ──────────────────────────────────────────────────────────────

class SubscriptionAssignRequest(BaseModel):
    product_id: uuid.UUID
    tier_id:    uuid.UUID


class SubscriptionUpdateRequest(BaseModel):
    tier_id:   Optional[uuid.UUID] = None
    is_active: Optional[bool]      = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           uuid.UUID
    company_id:   uuid.UUID
    product_id:   uuid.UUID
    product_name: str
    product_code: str
    tier_id:      uuid.UUID
    tier_name:    str
    is_active:    bool
    assigned_at:  datetime


# ── Tier ──────────────────────────────────────────────────────────────────────

class TierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID
    name:        str
    description: Optional[str]
    is_active:   bool


# ── Admin User View ───────────────────────────────────────────────────────────

class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         uuid.UUID
    email:      str
    full_name:  Optional[str]
    role:       str
    company_id: Optional[uuid.UUID]
    is_active:  bool
    last_login: Optional[datetime]
    created_at: datetime

class UserCreateRequest(BaseModel):
    email:             EmailStr
    full_name:         Optional[str] = None
    role:              str                    # role name e.g. "agent", "team_lead"
    preferred_contact: Optional[str] = "email"

class RoleResponse(BaseModel):
    id:   uuid.UUID
    name: str
 
    model_config = {"from_attributes": True}