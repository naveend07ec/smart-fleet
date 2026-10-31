"""
SQLAlchemy models for Phase 5 QUBO / Simulated Annealing Fleet Routing & Optimization.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class RoutingExperiment(Base):
    __tablename__ = "routing_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    num_vehicles = Column(Integer, nullable=False)
    num_waypoints = Column(Integer, nullable=False)
    scenario = Column(String(50), nullable=False, default="urban_delivery")
    
    # Classical Metrics
    classical_distance_km = Column(Float, nullable=False)
    classical_energy_kwh = Column(Float, nullable=False)
    classical_execution_ms = Column(Float, nullable=False)
    classical_routes = Column(JSON, nullable=False)
    
    # QUBO / Simulated Annealing Metrics
    qubo_distance_km = Column(Float, nullable=False)
    qubo_energy_kwh = Column(Float, nullable=False)
    qubo_execution_ms = Column(Float, nullable=False)
    qubo_routes = Column(JSON, nullable=False)
    qubo_iterations = Column(Integer, nullable=False, default=1000)
    convergence_history = Column(JSON, nullable=False)
    
    # Differential KPIs
    distance_reduction_percent = Column(Float, nullable=False)
    energy_savings_percent = Column(Float, nullable=False)
    qubo_valid_solution = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
