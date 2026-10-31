"""
FastAPI router for Phase 5 QUBO / Simulated Annealing Fleet Routing & Optimization.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.routing import RoutingExperiment
from app.schemas.routing import (
    RoutingOptimizationRequest,
    RoutingOptimizationResponse,
    RoutingExperimentListItem,
    DepotLocation,
    Waypoint,
    VehicleConfig
)
from app.services.routing.qubo_routing_service import (
    qubo_routing_service,
    DEFAULT_CHENNAI_DEPOT,
    DEFAULT_CHENNAI_WAYPOINTS,
    DEFAULT_VEHICLES
)

router = APIRouter(prefix="/api/routing", tags=["QUBO Fleet Routing"])


@router.get("/defaults", summary="Get default Chennai depot, waypoints, and fleet configuration")
def get_routing_defaults():
    """Returns baseline parameters and presets for route optimization."""
    return {
        "depot": DEFAULT_CHENNAI_DEPOT,
        "waypoints": DEFAULT_CHENNAI_WAYPOINTS,
        "vehicles": DEFAULT_VEHICLES,
        "scenarios": [
            {
                "id": "urban_delivery",
                "name": "Chennai Urban Express Distribution",
                "description": "8 commercial waypoints across central & south Chennai served by 3 EV vans."
            },
            {
                "id": "emergency_medical",
                "name": "Critical Medical Supply Dispatch",
                "description": "High-priority hospital and clinic drops requiring strict load balance and minimal delay."
            },
            {
                "id": "ev_range_constrained",
                "name": "EV Green Transit Optimization",
                "description": "Battery-conscious delivery with quadratic energy penalty terms in the QUBO objective."
            }
        ]
    }


@router.post("/optimize", response_model=RoutingOptimizationResponse, summary="Execute Classical vs QUBO/SA comparative route optimization")
def optimize_routes(
    req: RoutingOptimizationRequest,
    db: Session = Depends(get_db)
):
    """
    Executes a side-by-side run of:
    1. Classical Greedy Nearest Neighbor + 2-Opt local search
    2. QUBO formulation with Simulated Annealing (Metropolis-Hastings sampling)
    """
    if req.waypoints is not None and len(req.waypoints) == 0:
        raise HTTPException(status_code=400, detail="At least one waypoint is required.")
    if req.vehicles is not None and len(req.vehicles) == 0:
        raise HTTPException(status_code=400, detail="At least one vehicle is required.")

    depot_dict = (req.depot.model_dump() if hasattr(req.depot, "model_dump") else req.depot.dict()) if req.depot else DEFAULT_CHENNAI_DEPOT
    
    if req.waypoints is not None:
        waypoints_dict = [w.model_dump() if hasattr(w, "model_dump") else w.dict() for w in req.waypoints]
    else:
        waypoints_dict = DEFAULT_CHENNAI_WAYPOINTS

    if req.vehicles is not None:
        vehicles_dict = [v.model_dump() if hasattr(v, "model_dump") else v.dict() for v in req.vehicles]
    else:
        vehicles_dict = DEFAULT_VEHICLES


    result = qubo_routing_service.run_optimization_benchmark(
        depot=depot_dict,
        waypoints=waypoints_dict,
        vehicles=vehicles_dict,
        sa_iterations=req.sa_iterations,
        sa_initial_temp=req.sa_initial_temp,
        sa_cooling_rate=req.sa_cooling_rate,
        scenario=req.scenario
    )

    exp_id = None
    if req.save_experiment:
        try:
            exp_name = req.experiment_name or f"QUBO Run: {req.scenario} ({len(waypoints_dict)} wp, {len(vehicles_dict)} veh)"
            exp_record = RoutingExperiment(
                name=exp_name,
                description=f"Comparison of Classical vs QUBO/SA under {req.scenario}",
                num_vehicles=result["num_vehicles"],
                num_waypoints=result["num_waypoints"],
                scenario=result["scenario"],
                classical_distance_km=result["classical_heuristic"]["total_distance_km"],
                classical_energy_kwh=result["classical_heuristic"]["total_energy_kwh"],
                classical_execution_ms=result["classical_heuristic"]["execution_time_ms"],
                classical_routes=result["classical_heuristic"]["routes"],
                qubo_distance_km=result["qubo_simulated_annealing"]["total_distance_km"],
                qubo_energy_kwh=result["qubo_simulated_annealing"]["total_energy_kwh"],
                qubo_execution_ms=result["qubo_simulated_annealing"]["execution_time_ms"],
                qubo_routes=result["qubo_simulated_annealing"]["routes"],
                qubo_iterations=req.sa_iterations,
                convergence_history=result["convergence_history"],
                distance_reduction_percent=result["differential_kpis"]["distance_reduction_percent"],
                energy_savings_percent=result["differential_kpis"]["energy_savings_percent"],
                qubo_valid_solution=result["qubo_simulated_annealing"]["all_feasible"]
            )
            db.add(exp_record)
            db.commit()
            db.refresh(exp_record)
            exp_id = exp_record.id
        except Exception:
            db.rollback()

    result["experiment_id"] = exp_id
    return result


@router.get("/experiments", response_model=List[RoutingExperimentListItem], summary="List historical routing experiment benchmarks")
def list_experiments(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Returns paginated historical routing optimization trials."""
    records = db.query(RoutingExperiment).order_by(desc(RoutingExperiment.created_at)).offset(offset).limit(limit).all()
    return [
        RoutingExperimentListItem(
            id=r.id,
            name=r.name,
            scenario=r.scenario,
            num_vehicles=r.num_vehicles,
            num_waypoints=r.num_waypoints,
            classical_distance_km=r.classical_distance_km,
            qubo_distance_km=r.qubo_distance_km,
            distance_reduction_percent=r.distance_reduction_percent,
            energy_savings_percent=r.energy_savings_percent,
            created_at=r.created_at
        )
        for r in records
    ]


@router.get("/experiments/{experiment_id}", summary="Get detailed routing experiment record")
def get_experiment_detail(
    experiment_id: int,
    db: Session = Depends(get_db)
):
    """Retrieves full route geometry, stop sequence, and convergence telemetry for an experiment."""
    record = db.query(RoutingExperiment).filter(RoutingExperiment.id == experiment_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Routing experiment not found.")
    return record


@router.delete("/experiments/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete experiment record")
def delete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db)
):
    """Deletes a routing experiment."""
    record = db.query(RoutingExperiment).filter(RoutingExperiment.id == experiment_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Routing experiment not found.")
    db.delete(record)
    db.commit()
    return None
