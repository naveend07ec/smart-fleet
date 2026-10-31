"""004_ed25519_sender_auth

Revision ID: 004_ed25519_sender_auth
Revises: 003_secure_transmissions
Create Date: 2026-10-30 12:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_ed25519_sender_auth'
down_revision: Union[str, None] = '003_secure_transmissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add signing_public_key to vehicle_enrollments
    op.add_column(
        'vehicle_enrollments',
        sa.Column('signing_public_key', sa.String(length=128), nullable=True)
    )

    # 2. Add signature_b64 and signature_verified to secure_transmissions
    op.add_column(
        'secure_transmissions',
        sa.Column('signature_b64', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'secure_transmissions',
        sa.Column('signature_verified', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )

def downgrade() -> None:
    op.drop_column('secure_transmissions', 'signature_verified')
    op.drop_column('secure_transmissions', 'signature_b64')
    op.drop_column('vehicle_enrollments', 'signing_public_key')
