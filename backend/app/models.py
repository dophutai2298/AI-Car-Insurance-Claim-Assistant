from enum import Enum

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ADJUSTER = "ADJUSTER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, native_enum=False))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClaimStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    AI_APPROVED = "AI_APPROVED"
    AI_REJECTED = "AI_REJECTED"
    FAILED = "FAILED"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_number: Mapped[str | None] = mapped_column(String(24), unique=True, index=True, nullable=True)
    claimant_name: Mapped[str] = mapped_column(String(120))
    vehicle_make: Mapped[str] = mapped_column(String(80))
    vehicle_model: Mapped[str] = mapped_column(String(80))
    vehicle_year: Mapped[int] = mapped_column(Integer)
    license_plate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(
        SqlEnum(ClaimStatus, native_enum=False), default=ClaimStatus.DRAFT
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
