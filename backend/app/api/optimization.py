"""
FastAPI router for Phase 5 QUBO & Quantum-Inspired Fleet Optimization.
Endpoints:
- GET  /api/optimization/status
- GET  /api/optimization/scenarios
- POST /api/optimization/run
- GET  /api/optimization/experiments
- GET  /api/optimization/experiments/{id}
- DELETE /api/optimization/experiments/{id}
- GET  /api/optimization/analytics
- GET  /api/optimization/compare
"""

from typing import List, Optional, Dict, Any
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db
from app.models.optimization import OptimizationExperiment, OptimizationTrialResult
from app.schemas.optimization import (
    OptimizationRunRequest,
    OptimizationRunResponse,
    OptimizationExperimentListItem,
    OptimizationScenarioInfo,
    OptimizationTrialDetail,
    MethodComparisonSummary
)
from app.services.routing.qubo_routing_service import (
    qubo_routing_service,
    STANDARDIZED_SCENARIOS,
    DEFAULT_CHENNAI_DEPOT
)

router = APIRouter(prefix="/api/optimization", tags=["Quantum-Inspired Fleet Optimization (QUBO)"])


@router.get("/status", summary="Get Fleet Optimization Subsystem Status")
def get_optimization_status(db: Session = Depends(get_db)):
    """Returns the operational status, database connectivity, and solver capabilities."""
    try:
        exp_count = db.query(func.count(OptimizationExperiment.id)).scalar() or 0
        trial_count = db.query(func.count(OptimizationTrialResult.id)).scalar() or 0
    except Exception:
        exp_count = 0
        trial_count = 0

    return {
        "status": "operational",
        "phase": "Phase 5 — QUBO Fleet Optimization",
        "database": "PostgreSQL (Port 5435)",
        "solvers_available": [
            {
                "id": "greedy",
                "name": "Method A — Conventional Greedy Routing",
                "type": "classical_baseline",
                "description": "Deterministic priority and capacity-bounded nearest neighbor insertion with 2-opt."
            },
            {
                "id": "classical_sa",
                "name": "Method B — Classical Simulated Annealing",
                "type": "heuristic_permutation",
                "description": "Stochastic local search in route permutation space with relocate, swap, and 2-opt."
            },
            {
                "id": "qubo_sa",
                "name": "Method C — QUBO Formulation + Simulated Annealing Solver",
                "type": "quantum_inspired",
                "description": "Mathematical binary quadratic Hamiltonian x^T Q x solved via Metropolis sampling."
            },
            {
                "id": "brute_force_exact",
                "name": "Mathematical Ground Truth (Exact Brute Force)",
                "type": "exact_oracle",
                "description": "Exhaustive evaluation of all 2^M states for small instances (M <= 16)."
            }
        ],
        "scenarios": list(STANDARDIZED_SCENARIOS.keys()),
        "persisted_experiments_count": exp_count,
        "persisted_trials_count": trial_count
    }


@router.get("/scenarios", response_model=List[OptimizationScenarioInfo], summary="List Standardized Benchmark Scenarios")
def get_scenarios():
    """Returns predefined reproducible benchmark scenarios (Small, Medium, Large)."""
    result = []
    for sc_id, sc in STANDARDIZED_SCENARIOS.items():
        v_count = sc["num_vehicles"]
        d_count = sc["num_destinations"]
        steps = sc["max_steps"]
        num_vars = v_count * d_count * steps
        state_space = f"2^{num_vars} ≈ {2**num_vars if num_vars <= 30 else f'10^{round(num_vars * 0.301, 1)}'}"
        result.append(
            OptimizationScenarioInfo(
                id=sc["id"],
                name=sc["name"],
                description=sc["description"],
                vehicle_count=v_count,
                destination_count=d_count,
                max_steps=steps,
                num_qubo_variables=num_vars,
                state_space_size=state_space,
                depot=DEFAULT_CHENNAI_DEPOT,
                vehicles=sc["vehicles"],
                destinations=sc["waypoints"]
            )
        )
    return result


