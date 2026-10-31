import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry
from app.config import settings

DEMO_FLEET_DEFINITIONS = [
    {"identifier": "SIM-DEMO-001", "name": "Metro Transit Shuttle A1", "status": "moving"},
    {"identifier": "SIM-DEMO-002", "name": "Metro Transit Shuttle A2", "status": "moving"},
    {"identifier": "SIM-DEMO-003", "name": "Logistics Van Express 101", "status": "moving"},
    {"identifier": "SIM-DEMO-004", "name": "Logistics Van Express 102", "status": "idle"},
    {"identifier": "SIM-DEMO-005", "name": "Urban Delivery EV 201", "status": "moving"},
    {"identifier": "SIM-DEMO-006", "name": "Urban Delivery EV 202", "status": "idle"},
    {"identifier": "SIM-DEMO-007", "name": "Campus Electric Tram 01", "status": "moving"},
    {"identifier": "SIM-DEMO-008", "name": "Campus Electric Tram 02", "status": "moving"},
    {"identifier": "SIM-DEMO-009", "name": "Heavy Freight Feeder 501", "status": "idle"},
    {"identifier": "SIM-DEMO-010", "name": "Emergency Support Unit E1", "status": "offline"},
    {"identifier": "SIM-DEMO-011", "name": "Port Logistics Hauler P1", "status": "idle"},
    {"identifier": "SIM-DEMO-012", "name": "Autonomous Drone Van D1", "status": "offline"},
]

def seed_demo_data(db: Session, force_telemetry: bool = False) -> Dict[str, Any]:
    """
    Idempotent seeding function:
    Creates demo fleet if not present, and adds initial historical telemetry.
    Repeated runs will NOT duplicate vehicles or balloon telemetry.
    """
    created_vehicles_count = 0
    created_telemetry_count = 0
    existing_demo_vehicles = {
        v.vehicle_identifier: v 
        for v in db.query(Vehicle).filter(Vehicle.vehicle_identifier.like("SIM-DEMO-%")).all()
    }

    rng = random.Random(42)  # Deterministic seed for repeatable demo data
    now = datetime.now(timezone.utc)

    seeded_vehicles = []
    for defn in DEMO_FLEET_DEFINITIONS:
        ident = defn["identifier"]
        if ident in existing_demo_vehicles:
            vehicle = existing_demo_vehicles[ident]
        else:
            vehicle = Vehicle(
                vehicle_identifier=ident,
                name=defn["name"],
                status=defn["status"],
                created_at=now - timedelta(hours=6),
                updated_at=now
            )
            db.add(vehicle)
            db.flush()
            created_vehicles_count += 1
        seeded_vehicles.append(vehicle)

    # For each seeded vehicle, check if telemetry already exists
    for v in seeded_vehicles:
        existing_tel_count = db.query(Telemetry).filter(Telemetry.vehicle_id == v.id).count()
        if existing_tel_count == 0 or force_telemetry:
            # Generate 20 historical points over the last 2 hours
            base_lat = rng.uniform(settings.SIMULATION_BOUNDS_MIN_LAT + 0.02, settings.SIMULATION_BOUNDS_MAX_LAT - 0.02)
            base_lng = rng.uniform(settings.SIMULATION_BOUNDS_MIN_LNG + 0.02, settings.SIMULATION_BOUNDS_MAX_LNG - 0.02)
            battery = rng.uniform(65.0, 95.0)

            for step in range(20):
                t_offset = timedelta(minutes=(20 - step) * 6)
                point_time = now - t_offset

                if v.status == "moving":
                    speed = rng.uniform(25.0, 68.0)
                    base_lat += rng.uniform(-0.003, 0.003)
                    base_lng += rng.uniform(-0.003, 0.003)
                    battery = max(15.0, battery - 0.3)
                    point_status = "moving"
                elif v.status == "idle":
                    speed = 0.0
                    point_status = "idle"
                else:
                    speed = 0.0
                    point_status = "offline"

                tel = Telemetry(
                    vehicle_id=v.id,
                    timestamp=point_time,
                    latitude=round(base_lat, 6),
                    longitude=round(base_lng, 6),
                    speed=round(speed, 2),
                    status=point_status,
                    battery_level=round(battery, 1)
                )
                db.add(tel)
                created_telemetry_count += 1

    db.commit()

    return {
        "status": "success",
        "created_vehicles": created_vehicles_count,
        "created_telemetry": created_telemetry_count,
        "total_demo_vehicles": len(seeded_vehicles),
        "is_idempotent": True,
        "already_seeded": (created_vehicles_count == 0 and created_telemetry_count == 0)
    }
