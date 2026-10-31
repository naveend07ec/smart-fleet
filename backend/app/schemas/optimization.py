"""
Pydantic schemas for Phase 5 QUBO & Quantum-Inspired Fleet Optimization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class WaypointNode(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    demand: int = Field(default=15, ge=1, le=100)
    priority: int = Field(default=1, ge=1, le=5)


class DepotNode(BaseModel):
    id: str = "depot-central"
    name: str = "Central Logistics Hub"
    latitude: float = 13.0827
    longitude: float = 80.2707


class FleetVehicle(BaseModel):
    id: str
    name: str
    capacity: int = Field(default=60, ge=10, le=500)
    battery_range_km: float = Field(default=85.0, ge=10.0, le=400.0)
    energy_rate_kwh_per_km: float = Field(default=0.22, ge=0.05, le=1.0)


class OptimizationRunRequest(BaseModel):
    scenario: str = Field(default="small", description="'small' (2v, 3d), 'medium' (3v, 5d), 'large' (5v, 8d) or 'custom'")
    num_vehicles: Optional[int] = Field(default=None, ge=1, le=10)
    num_destinations: Optional[int] = Field(default=None, ge=2, le=20)
    method: str = Field(default="all_comparative", description="'greedy', 'classical_sa', 'qubo_sa', or 'all_comparative'")
    trials: int = Field(default=1, ge=1, le=50, description="Number of independent trials")
    random_seed: int = Field(default=42, ge=0, le=999999)
    sa_iterations: int = Field(default=1000, ge=100, le=5000)
    sa_initial_temp: float = Field(default=100.0, ge=1.0, le=1000.0)
    sa_cooling_rate: float = Field(default=0.985, ge=0.8, le=0.999)
    penalty_visit: float = Field(default=150.0, ge=10.0, le=2000.0)
    penalty_slot: float = Field(default=120.0, ge=10.0, le=2000.0)
    penalty_contig: float = Field(default=80.0, ge=10.0, le=2000.0)
    penalty_cap: float = Field(default=100.0, ge=10.0, le=2000.0)
    experiment_name: Optional[str] = None
    save_to_db: bool = Field(default=True)
    include_brute_force: bool = Field(default=False, description="Run exact enumeration if state space is small (<= 4096 states)")


class OptimizationTrialDetail(BaseModel):
    trial_number: int
    method: str
    objective_value: float
    total_distance: float
    estimated_travel_time: float
    execution_time_ms: float
    feasibility_status: bool
    constraint_violations: int
    solution_data: Dict[str, Any]


class MethodComparisonSummary(BaseModel):
    method: str
    method_name: str
    trial_count: int
    feasibility_percentage: float
    best_objective: float
    mean_objective: float
    std_objective: float
    mean_distance_km: float
    mean_travel_time_min: float
    median_runtime_ms: float
    p95_runtime_ms: float
    mean_violations: float
    best_solution_routes: List[Dict[str, Any]]
    convergence_history: Optional[List[Dict[str, Any]]] = None


class OptimizationRunResponse(BaseModel):
    experiment_id: Optional[int] = None
    experiment_name: Optional[str] = None
    scenario_name: str
    vehicle_count: int
    destination_count: int
    method: str
    random_seed: int
    solver_parameters: Dict[str, Any]
    depot: Dict[str, Any]
    destinations: List[Dict[str, Any]]
    vehicles: List[Dict[str, Any]]
    methods_summary: Dict[str, MethodComparisonSummary]
    trials: List[OptimizationTrialDetail]
    brute_force_exact: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OptimizationExperimentListItem(BaseModel):
    id: int
    experiment_name: str
    scenario_name: str
    vehicle_count: int
    destination_count: int
    method: str
    random_seed: int
    objective_value: Optional[float]
    total_distance: Optional[float]
    execution_time_ms: Optional[float]
    feasibility_status: bool
    constraint_violations: int
    created_at: datetime


class OptimizationScenarioInfo(BaseModel):
    id: str
    name: str
    description: str
    vehicle_count: int
    destination_count: int
    max_steps: int
    num_qubo_variables: int
    state_space_size: str
    depot: Dict[str, Any]
    vehicles: List[Dict[str, Any]]
    destinations: List[Dict[str, Any]]
