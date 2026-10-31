"""005_bqc_experiments

Revision ID: 005_bqc_experiments
Revises: 004_ed25519_sender_auth
Create Date: 2026-10-30 14:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_bqc_experiments'
down_revision: Union[str, None] = '004_ed25519_sender_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create bqc_experiments table
    op.create_table(
        'bqc_experiments',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('num_candidates', sa.Integer(), nullable=False),
        sa.Column('num_qubits', sa.Integer(), nullable=False),
        sa.Column('cluster_topology', sa.String(length=50), nullable=False, server_default='linear'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create bqc_trials table
    op.create_table(
        'bqc_trials',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('experiment_id', sa.Integer(), nullable=True),
        sa.Column('trial_number', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),  # 'mode_a' or 'mode_b'
        sa.Column('vehicle_identifier', sa.String(length=50), nullable=False),
        sa.Column('num_candidates', sa.Integer(), nullable=False),
        sa.Column('selected_depot_index', sa.Integer(), nullable=False),
        sa.Column('selected_depot_name', sa.String(length=100), nullable=False),
        sa.Column('selected_cost', sa.Float(), nullable=False),
        sa.Column('all_costs', sa.JSON(), nullable=False),
        sa.Column('classical_min_index', sa.Integer(), nullable=False),
        sa.Column('correctness', sa.Boolean(), nullable=False),
        sa.Column('client_prep_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('server_quantum_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_execution_ms', sa.Float(), nullable=False),
        sa.Column('client_to_server_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('server_to_client_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_wire_bytes', sa.Integer(), nullable=False),
        sa.Column('angle_entropy_bits', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('server_learned_gps', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('server_learned_costs', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('server_learned_output', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['experiment_id'], ['bqc_experiments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bqc_trials_exp_id', 'bqc_trials', ['experiment_id'])
    op.create_index('idx_bqc_trials_mode', 'bqc_trials', ['mode'])


def downgrade() -> None:
    op.drop_index('idx_bqc_trials_mode', table_name='bqc_trials')
    op.drop_index('idx_bqc_trials_exp_id', table_name='bqc_trials')
    op.drop_table('bqc_trials')
    op.drop_table('bqc_experiments')
