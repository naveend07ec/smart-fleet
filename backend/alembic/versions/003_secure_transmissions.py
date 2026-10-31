"""003_secure_transmissions

Revision ID: 003_secure_transmissions
Revises: 002_ibe_experiments
Create Date: 2026-10-30 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_secure_transmissions'
down_revision: Union[str, None] = '002_ibe_experiments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. vehicle_enrollments table
    op.create_table(
        'vehicle_enrollments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vehicle_identifier', sa.String(length=64), nullable=False),
        sa.Column('assigned_identity', sa.String(length=120), nullable=False),
        sa.Column('is_enrolled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicle_enrollments_id'), 'vehicle_enrollments', ['id'], unique=False)
    op.create_index(op.f('ix_vehicle_enrollments_vehicle_identifier'), 'vehicle_enrollments', ['vehicle_identifier'], unique=True)
    op.create_index(op.f('ix_vehicle_enrollments_assigned_identity'), 'vehicle_enrollments', ['assigned_identity'], unique=True)

    # 2. secure_transmissions table
    op.create_table(
        'secure_transmissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('transmission_id', sa.String(length=64), nullable=False),
        sa.Column('batch_id', sa.String(length=64), nullable=True),
        sa.Column('vehicle_identifier', sa.String(length=64), nullable=False),
        sa.Column('sender_identity', sa.String(length=120), nullable=False),
        sa.Column('recipient_identity', sa.String(length=120), nullable=False),
        sa.Column('transmission_mode', sa.String(length=20), nullable=False),
        sa.Column('payload_category', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('original_payload_size_bytes', sa.Integer(), nullable=False),
        sa.Column('encrypted_envelope_size_bytes', sa.Integer(), nullable=False),
        sa.Column('payload_expansion_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload_expansion_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('encryption_duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('decryption_duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('server_processing_duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('rejection_reason', sa.String(length=255), nullable=True),
        sa.Column('tampered_flag', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('replayed_flag', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('unauthorized_identity_flag', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('message_id', sa.String(length=64), nullable=True),
        sa.Column('message_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_secure_transmissions_id'), 'secure_transmissions', ['id'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_transmission_id'), 'secure_transmissions', ['transmission_id'], unique=True)
    op.create_index(op.f('ix_secure_transmissions_batch_id'), 'secure_transmissions', ['batch_id'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_vehicle_identifier'), 'secure_transmissions', ['vehicle_identifier'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_sender_identity'), 'secure_transmissions', ['sender_identity'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_recipient_identity'), 'secure_transmissions', ['recipient_identity'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_transmission_mode'), 'secure_transmissions', ['transmission_mode'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_status'), 'secure_transmissions', ['status'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_message_id'), 'secure_transmissions', ['message_id'], unique=False)
    op.create_index(op.f('ix_secure_transmissions_created_at'), 'secure_transmissions', ['created_at'], unique=False)
    op.create_index('idx_secure_tx_created_at_desc', 'secure_transmissions', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_secure_tx_mode_status', 'secure_transmissions', ['transmission_mode', 'status'], unique=False)

    # 3. processed_message_cache table
    op.create_table(
        'processed_message_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.String(length=64), nullable=False),
        sa.Column('sender_identity', sa.String(length=120), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_processed_message_cache_id'), 'processed_message_cache', ['id'], unique=False)
    op.create_index(op.f('ix_processed_message_cache_message_id'), 'processed_message_cache', ['message_id'], unique=True)
    op.create_index(op.f('ix_processed_message_cache_sender_identity'), 'processed_message_cache', ['sender_identity'], unique=False)
    op.create_index(op.f('ix_processed_message_cache_received_at'), 'processed_message_cache', ['received_at'], unique=False)

def downgrade() -> None:
    op.drop_table('processed_message_cache')
    op.drop_table('secure_transmissions')
    op.drop_table('vehicle_enrollments')
