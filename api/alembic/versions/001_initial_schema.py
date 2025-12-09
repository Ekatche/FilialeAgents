"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS)
    op.execute("DO $$ BEGIN CREATE TYPE userrole AS ENUM ('admin', 'member'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE extractionstatus AS ENUM ('pending', 'running', 'completed', 'failed'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE extractiontype AS ENUM ('name', 'url', 'hierarchical'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('hubspot_company_id', sa.String(length=255), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_organizations_hubspot_company_id', 'organizations', ['hubspot_company_id'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hubspot_user_id', sa.String(length=255), nullable=False, unique=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('role', postgresql.ENUM('admin', 'member', name='userrole', create_type=False), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_users_hubspot_user_id', 'users', ['hubspot_user_id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Create oauth_tokens table
    op.create_table(
        'oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('token_type', sa.String(length=50), nullable=False, server_default='bearer'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scope', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create company_extractions table
    op.create_table(
        'company_extractions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False, unique=True),
        sa.Column('company_name', sa.String(length=500), nullable=False),
        sa.Column('company_url', sa.String(length=1000), nullable=True),
        sa.Column('extraction_type', postgresql.ENUM('name', 'url', 'hierarchical', name='extractiontype', create_type=False), nullable=False),
        sa.Column('extraction_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'completed', 'failed', name='extractionstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('subsidiaries_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_company_extractions_session_id', 'company_extractions', ['session_id'])
    op.create_index('idx_extraction_org_created', 'company_extractions', ['organization_id', 'created_at'])
    op.create_index('idx_extraction_user_created', 'company_extractions', ['user_id', 'created_at'])
    op.create_index('idx_extraction_status', 'company_extractions', ['status'])

    # Create organization_usage table
    op.create_table(
        'organization_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('month', sa.DateTime(timezone=True), nullable=False),
        sa.Column('searches_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('api_calls_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'month', name='uq_org_month'),
    )
    op.create_index('idx_usage_org_month', 'organization_usage', ['organization_id', 'month'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('organization_usage')
    op.drop_table('company_extractions')
    op.drop_table('oauth_tokens')
    op.drop_table('users')
    op.drop_table('organizations')

    # Drop enum types
    op.execute("DROP TYPE extractiontype")
    op.execute("DROP TYPE extractionstatus")
    op.execute("DROP TYPE userrole")
    op.execute("DROP TYPE plantype")
