from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Index
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class VehicleEnrollment(Base):
    __tablename__ = "vehicle_enrollments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_identifier = Column(String(64), unique=True, index=True, nullable=False)
    assigned_identity = Column(String(120), unique=True, index=True, nullable=False)
    is_enrolled = Column(Boolean, nullable=False, default=True)
    enrolled_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    signing_public_key = Column(String(128), nullable=True)  # Ed25519 public verification key (Base64)
    notes = Column(String(255), nullable=True)

    def __repr__(self):
        return (
            f"<VehicleEnrollment id={self.id} vehicle='{self.vehicle_identifier}' "
            f"identity='{self.assigned_identity}' enrolled={self.is_enrolled}>"
        )


class SecureTransmission(Base):
    __tablename__ = "secure_transmissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transmission_id = Column(String(64), unique=True, index=True, nullable=False)
    batch_id = Column(String(64), index=True, nullable=True)
    vehicle_identifier = Column(String(64), index=True, nullable=False)
    sender_identity = Column(String(120), index=True, nullable=False)
    recipient_identity = Column(String(120), index=True, nullable=False)
    transmission_mode = Column(String(20), index=True, nullable=False)  # 'plaintext' | 'ibe_protected'
    payload_category = Column(String(20), nullable=False, default="medium")  # 'small' | 'medium' | 'large'
    original_payload_size_bytes = Column(Integer, nullable=False)
    encrypted_envelope_size_bytes = Column(Integer, nullable=False)
    payload_expansion_bytes = Column(Integer, nullable=False, default=0)
    payload_expansion_percent = Column(Float, nullable=False, default=0.0)
    encryption_duration_ms = Column(Float, nullable=False, default=0.0)
    decryption_duration_ms = Column(Float, nullable=False, default=0.0)
    server_processing_duration_ms = Column(Float, nullable=False, default=0.0)
    total_duration_ms = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), index=True, nullable=False, default="success")  # 'success' | 'rejected' | 'failed'
    rejection_reason = Column(String(255), nullable=True)
    tampered_flag = Column(Boolean, nullable=False, default=False)
    replayed_flag = Column(Boolean, nullable=False, default=False)
    unauthorized_identity_flag = Column(Boolean, nullable=False, default=False)
    signature_b64 = Column(String(255), nullable=True)  # Ed25519 digital signature
    signature_verified = Column(Boolean, nullable=False, default=False)  # True when signature verified
    message_id = Column(String(64), index=True, nullable=True)
    message_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_secure_tx_created_at_desc", created_at.desc()),
        Index("idx_secure_tx_mode_status", transmission_mode, status),
    )

    def __repr__(self):
        return (
            f"<SecureTransmission id={self.id} tx='{self.transmission_id}' "
            f"mode='{self.transmission_mode}' status='{self.status}'>"
        )


class ProcessedMessageCache(Base):
    __tablename__ = "processed_message_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(String(64), unique=True, index=True, nullable=False)
    sender_identity = Column(String(120), index=True, nullable=False)
    received_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<ProcessedMessageCache message_id='{self.message_id}' sender='{self.sender_identity}'>"
