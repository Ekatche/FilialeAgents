"""Remove Organization model and migrate to HubSpotPortal

Revision ID: 004
Revises: 003
Create Date: 2025-01-XX

Migration steps:
1. Add is_active to hubspot_portals
2. Migrate data from organizations to hubspot_portals (if needed)
3. Remove organization_id from users
4. Remove organization_id from company_extractions (if exists)
5. Rename organization_usage to portal_usage
6. Drop organizations table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add is_active column to hubspot_portals (migrated from Organization)
    op.add_column('hubspot_portals',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )

    # Step 2: Migrate is_active from organizations to hubspot_portals if needed
    op.execute("""
        UPDATE hubspot_portals hp
        SET
            is_active = COALESCE((SELECT is_active FROM organizations o WHERE o.hubspot_company_id::text = hp.hubspot_portal_id::text), true)
        WHERE EXISTS (
            SELECT 1 FROM organizations o
            WHERE o.hubspot_company_id::text = hp.hubspot_portal_id::text
        )
    """)

    # Step 3: Remove organization_id from users
    op.drop_constraint('users_organization_id_fkey', 'users', type_='foreignkey')
    op.drop_index('ix_users_organization_id', table_name='users', if_exists=True)
    op.drop_column('users', 'organization_id')

    # Step 4: Remove organization_id from company_extractions (if it exists)
    # Note: organization_id might have been removed in migration 003, but we check anyway
    op.drop_constraint('company_extractions_organization_id_fkey', 'company_extractions', type_='foreignkey', if_exists=True)
    op.drop_index('idx_extraction_org_created', table_name='company_extractions', if_exists=True)
    op.drop_column('company_extractions', 'organization_id', if_exists=True)

    # Step 5: Rename organization_usage to portal_usage
    op.rename_table('organization_usage', 'portal_usage')
    
    # Update foreign key and column name
    op.drop_constraint('organization_usage_organization_id_fkey', 'portal_usage', type_='foreignkey', if_exists=True)
    # Rename column using SQL (Alembic doesn't have rename_column method)
    op.execute('ALTER TABLE portal_usage RENAME COLUMN organization_id TO hubspot_portal_id')
    op.create_foreign_key(
        'fk_portal_usage_hubspot_portal_id',
        'portal_usage', 'hubspot_portals',
        ['hubspot_portal_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Update indexes
    op.drop_index('idx_usage_org_month', table_name='portal_usage', if_exists=True)
    op.drop_constraint('uq_org_month', 'portal_usage', type_='unique', if_exists=True)
    op.create_index('idx_usage_portal_month', 'portal_usage', ['hubspot_portal_id', 'month'])
    op.create_unique_constraint('uq_portal_month', 'portal_usage', ['hubspot_portal_id', 'month'])

    # Step 6: Drop organizations table
    op.drop_table('organizations')


def downgrade() -> None:
    # Recreate organizations table
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

    # Revert portal_usage to organization_usage
    op.drop_constraint('uq_portal_month', 'portal_usage', type_='unique')
    op.drop_index('idx_usage_portal_month', table_name='portal_usage')
    op.drop_constraint('fk_portal_usage_hubspot_portal_id', 'portal_usage', type_='foreignkey')
    op.execute('ALTER TABLE portal_usage RENAME COLUMN hubspot_portal_id TO organization_id')
    op.create_foreign_key(
        'organization_usage_organization_id_fkey',
        'portal_usage', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_usage_org_month', 'portal_usage', ['organization_id', 'month'])
    op.create_unique_constraint('uq_org_month', 'portal_usage', ['organization_id', 'month'])
    op.rename_table('portal_usage', 'organization_usage')

    # Re-add organization_id to company_extractions
    op.add_column('company_extractions',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'company_extractions_organization_id_fkey',
        'company_extractions', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_extraction_org_created', 'company_extractions', ['organization_id', 'created_at'])

    # Re-add organization_id to users
    op.add_column('users',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'users_organization_id_fkey',
        'users', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])

    # Remove columns from hubspot_portals
    op.drop_column('hubspot_portals', 'is_active')
    op.drop_column('hubspot_portals', 'max_searches_per_month')
    op.drop_column('hubspot_portals', 'plan_type')

