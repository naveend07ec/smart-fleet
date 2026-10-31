"""
Pydantic schemas for Phase 5 QUBO / Simulated Annealing Fleet Routing & Optimization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    demand: int = Field(default=15, ge=1, le=100, description="Package / delivery load in units")
    priority: int = Field(default=1, ge=1, le=5, description="Priority weight (1-5)")


class DepotLocation(BaseModel):
    id: str = "depot-central"
    name: str = "Central Logistics Hub"
    latitude: float = 13.0827
    longitude: float = 80.2707


class VehicleConfig(BaseModel):
    id: str
    name: str
    capacity: int = Field(default=60, ge=10, le=500)
    battery_range_km: float = Field(default=80.0, ge=20.0, le=300.0)
    energy_rate_kwh_per_km: float = Field(default=0.25, ge=0.05, le=1.0)


class RoutingOptimizationRequest(BaseModel):
    scenario: str = Field(default="urban_express", description="Scenario name")
    depot: DepotLocation = Field(default_factory=DepotLocation)
    waypoints: Optional[List[Waypoint]] = None
    vehicles: Optional[List[VehicleConfig]] = None
    sa_iterations: int = Field(default=1000, ge=100, le=5000, description="Simulated Annealing iterations")
    sa_initial_temp: float = Field(default=100.0, ge=10.0, le=1000.0)
    sa_cooling_rate: float = Field(default=0.985, ge=0.90, le=0.999)
    save_experiment: bool = Field(default=True, description="Save record to database")
    experiment_name: Optional[str] = None


class VehicleRoute(BaseModel):
    vehicle_id: str
    vehicle_name: str
    stop_sequence: List[Dict[str, Any]]
    total_distance_km: float
    total_energy_kwh: float
    total_demand_delivered: int
    capacity_utilized_percent: float
    feasible: bool


class MethodRoutingResult(BaseModel):
    method_name: str
    routes: List[VehicleRoute]
    total_distance_km: float
    total_energy_kwh: float
    execution_time_ms: float
    max_route_distance_km: float
    route_variance_km: float
    all_feasible: bool
    qubo_energy_score: Optional[float] = None


class RoutingOptimizationResponse(BaseModel):
    scenario: str
    num_vehicles: int
    num_waypoints: int
    depot: DepotLocation
    classical_heuristic: MethodRoutingResult
    qubo_simulated_annealing: MethodRoutingResult
    differential_kpis: Dict[str, Any]
    convergence_history: List[Dict[str, Any]]
    experiment_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoutingExperimentListItem(BaseModel):
    id: int
    name: str
    scenario: str
    num_vehicles: int
    num_waypoints: int
    classical_distance_km: float
    qubo_distance_km: float
    distance_reduction_percent: float
    energy_savings_percent: float
    created_at: datetime
