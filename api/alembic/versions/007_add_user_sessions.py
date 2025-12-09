"""Add UserSession model for tracking user authentication sessions

Revision ID: 007
Revises: 006
Create Date: 2025-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_token_hash', sa.String(length=255), unique=True, nullable=False, comment='SHA-256 hash of access token'),
        sa.Column('refresh_token_hash', sa.String(length=255), nullable=False, comment='SHA-256 hash of refresh token'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IPv4 or IPv6 address'),
        sa.Column('user_agent', sa.String(length=500), nullable=True, comment='User agent string'),
        sa.Column('auth_method', sa.String(length=50), nullable=False, server_default='local', comment="Authentication method: 'local' or 'hubspot'"),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Based on refresh token expiration'),
    )
    
    # Create indexes
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_session_token_hash', 'user_sessions', ['session_token_hash'])
    op.create_index('ix_user_sessions_refresh_token_hash', 'user_sessions', ['refresh_token_hash'])
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'])
    op.create_index('idx_user_sessions_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    op.create_index('idx_user_sessions_last_activity', 'user_sessions', ['last_activity_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_user_sessions_last_activity', table_name='user_sessions')
    op.drop_index('idx_user_sessions_expires_at', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_active', table_name='user_sessions')
    op.drop_index('ix_user_sessions_is_active', table_name='user_sessions')
    op.drop_index('ix_user_sessions_refresh_token_hash', table_name='user_sessions')
    op.drop_index('ix_user_sessions_session_token_hash', table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    
    # Drop table
    op.drop_table('user_sessions')

