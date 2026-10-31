"""006_qubo_routing_experiments

Revision ID: 006_qubo_routing_experiments
Revises: 005_bqc_experiments
Create Date: 2026-10-31 10:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_qubo_routing_experiments'
down_revision: Union[str, None] = '005_bqc_experiments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('routing_experiments'):
        op.create_table(
            'routing_experiments',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('num_vehicles', sa.Integer(), nullable=False),
            sa.Column('num_waypoints', sa.Integer(), nullable=False),
            sa.Column('scenario', sa.String(length=50), nullable=False, server_default='urban_delivery'),
            sa.Column('classical_distance_km', sa.Float(), nullable=False),
            sa.Column('classical_energy_kwh', sa.Float(), nullable=False),
            sa.Column('classical_execution_ms', sa.Float(), nullable=False),
            sa.Column('classical_routes', sa.JSON(), nullable=False),
            sa.Column('qubo_distance_km', sa.Float(), nullable=False),
            sa.Column('qubo_energy_kwh', sa.Float(), nullable=False),
            sa.Column('qubo_execution_ms', sa.Float(), nullable=False),
            sa.Column('qubo_routes', sa.JSON(), nullable=False),
            sa.Column('qubo_iterations', sa.Integer(), nullable=False, server_default='1000'),
            sa.Column('convergence_history', sa.JSON(), nullable=False),
            sa.Column('distance_reduction_percent', sa.Float(), nullable=False),
            sa.Column('energy_savings_percent', sa.Float(), nullable=False),
            sa.Column('qubo_valid_solution', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )



def downgrade() -> None:
    op.drop_table('routing_experiments')