@router.post("/run", response_model=OptimizationRunResponse, summary="Execute Comparative Optimization Experiment")
async def run_optimization_experiment(
    req: OptimizationRunRequest,
    db: Session = Depends(get_db)
):
    """
    Executes a multi-trial comparative benchmark between Method A, B, and C.
    Runs non-blocking in a worker thread to ensure the async event loop is preserved.
    """
    # Enforce safe bounds for local execution
    if req.trials > 50:
        raise HTTPException(status_code=400, detail="Trial count cannot exceed 50 for local resource safety.")
    if req.sa_iterations > 5000:
        raise HTTPException(status_code=400, detail="SA iterations capped at 5000.")

    # Run optimization synchronously in thread pool
    try:
        benchmark_data = await asyncio.to_thread(
            qubo_routing_service.run_multi_trial_experiment,
            scenario=req.scenario,
            num_vehicles=req.num_vehicles,
            num_destinations=req.num_destinations,
            method=req.method,
            trials=req.trials,
            random_seed=req.random_seed,
            sa_iterations=req.sa_iterations,
            sa_initial_temp=req.sa_initial_temp,
            sa_cooling_rate=req.sa_cooling_rate,
            penalty_visit=req.penalty_visit,
            penalty_slot=req.penalty_slot,
            penalty_contig=req.penalty_contig,
            penalty_cap=req.penalty_cap,
            include_brute_force=req.include_brute_force
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization solver execution encountered an error: {str(e)}")

    exp_name = req.experiment_name or f"Phase 5 Run: {benchmark_data['scenario_name'].capitalize()} ({benchmark_data['vehicle_count']}V, {benchmark_data['destination_count']}D, {req.trials} trials)"
    benchmark_data["experiment_name"] = exp_name

    exp_id = None
    if req.save_to_db:
        try:
            # Pick best objective from methods
            best_obj = min(
                (summary["best_objective"] for summary in benchmark_data["methods_summary"].values()),
                default=0.0
            )

            exp_record = OptimizationExperiment(
                experiment_name=exp_name,
                scenario_name=benchmark_data["scenario_name"],
                vehicle_count=benchmark_data["vehicle_count"],
                destination_count=benchmark_data["destination_count"],
                method=benchmark_data["method"],
                random_seed=benchmark_data["random_seed"],
                solver_parameters=benchmark_data["solver_parameters"],
                objective_value=best_obj,
                total_distance=min((s["mean_distance_km"] for s in benchmark_data["methods_summary"].values()), default=0.0),
                estimated_travel_time=min((s["mean_travel_time_min"] for s in benchmark_data["methods_summary"].values()), default=0.0) / 60.0,
                execution_time_ms=min((s["median_runtime_ms"] for s in benchmark_data["methods_summary"].values()), default=0.0),
                feasibility_status=any(s["feasibility_percentage"] > 0 for s in benchmark_data["methods_summary"].values()),
                constraint_violations=int(min((s["mean_violations"] for s in benchmark_data["methods_summary"].values()), default=0)),
                summary_metrics=benchmark_data["methods_summary"]
            )
            db.add(exp_record)
            db.commit()
            db.refresh(exp_record)
            exp_id = exp_record.id

            # Save individual trials
            for trial in benchmark_data["trials"]:
                trial_record = OptimizationTrialResult(
                    experiment_id=exp_id,
                    trial_number=trial["trial_number"],
                    method=trial["method"],
                    objective_value=trial["objective_value"],
                    total_distance=trial["total_distance"],
                    estimated_travel_time=trial["estimated_travel_time"],
                    execution_time_ms=trial["execution_time_ms"],
                    feasibility_status=trial["feasibility_status"],
                    constraint_violations=trial["constraint_violations"],
                    solution_data=trial["solution_data"]
                )
                db.add(trial_record)
            db.commit()
        except Exception:
            db.rollback()

    benchmark_data["experiment_id"] = exp_id
    return benchmark_data


@router.get("/experiments", response_model=List[OptimizationExperimentListItem], summary="List Historical Optimization Experiments")
def list_optimization_experiments(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scenario: Optional[str] = None,
    method: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns paginated historical optimization experiment runs."""
    q = db.query(OptimizationExperiment)
    if scenario:
        q = q.filter(OptimizationExperiment.scenario_name == scenario)
    if method:
        q = q.filter(OptimizationExperiment.method == method)

    records = q.order_by(desc(OptimizationExperiment.created_at)).offset(offset).limit(limit).all()
    return [
        OptimizationExperimentListItem(
            id=r.id,
            experiment_name=r.experiment_name,
            scenario_name=r.scenario_name,
            vehicle_count=r.vehicle_count,
            destination_count=r.destination_count,
            method=r.method,
            random_seed=r.random_seed,
            objective_value=r.objective_value,
            total_distance=r.total_distance,
            execution_time_ms=r.execution_time_ms,
            feasibility_status=r.feasibility_status,
            constraint_violations=r.constraint_violations,
            created_at=r.created_at
        )
        for r in records
    ]


@router.get("/experiments/{experiment_id}", summary="Get Detailed Optimization Experiment with Trials")
def get_optimization_experiment_detail(
    experiment_id: int,
    db: Session = Depends(get_db)
):
    """Returns the full record of an experiment including all individual trial executions."""
    exp = db.query(OptimizationExperiment).filter(OptimizationExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment with ID {experiment_id} not found.")

    trials = db.query(OptimizationTrialResult).filter(OptimizationTrialResult.experiment_id == experiment_id).order_by(OptimizationTrialResult.trial_number).all()

    return {
        "id": exp.id,
        "experiment_name": exp.experiment_name,
        "scenario_name": exp.scenario_name,
        "vehicle_count": exp.vehicle_count,
        "destination_count": exp.destination_count,
        "method": exp.method,
        "random_seed": exp.random_seed,
        "solver_parameters": exp.solver_parameters,
        "objective_value": exp.objective_value,
        "total_distance": exp.total_distance,
        "estimated_travel_time": exp.estimated_travel_time,
        "execution_time_ms": exp.execution_time_ms,
        "feasibility_status": exp.feasibility_status,
        "constraint_violations": exp.constraint_violations,
        "summary_metrics": exp.summary_metrics,
        "created_at": exp.created_at,
        "trials": [
            {
                "id": t.id,
                "trial_number": t.trial_number,
                "method": t.method,
                "objective_value": t.objective_value,
                "total_distance": t.total_distance,
                "estimated_travel_time": t.estimated_travel_time,
                "execution_time_ms": t.execution_time_ms,
                "feasibility_status": t.feasibility_status,
                "constraint_violations": t.constraint_violations,
                "solution_data": t.solution_data,
                "created_at": t.created_at
            }
            for t in trials
        ]
    }


@router.delete("/experiments/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Optimization Experiment")
def delete_optimization_experiment(
    experiment_id: int,
    db: Session = Depends(get_db)
):
    """Deletes an experiment record and all associated trial results."""
    exp = db.query(OptimizationExperiment).filter(OptimizationExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    db.delete(exp)
    db.commit()
    return None


@router.get("/analytics", summary="Get Aggregated Fleet Optimization Analytics")
def get_optimization_analytics(db: Session = Depends(get_db)):
    """Returns high-level statistics across all historical optimization runs."""
    total_experiments = db.query(func.count(OptimizationExperiment.id)).scalar() or 0
    total_trials = db.query(func.count(OptimizationTrialResult.id)).scalar() or 0

    trials = db.query(OptimizationTrialResult).all()

    method_stats = {}
    for t in trials:
        m = t.method
        if m not in method_stats:
            method_stats[m] = {
                "count": 0,
                "total_distance": 0.0,
                "total_runtime_ms": 0.0,
                "feasible_count": 0,
                "violations": 0
            }
        method_stats[m]["count"] += 1
        method_stats[m]["total_distance"] += t.total_distance
        method_stats[m]["total_runtime_ms"] += t.execution_time_ms
        if t.feasibility_status:
            method_stats[m]["feasible_count"] += 1
        method_stats[m]["violations"] += t.constraint_violations

    aggregated = []
    for m, s in method_stats.items():
        cnt = s["count"]
        aggregated.append({
            "method": m,
            "trial_count": cnt,
            "avg_distance_km": round(s["total_distance"] / max(1, cnt), 2),
            "avg_runtime_ms": round(s["total_runtime_ms"] / max(1, cnt), 2),
            "feasibility_rate_percent": round((s["feasible_count"] / max(1, cnt)) * 100.0, 1),
            "avg_violations": round(s["violations"] / max(1, cnt), 2)
        })

    return {
        "total_experiments": total_experiments,
        "total_trials": total_trials,
        "method_performance": aggregated
    }


@router.get("/compare", summary="Compare Multiple Optimization Experiments Side-by-Side")
def compare_optimization_experiments(
    experiment_ids: str = Query(..., description="Comma-separated IDs e.g. '1,2,3'"),
    db: Session = Depends(get_db)
):
    """Compares multiple experiments side-by-side for comparative charts."""
    try:
        ids = [int(i.strip()) for i in experiment_ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comma-separated experiment IDs format.")

    if not ids:
        raise HTTPException(status_code=400, detail="At least one experiment ID is required.")

    records = db.query(OptimizationExperiment).filter(OptimizationExperiment.id.in_(ids)).all()
    return [
        {
            "id": r.id,
            "experiment_name": r.experiment_name,
            "scenario_name": r.scenario_name,
            "vehicle_count": r.vehicle_count,
            "destination_count": r.destination_count,
            "method": r.method,
            "objective_value": r.objective_value,
            "total_distance": r.total_distance,
            "execution_time_ms": r.execution_time_ms,
            "feasibility_status": r.feasibility_status,
            "constraint_violations": r.constraint_violations,
            "summary_metrics": r.summary_metrics,
            "created_at": r.created_at
        }
        for r in records
    ]
