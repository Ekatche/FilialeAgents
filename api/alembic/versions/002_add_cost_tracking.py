"""Add cost tracking columns to company_extractions

Revision ID: 002
Revises: 001
Create Date: 2025-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cost tracking columns to company_extractions table
    op.add_column('company_extractions',
        sa.Column('cost_usd', sa.Float(), nullable=True, comment='Total cost in USD')
    )
    op.add_column('company_extractions',
        sa.Column('cost_eur', sa.Float(), nullable=True, comment='Total cost in EUR')
    )
    op.add_column('company_extractions',
        sa.Column('total_tokens', sa.Integer(), nullable=True, comment='Total tokens used')
    )
    op.add_column('company_extractions',
        sa.Column('input_tokens', sa.Integer(), nullable=True, comment='Input tokens')
    )
    op.add_column('company_extractions',
        sa.Column('output_tokens', sa.Integer(), nullable=True, comment='Output tokens')
    )
    op.add_column('company_extractions',
        sa.Column('models_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Detailed breakdown by model')
    )

    # Add index on cost_eur for faster queries on expensive searches
    op.create_index('idx_extraction_cost_eur', 'company_extractions', ['cost_eur'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_extraction_cost_eur', table_name='company_extractions')

    # Remove cost tracking columns
    op.drop_column('company_extractions', 'models_usage')
    op.drop_column('company_extractions', 'output_tokens')
    op.drop_column('company_extractions', 'input_tokens')
    op.drop_column('company_extractions', 'total_tokens')
    op.drop_column('company_extractions', 'cost_eur')
    op.drop_column('company_extractions', 'cost_usd')
