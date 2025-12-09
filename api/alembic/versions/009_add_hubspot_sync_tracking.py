"""Add HubSpot sync tracking to company_extractions

Revision ID: 009
Revises: 008
Create Date: 2025-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add hubspot_sync_data column to company_extractions table
    op.add_column(
        'company_extractions',
        sa.Column('hubspot_sync_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Tracking des synchronisations HubSpot (IDs, statuts, dates)')
    )
    
    # Create GIN index for efficient JSONB queries
    op.create_index(
        'idx_hubspot_sync_data_gin',
        'company_extractions',
        ['hubspot_sync_data'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_hubspot_sync_data_gin', table_name='company_extractions')
    
    # Drop column
    op.drop_column('company_extractions', 'hubspot_sync_data')

