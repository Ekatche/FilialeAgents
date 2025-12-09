"""Add SessionState model for WebSocket session tracking (replaces Redis)

Revision ID: 005
Revises: 004
Create Date: 2025-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create session_states table
    op.create_table(
        'session_states',
        sa.Column('session_id', sa.String(length=255), primary_key=True),
        sa.Column('progress_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='ExtractionProgress serialized as JSON'),
        sa.Column('results_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Final extraction results'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='TTL for automatic cleanup'),
    )
    
    # Create indexes
    op.create_index('ix_session_states_session_id', 'session_states', ['session_id'])
    op.create_index('idx_session_expires_at', 'session_states', ['expires_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_session_expires_at', table_name='session_states')
    op.drop_index('ix_session_states_session_id', table_name='session_states')
    
    # Drop table
    op.drop_table('session_states')

