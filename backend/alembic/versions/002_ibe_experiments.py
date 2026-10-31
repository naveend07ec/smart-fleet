"""002_ibe_experiments

Revision ID: 002_ibe_experiments
Revises: 001_initial_schema
Create Date: 2026-10-29 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_ibe_experiments'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'ibe_experiments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('experiment_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheme', sa.String(length=64), nullable=False),
        sa.Column('recipient_identity', sa.String(length=120), nullable=False),
        sa.Column('unauthorized_identity', sa.String(length=120), nullable=True),
        sa.Column('payload_size_bytes', sa.Integer(), nullable=False),
        sa.Column('ciphertext_size_bytes', sa.Integer(), nullable=False),
        sa.Column('encryption_duration_ms', sa.Float(), nullable=False),
        sa.Column('decryption_duration_ms', sa.Float(), nullable=False),
        sa.Column('authorized_success', sa.Boolean(), nullable=False),
        sa.Column('unauthorized_rejected', sa.Boolean(), nullable=False),
        sa.Column('tamper_check_passed', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ibe_experiments_id'), 'ibe_experiments', ['id'], unique=False)
    op.create_index(op.f('ix_ibe_experiments_experiment_id'), 'ibe_experiments', ['experiment_id'], unique=True)
    op.create_index(op.f('ix_ibe_experiments_timestamp'), 'ibe_experiments', ['timestamp'], unique=False)
    op.create_index(op.f('ix_ibe_experiments_recipient_identity'), 'ibe_experiments', ['recipient_identity'], unique=False)
    op.create_index('idx_ibe_experiments_timestamp_desc', 'ibe_experiments', [sa.text('timestamp DESC')], unique=False)

def downgrade() -> None:
    op.drop_index('idx_ibe_experiments_timestamp_desc', table_name='ibe_experiments')
    op.drop_index(op.f('ix_ibe_experiments_recipient_identity'), table_name='ibe_experiments')
    op.drop_index(op.f('ix_ibe_experiments_timestamp'), table_name='ibe_experiments')
    op.drop_index(op.f('ix_ibe_experiments_experiment_id'), table_name='ibe_experiments')
    op.drop_index(op.f('ix_ibe_experiments_id'), table_name='ibe_experiments')
    op.drop_table('ibe_experiments')
