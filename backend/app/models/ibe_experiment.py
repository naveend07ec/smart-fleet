from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Index
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class IBEExperiment(Base):
    __tablename__ = "ibe_experiments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    experiment_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    scheme = Column(String(64), nullable=False, default="Boneh-Franklin-BN128-AES256GCM")
    recipient_identity = Column(String(120), nullable=False, index=True)
    unauthorized_identity = Column(String(120), nullable=True)
    payload_size_bytes = Column(Integer, nullable=False)
    ciphertext_size_bytes = Column(Integer, nullable=False)
    encryption_duration_ms = Column(Float, nullable=False)
    decryption_duration_ms = Column(Float, nullable=False)
    authorized_success = Column(Boolean, nullable=False, default=True)
    unauthorized_rejected = Column(Boolean, nullable=False, default=True)
    tamper_check_passed = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="success")
    notes = Column(String(255), nullable=True)

    __table_args__ = (
        Index("idx_ibe_experiments_timestamp_desc", timestamp.desc()),
    )

    def __repr__(self):
        return (
            f"<IBEExperiment id={self.id} experiment_id='{self.experiment_id}' "
            f"recipient='{self.recipient_identity}' status='{self.status}'>"
        )
