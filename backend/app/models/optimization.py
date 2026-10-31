"""
SQLAlchemy models for Phase 5 QUBO & Quantum-Inspired Fleet Optimization Experiments.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class OptimizationExperiment(Base):
    __tablename__ = "optimization_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_name = Column(String(120), nullable=False)
    scenario_name = Column(String(50), nullable=False)
    vehicle_count = Column(Integer, nullable=False)
    destination_count = Column(Integer, nullable=False)
    method = Column(String(50), nullable=False)  # "greedy", "classical_sa", "qubo_sa", "all_comparative"
    random_seed = Column(Integer, nullable=False, default=42)
    solver_parameters = Column(JSON, nullable=False)
    
    # Aggregated metrics for the overall experiment
    objective_value = Column(Float, nullable=True)
    total_distance = Column(Float, nullable=True)
    estimated_travel_time = Column(Float, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    feasibility_status = Column(Boolean, nullable=False, default=True)
    constraint_violations = Column(Integer, nullable=False, default=0)
    summary_metrics = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    trials = relationship("OptimizationTrialResult", back_populates="experiment", cascade="all, delete-orphan")


class OptimizationTrialResult(Base):
    __tablename__ = "optimization_trial_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("optimization_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    trial_number = Column(Integer, nullable=False)
    method = Column(String(50), nullable=False, index=True)
    objective_value = Column(Float, nullable=False)
    total_distance = Column(Float, nullable=False)
    estimated_travel_time = Column(Float, nullable=False)
    execution_time_ms = Column(Float, nullable=False)
    feasibility_status = Column(Boolean, nullable=False, default=True)
    constraint_violations = Column(Integer, nullable=False, default=0)
    solution_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    experiment = relationship("OptimizationExperiment", back_populates="trials")
