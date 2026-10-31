from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_identifier = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="idle", index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    telemetry_records = relationship(
        "Telemetry",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="desc(Telemetry.timestamp)"
    )

    def __repr__(self):
        return f"<Vehicle id={self.id} identifier='{self.vehicle_identifier}' name='{self.name}' status='{self.status}'>"
