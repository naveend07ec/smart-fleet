from fastapi import APIRouter, HTTPException, status
from app.schemas.simulation import SimulationStartRequest, SimulationStatusResponse
from app.services.simulation_service import simulation_service

router = APIRouter(prefix="/api/simulation", tags=["Simulation Engine Controls"])

@router.get("/status", response_model=SimulationStatusResponse, summary="Get simulator execution status")
def get_simulation_status():
    """Returns the current state of the telemetry simulation engine."""
    return simulation_service.get_status()

@router.post("/start", response_model=SimulationStatusResponse, summary="Start synthetic telemetry generation")
def start_simulation(payload: SimulationStartRequest):
    """
    Start generating synthetic vehicle telemetry.
    Supports fleet scenarios of 10, 25, 50 (or up to 100) vehicles.
    Deterministic simulation can be activated by providing an optional random_seed.
    """
    result = simulation_service.start(
        vehicle_count=payload.vehicle_count,
        interval_seconds=payload.interval_seconds,
        random_seed=payload.random_seed
    )
    return result

@router.post("/stop", response_model=SimulationStatusResponse, summary="Stop synthetic telemetry generation")
def stop_simulation():
    """
    Cleanly halts the background simulation loop and avoids runaway background threads.
    """
    result = simulation_service.stop()
    return result
