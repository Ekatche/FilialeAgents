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
    HIERARCHICAL = "hierarchical"


class HubSpotPortal(Base):
    """
    HubSpot Portal model.
    Représente un portail HubSpot (hub_id).
    Un portail peut avoir plusieurs users et partage les recherches entre eux.
    Remplace Organization : le portail gère les limites et la facturation.
    """

    __tablename__ = "hubspot_portals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hubspot_portal_id = Column(Integer, unique=True, nullable=False, index=True, comment="HubSpot hub_id")
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    timezone = Column(String(100), nullable=True)

    # Champs migrés depuis Organization
    is_active = Column(Boolean, default=True, nullable=False)
    
    settings = Column(JSONB, default=dict, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="hubspot_portal", cascade="all, delete-orphan")
    extractions = relationship("CompanyExtraction", back_populates="hubspot_portal", cascade="all, delete-orphan")
    usage_stats = relationship("PortalUsage", back_populates="hubspot_portal", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HubSpotPortal {self.name} (hub_id: {self.hubspot_portal_id})>"


class User(Base):
    """
    User model.
    Synced with HubSpot Contact/User.
    Lié à un HubSpotPortal pour partager les recherches avec les autres users du même portail.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hubspot_portal_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_portals.id", ondelete="CASCADE"), nullable=False, index=True)
    hubspot_user_id = Column(String(255), unique=True, nullable=True, index=True)  # Nullable pour mode local
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)  # Pour auth locale uniquement
    role = Column(Enum(*(e.value for e in UserRole), name="userrole"), default=UserRole.MEMBER.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    hubspot_portal = relationship("HubSpotPortal", back_populates="users")
    oauth_token = relationship("OAuthToken", back_populates="user", uselist=False, cascade="all, delete-orphan")
    extractions = relationship("CompanyExtraction", back_populates="user")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

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
    Lié à un HubSpotPortal pour partager les recherches entre users du même portail.
    Les résultats sont stockés en JSONB pour un accès flexible (format NoSQL dans PostgreSQL).
    """

    __tablename__ = "company_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hubspot_portal_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_portals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)

    company_name = Column(String(500), nullable=False)
    company_url = Column(String(1000), nullable=True)
    extraction_type = Column(Enum(*(e.value for e in ExtractionType), name="extractiontype"), nullable=False)

    # Store complete extraction results as JSONB (format NoSQL dans PostgreSQL)
    extraction_data = Column(JSONB, nullable=True)

    status = Column(Enum(*(e.value for e in ExtractionStatus), name="extractionstatus"), default=ExtractionStatus.PENDING.value, nullable=False)
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

    # HubSpot synchronization tracking
    hubspot_sync_data = Column(JSONB, nullable=True, comment="Tracking des synchronisations HubSpot (IDs, statuts, dates)")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    hubspot_portal = relationship("HubSpotPortal", back_populates="extractions")
    user = relationship("User", back_populates="extractions")

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_extraction_portal_created", "hubspot_portal_id", "created_at"),
        Index("idx_extraction_user_created", "user_id", "created_at"),
        Index("idx_extraction_status", "status"),
        # Index GIN pour les requêtes JSON sur extraction_data
        Index("idx_extraction_data_gin", "extraction_data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<CompanyExtraction {self.company_name} ({self.status})>"


class PortalUsage(Base):
    """
    Track portal usage statistics per month.
    Used for plan limits and billing.
    """

    __tablename__ = "portal_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hubspot_portal_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_portals.id", ondelete="CASCADE"), nullable=False)

    # Month tracking (stored as first day of month)
    month = Column(DateTime(timezone=True), nullable=False)

    searches_count = Column(Integer, default=0, nullable=False)
    api_calls_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    hubspot_portal = relationship("HubSpotPortal", back_populates="usage_stats")

    # Unique constraint: one record per portal per month
    __table_args__ = (
        UniqueConstraint("hubspot_portal_id", "month", name="uq_portal_month"),
        Index("idx_usage_portal_month", "hubspot_portal_id", "month"),
    )

    def __repr__(self):
        return f"<PortalUsage {self.hubspot_portal_id} - {self.month.strftime('%Y-%m')}>"


class SessionState(Base):
    """
    Session state storage for WebSocket tracking.
    Replaces Redis for session persistence.
    Stores extraction progress and agent status in PostgreSQL.
    """

    __tablename__ = "session_states"

    session_id = Column(String(255), primary_key=True, index=True)
    progress_data = Column(JSONB, nullable=False, comment="ExtractionProgress serialized as JSON")
    results_data = Column(JSONB, nullable=True, comment="Final extraction results")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True, comment="TTL for automatic cleanup")

    # Indexes for cleanup queries
    __table_args__ = (
        Index("idx_session_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<SessionState {self.session_id} (expires: {self.expires_at})>"


class UserSession(Base):
    """
    User authentication session tracking.
    Tracks active user sessions for both local and HubSpot authentication.
    Allows session revocation and management.
    """

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Session identification (hash of JWT access token for identification)
    session_token_hash = Column(String(255), unique=True, nullable=False, index=True, comment="SHA-256 hash of access token")
    refresh_token_hash = Column(String(255), nullable=False, index=True, comment="SHA-256 hash of refresh token")
    
    # Session metadata
    ip_address = Column(String(45), nullable=True, comment="IPv4 or IPv6 address")
    user_agent = Column(String(500), nullable=True, comment="User agent string")
    auth_method = Column(String(50), nullable=False, default="local", comment="Authentication method: 'local' or 'hubspot'")
    
    # Session state
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True, comment="Based on refresh token expiration")
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes for cleanup and queries
    __table_args__ = (
        Index("idx_user_sessions_user_active", "user_id", "is_active"),
        Index("idx_user_sessions_expires_at", "expires_at"),
        Index("idx_user_sessions_last_activity", "last_activity_at"),
    )
    
    def __repr__(self):
        return f"<UserSession {self.id} (user: {self.user_id}, active: {self.is_active})>"
