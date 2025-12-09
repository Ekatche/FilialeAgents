"""add password_hash to users

Revision ID: 006
Revises: 005
Create Date: 2025-01-04 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter le champ password_hash pour l'authentification locale
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))

    # Rendre hubspot_user_id nullable pour permettre l'auth locale
    op.alter_column('users', 'hubspot_user_id',
               existing_type=sa.String(255),
               nullable=True)


def downgrade():
    # Retirer le champ password_hash
    op.drop_column('users', 'password_hash')

    # Remettre hubspot_user_id non-nullable
    op.alter_column('users', 'hubspot_user_id',
               existing_type=sa.String(255),
               nullable=False)
