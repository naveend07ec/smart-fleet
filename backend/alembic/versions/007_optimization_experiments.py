"""007_optimization_experiments

Revision ID: 007_optimization_experiments
Revises: 006_qubo_routing_experiments
Create Date: 2026-10-31 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_optimization_experiments'
down_revision: Union[str, None] = '006_qubo_routing_experiments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    if not insp.has_table('optimization_experiments'):
        op.create_table(
            'optimization_experiments',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('experiment_name', sa.String(length=120), nullable=False),
            sa.Column('scenario_name', sa.String(length=50), nullable=False),
            sa.Column('vehicle_count', sa.Integer(), nullable=False),
            sa.Column('destination_count', sa.Integer(), nullable=False),
            sa.Column('method', sa.String(length=50), nullable=False),
            sa.Column('random_seed', sa.Integer(), nullable=False, server_default='42'),
            sa.Column('solver_parameters', sa.JSON(), nullable=False),
            sa.Column('objective_value', sa.Float(), nullable=True),
            sa.Column('total_distance', sa.Float(), nullable=True),
            sa.Column('estimated_travel_time', sa.Float(), nullable=True),
            sa.Column('execution_time_ms', sa.Float(), nullable=True),
            sa.Column('feasibility_status', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('constraint_violations', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('summary_metrics', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_optimization_experiments_scenario', 'optimization_experiments', ['scenario_name'])
        op.create_index('ix_optimization_experiments_method', 'optimization_experiments', ['method'])

    if not insp.has_table('optimization_trial_results'):
        op.create_table(
            'optimization_trial_results',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('experiment_id', sa.Integer(), nullable=False),
            sa.Column('trial_number', sa.Integer(), nullable=False),
            sa.Column('method', sa.String(length=50), nullable=False),
            sa.Column('objective_value', sa.Float(), nullable=False),
            sa.Column('total_distance', sa.Float(), nullable=False),
            sa.Column('estimated_travel_time', sa.Float(), nullable=False),
            sa.Column('execution_time_ms', sa.Float(), nullable=False),
            sa.Column('feasibility_status', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('constraint_violations', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('solution_data', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['experiment_id'], ['optimization_experiments.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_optimization_trial_results_experiment_id', 'optimization_trial_results', ['experiment_id'])
        op.create_index('ix_optimization_trial_results_method', 'optimization_trial_results', ['method'])


def downgrade() -> None:
    op.drop_table('optimization_trial_results')
    op.drop_table('optimization_experiments')
