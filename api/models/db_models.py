"""
SQLAlchemy database models for authentication and data persistence.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class UserRole(str, PyEnum):
    """User roles in the organization."""

    ADMIN = "admin"
    MEMBER = "member"


class PlanType(str, PyEnum):
    """Organization subscription plan types."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ExtractionStatus(str, PyEnum):
    """Status of company extraction."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractionType(str, PyEnum):
    """Type of extraction."""

    NAME = "name"
    URL = "url"


class Organization(Base):
    """
    Organization/Company model.
    Synced with HubSpot Company.
    """

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hubspot_company_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    plan_type = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    max_searches_per_month = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSONB, default=dict, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    extractions = relationship("CompanyExtraction", back_populates="organization", cascade="all, delete-orphan")
    usage_stats = relationship("OrganizationUsage", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name} ({self.hubspot_company_id})>"


class User(Base):
    """
    User model.
    Synced with HubSpot Contact/User.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    hubspot_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    oauth_token = relationship("OAuthToken", back_populates="user", uselist=False, cascade="all, delete-orphan")
    extractions = relationship("CompanyExtraction", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class OAuthToken(Base):
    """
    OAuth token storage for HubSpot integration.
    Tokens are encrypted at rest.
    """

    __tablename__ = "oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Encrypted tokens (should be encrypted before storage)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="bearer", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    scope = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="oauth_token")

    def __repr__(self):
        return f"<OAuthToken for user {self.user_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.utcnow() >= self.expires_at


class CompanyExtraction(Base):
    """
    Company extraction/search history.
    Stores all extraction requests and results.
    """

    __tablename__ = "company_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)

    company_name = Column(String(500), nullable=False)
    company_url = Column(String(1000), nullable=True)
    extraction_type = Column(Enum(ExtractionType), nullable=False)

    # Store complete extraction results as JSONB
    extraction_data = Column(JSONB, nullable=True)

    status = Column(Enum(ExtractionStatus), default=ExtractionStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)  # Time in seconds
    subsidiaries_count = Column(Integer, default=0, nullable=False)

    # Cost tracking
    cost_usd = Column(Float, nullable=True)  # Total cost in USD
    cost_eur = Column(Float, nullable=True)  # Total cost in EUR
    total_tokens = Column(Integer, nullable=True)  # Total tokens used
    input_tokens = Column(Integer, nullable=True)  # Input tokens
    output_tokens = Column(Integer, nullable=True)  # Output tokens
    models_usage = Column(JSONB, nullable=True)  # Detailed breakdown by model

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="extractions")
    user = relationship("User", back_populates="extractions")

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_extraction_org_created", "organization_id", "created_at"),
        Index("idx_extraction_user_created", "user_id", "created_at"),
        Index("idx_extraction_status", "status"),
    )

    def __repr__(self):
        return f"<CompanyExtraction {self.company_name} ({self.status})>"


class OrganizationUsage(Base):
    """
    Track organization usage statistics per month.
    Used for plan limits and billing.
    """

    __tablename__ = "organization_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # Month tracking (stored as first day of month)
    month = Column(DateTime(timezone=True), nullable=False)

    searches_count = Column(Integer, default=0, nullable=False)
    api_calls_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="usage_stats")

    # Unique constraint: one record per organization per month
    __table_args__ = (
        UniqueConstraint("organization_id", "month", name="uq_org_month"),
        Index("idx_usage_org_month", "organization_id", "month"),
    )

    def __repr__(self):
        return f"<OrganizationUsage {self.organization_id} - {self.month.strftime('%Y-%m')}>"
