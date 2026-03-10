from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar, Optional

import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "role"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    name:        Mapped[str]          = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]]= mapped_column(String(255), nullable=True)
    is_active:   Mapped[bool]         = mapped_column(Boolean, nullable=False, default=True)
    created_at:  Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tier(Base):
    __tablename__ = "tier"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    name:        Mapped[str]          = mapped_column(String(20), nullable=False, unique=True)
    description: Mapped[Optional[str]]= mapped_column(String(255), nullable=True)
    is_active:   Mapped[bool]         = mapped_column(Boolean, nullable=False, default=True)
    created_at:  Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "company"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    name:       Mapped[str]           = mapped_column(String(255), nullable=False)
    domain:     Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    is_active:  Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Product(Base):
    __tablename__ = "product"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    name:       Mapped[str]           = mapped_column(String(255), nullable=False)
    code:       Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    is_active:  Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CompanyProductSubscription(Base):
    __tablename__ = "company_product_subscription"
    __table_args__: ClassVar[tuple] = (
        Index(
            "uq_company_product_one_active",
            "company_id", "product_id",
            unique=True,
            postgresql_where="is_active = TRUE",
        ),
        {"schema": "auth"},
    )

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    company_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.company.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.product.id", ondelete="RESTRICT"), nullable=False, index=True)
    tier_id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.tier.id", ondelete="RESTRICT"), nullable=False)
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active:   Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True)


class User(Base):
    __tablename__ = "user"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:                   Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    email:                Mapped[str]           = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password:      Mapped[str]           = mapped_column(String(255), nullable=False)
    full_name:            Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_id:           Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.company.id", ondelete="SET NULL"), nullable=True, index=True)
    role_id:              Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("auth.role.id", ondelete="RESTRICT"), nullable=False, index=True)
    ph_no:                Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    preferred_contact:    Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active:            Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    last_login:           Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:           Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:           Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at:           Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RevokeToken(Base):
    __tablename__ = "revoke_token"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    user_id:    Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("auth.user.id", ondelete="CASCADE"), nullable=False, index=True)
    jti:        Mapped[str]           = mapped_column(String(255), nullable=False, unique=True, index=True)
    parent_jti: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    family_id:  Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    is_revoked: Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"
    __table_args__: ClassVar[dict] = {"schema": "auth"}

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.user.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str]       = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    is_used:    Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)