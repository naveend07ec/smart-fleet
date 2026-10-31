import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    VehicleDetailResponse,
    VehiclePaginationResponse
)
from app.schemas.telemetry import (
    TelemetryResponse,
    TelemetryPaginationResponse
)

router = APIRouter(prefix="/api/vehicles", tags=["Vehicle Management"])

def resolve_vehicle(db: Session, identifier: str) -> Vehicle:
    """Helper to resolve vehicle by either primary key integer ID or vehicle_identifier string."""
    query = db.query(Vehicle)
    if identifier.isdigit():
        vehicle = query.filter(or_(Vehicle.id == int(identifier), Vehicle.vehicle_identifier == identifier)).first()
    else:
        vehicle = query.filter(Vehicle.vehicle_identifier == identifier).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle '{identifier}' not found in simulated fleet."
        )
    return vehicle

def attach_latest_telemetry(db: Session, vehicle: Vehicle) -> Optional[Telemetry]:
    return (
        db.query(Telemetry)
        .filter(Telemetry.vehicle_id == vehicle.id)
        .order_by(desc(Telemetry.timestamp))
        .first()
    )

# ------------------------------------------------------------------------------
# Read-Only Public Demonstration Endpoints
# ------------------------------------------------------------------------------

@router.get("", response_model=VehiclePaginationResponse, summary="List all simulated vehicles with filtering and pagination")
def list_vehicles(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by vehicle ID or name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: moving, idle, offline"),
    db: Session = Depends(get_db)
):
    query = db.query(Vehicle)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Vehicle.vehicle_identifier.ilike(search_pattern),
                Vehicle.name.ilike(search_pattern)
            )
        )

    if status_filter:
        query = query.filter(Vehicle.status == status_filter.lower().strip())

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    vehicles = (
        query.order_by(Vehicle.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for v in vehicles:
        latest = attach_latest_telemetry(db, v)
        v_dict = {
            "id": v.id,
            "vehicle_identifier": v.vehicle_identifier,
            "name": v.name,
            "status": v.status,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
            "latest_telemetry": latest
        }
        items.append(v_dict)

    return VehiclePaginationResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{vehicle_id}", response_model=VehicleDetailResponse, summary="Get details and recent telemetry sample for a vehicle")
def get_vehicle_details(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = resolve_vehicle(db, vehicle_id)
    latest = attach_latest_telemetry(db, vehicle)
    
    total_tel = db.query(Telemetry).filter(Telemetry.vehicle_id == vehicle.id).count()
    recent_records = (
        db.query(Telemetry)
        .filter(Telemetry.vehicle_id == vehicle.id)
        .order_by(desc(Telemetry.timestamp))
        .limit(20)
        .all()
    )

    return VehicleDetailResponse(
        id=vehicle.id,
        vehicle_identifier=vehicle.vehicle_identifier,
        name=vehicle.name,
        status=vehicle.status,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        latest_telemetry=latest,
        telemetry_history_sample=recent_records,
        total_telemetry_records=total_tel
    )

@router.get("/{vehicle_id}/telemetry", response_model=TelemetryPaginationResponse, summary="Get paginated historical telemetry for a vehicle")
def get_vehicle_telemetry(
    vehicle_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db)
):
    vehicle = resolve_vehicle(db, vehicle_id)

    query = db.query(Telemetry).filter(Telemetry.vehicle_id == vehicle.id)
    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    records = (
        query.order_by(desc(Telemetry.timestamp))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return TelemetryPaginationResponse(
        items=records,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

# ------------------------------------------------------------------------------
# Write Endpoints (Notice: Require authentication / access protection in public hosting)
# ------------------------------------------------------------------------------

@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new simulated vehicle (Admin/Write)"
)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)):
    # Validate unique vehicle_identifier
    existing = db.query(Vehicle).filter(Vehicle.vehicle_identifier == payload.vehicle_identifier.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle identifier '{payload.vehicle_identifier}' already exists."
        )

    valid_statuses = {"moving", "idle", "offline"}
    if payload.status.lower() not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status must be one of: {', '.join(valid_statuses)}"
        )

    vehicle = Vehicle(
        vehicle_identifier=payload.vehicle_identifier.strip(),
        name=payload.name.strip(),
        status=payload.status.lower().strip()
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return VehicleResponse(
        id=vehicle.id,
        vehicle_identifier=vehicle.vehicle_identifier,
        name=vehicle.name,
        status=vehicle.status,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        latest_telemetry=None
    )

@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Update vehicle details (Admin/Write)"
)
def update_vehicle(vehicle_id: str, payload: VehicleUpdate, db: Session = Depends(get_db)):
    vehicle = resolve_vehicle(db, vehicle_id)

    if payload.status is not None:
        valid_statuses = {"moving", "idle", "offline"}
        if payload.status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status must be one of: {', '.join(valid_statuses)}"
            )
        vehicle.status = payload.status.lower().strip()

    if payload.name is not None:
        vehicle.name = payload.name.strip()

    db.commit()
    db.refresh(vehicle)
    latest = attach_latest_telemetry(db, vehicle)

    return VehicleResponse(
        id=vehicle.id,
        vehicle_identifier=vehicle.vehicle_identifier,
        name=vehicle.name,
        status=vehicle.status,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        latest_telemetry=latest
    )

@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a vehicle and its telemetry (Admin/Write)"
)
def delete_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = resolve_vehicle(db, vehicle_id)
    ident = vehicle.vehicle_identifier
    db.delete(vehicle)
    db.commit()
    return {"status": "success", "message": f"Vehicle '{ident}' and associated telemetry deleted."}
