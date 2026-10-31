"""
SQLAlchemy models for Phase 4 Blind Quantum Computing (BQC) experiments and trials.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class BqcExperiment(Base):
    __tablename__ = "bqc_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    num_candidates = Column(Integer, nullable=False)
    num_qubits = Column(Integer, nullable=False)
    cluster_topology = Column(String(50), nullable=False, default="linear")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    trials = relationship("BqcTrial", back_populates="experiment", cascade="all, delete-orphan")


class BqcTrial(Base):
    __tablename__ = "bqc_trials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("bqc_experiments.id", ondelete="CASCADE"), nullable=True, index=True)
    trial_number = Column(Integer, nullable=False)
    mode = Column(String(20), nullable=False, index=True)  # 'mode_a' or 'mode_b'
    vehicle_identifier = Column(String(50), nullable=False)
    num_candidates = Column(Integer, nullable=False)
    selected_depot_index = Column(Integer, nullable=False)
    selected_depot_name = Column(String(100), nullable=False)
    selected_cost = Column(Float, nullable=False)
    all_costs = Column(JSON, nullable=False)
    classical_min_index = Column(Integer, nullable=False)
    correctness = Column(Boolean, nullable=False)
    client_prep_ms = Column(Float, nullable=False, default=0.0)
    server_quantum_ms = Column(Float, nullable=False, default=0.0)
    total_execution_ms = Column(Float, nullable=False)
    client_to_server_bytes = Column(Integer, nullable=False, default=0)
    server_to_client_bytes = Column(Integer, nullable=False, default=0)
    total_wire_bytes = Column(Integer, nullable=False)
    angle_entropy_bits = Column(Float, nullable=False, default=0.0)
    server_learned_gps = Column(Boolean, nullable=False, default=False)
    server_learned_costs = Column(Boolean, nullable=False, default=False)
    server_learned_output = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    experiment = relationship("BqcExperiment", back_populates="trials")
