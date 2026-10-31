"""
Pydantic Schemas for Phase 4 Blind Quantum Computing (BQC) APIs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CandidateDepot(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    congestion: float = Field(default=0.2, ge=0.0, le=1.0)

class BqcDemonstrationRequest(BaseModel):
    vehicle_id: Optional[int] = Field(None, description="Optional vehicle ID to use real-time GPS/battery")
    num_candidates: int = Field(default=2, ge=2, le=4, description="Number of candidate depots (2 or 4)")
    cluster_topology: str = Field(default="linear", description="'linear' for 2 candidates, 'ladder' for 4 candidates")
    custom_depots: Optional[List[CandidateDepot]] = None
    seed: Optional[int] = Field(default=42, description="Random seed for reproducible demonstration")

class BqcTrialResult(BaseModel):
    mode: str
    selected_depot_index: int
    selected_depot_name: str
    selected_cost: float
    all_costs: List[float]
    execution_time_ms: float
    wire_bytes: int
    server_visibility: str
    privacy_guarantee: str

class BqcComparisonResponse(BaseModel):
    num_candidates: int
    candidate_names: List[str]
    mode_a: Dict[str, Any]
    mode_b: Dict[str, Any]
    correctness_verified: bool
    wire_expansion_percent: float
    privacy_contrast: Dict[str, str]

class BqcBatchTrialRequest(BaseModel):
    num_candidates: int = Field(default=2, ge=2, le=4)
    trials_per_mode: int = Field(default=10, ge=1, le=50)
    cluster_topology: str = Field(default="linear")
    experiment_name: Optional[str] = None

class ModeSummary(BaseModel):
    median_latency_ms: float
    mean_latency_ms: float
    p95_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    mean_wire_bytes: float

class BqcBatchSummaryResponse(BaseModel):
    experiment_id: int
    num_candidates: int
    trials_executed_per_mode: int
    mode_a: ModeSummary
    mode_b: ModeSummary
    wire_expansion_percent: float
    algorithmic_correctness_rate: float
    universal_blindness_verified_rate: float
    mean_angle_entropy_bits: float
    total_variation_distance: float
    distinguishability_verdict: str

class BqcExperimentListItem(BaseModel):
    id: int
    name: str
    num_candidates: int
    num_qubits: int
    cluster_topology: str
    created_at: datetime
    total_trials: int
    correctness_rate: float
