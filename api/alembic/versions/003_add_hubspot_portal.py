"""Add HubSpotPortal model and link users and extractions to portals

Revision ID: 003
Revises: 002
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create hubspot_portals table
    op.create_table(
        'hubspot_portals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('hubspot_portal_id', sa.Integer(), nullable=False, unique=True, comment='HubSpot hub_id'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=100), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_hubspot_portals_hubspot_portal_id', 'hubspot_portals', ['hubspot_portal_id'])

    # Add hubspot_portal_id to users table
    op.add_column('users',
        sa.Column('hubspot_portal_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_users_hubspot_portal_id',
        'users', 'hubspot_portals',
        ['hubspot_portal_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_users_hubspot_portal_id', 'users', ['hubspot_portal_id'])

    # Add hubspot_portal_id to company_extractions table
    op.add_column('company_extractions',
        sa.Column('hubspot_portal_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_company_extractions_hubspot_portal_id',
        'company_extractions', 'hubspot_portals',
        ['hubspot_portal_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_company_extractions_hubspot_portal_id', 'company_extractions', ['hubspot_portal_id'])

    # Create GIN index on extraction_data for JSON queries
    op.execute(
        "CREATE INDEX idx_extraction_data_gin ON company_extractions USING gin (extraction_data)"
    )

    # Update index on company_extractions to use hubspot_portal_id instead of organization_id
    op.drop_index('idx_extraction_org_created', table_name='company_extractions')
    op.create_index(
        'idx_extraction_portal_created',
        'company_extractions',
        ['hubspot_portal_id', 'created_at']
    )

    # Note: hubspot_portal_id is nullable initially for data migration
    # After migrating data, you should make it NOT NULL:
    # op.alter_column('users', 'hubspot_portal_id', nullable=False)
    # op.alter_column('company_extractions', 'hubspot_portal_id', nullable=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_extraction_portal_created', table_name='company_extractions')
    op.drop_index('idx_extraction_data_gin', table_name='company_extractions')
    op.drop_index('ix_company_extractions_hubspot_portal_id', table_name='company_extractions')
    op.drop_index('ix_users_hubspot_portal_id', table_name='users')

    # Recreate original index
    op.create_index(
        'idx_extraction_org_created',
        'company_extractions',
        ['organization_id', 'created_at']
    )

    # Drop foreign keys and columns
    op.drop_constraint('fk_company_extractions_hubspot_portal_id', 'company_extractions', type_='foreignkey')
    op.drop_column('company_extractions', 'hubspot_portal_id')
    
    op.drop_constraint('fk_users_hubspot_portal_id', 'users', type_='foreignkey')
    op.drop_column('users', 'hubspot_portal_id')

    # Drop hubspot_portals table
    op.drop_table('hubspot_portals')

