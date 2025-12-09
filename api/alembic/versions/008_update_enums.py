"""Update Enums

Revision ID: 008
Revises: 007
Create Date: 2025-12-04 12:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'hierarchical' to extractiontype enum
    # PostgreSQL allows adding values to enums inside a transaction (mostly)
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'hierarchical'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from Enums easily
    pass
