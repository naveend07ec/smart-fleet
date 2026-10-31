from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="idle")
    battery_level = Column(Float, nullable=False, default=100.0)

    # Relationship back to vehicle
    vehicle = relationship("Vehicle", back_populates="telemetry_records")

    __table_args__ = (
        Index("idx_telemetry_vehicle_timestamp", "vehicle_id", "timestamp"),
        Index("idx_telemetry_timestamp_desc", timestamp.desc()),
    )

    def __repr__(self):
        return (
            f"<Telemetry id={self.id} vehicle_id={self.vehicle_id} "
            f"speed={self.speed}km/h status='{self.status}' battery={self.battery_level}%>"
        )
