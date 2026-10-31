from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine
from app.config import settings
from app.services.simulation_service import simulation_service

router = APIRouter(prefix="/api/health", tags=["System Health"])

@router.get("", summary="System health and connectivity status")
def check_health(db: Session = Depends(get_db)):
    db_ok = False
    db_message = "Connected"
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_message = f"Database error: {str(e)}"

    sim_status = simulation_service.get_status()

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": "ok" if db_ok else "unreachable",
            "dialect": engine.dialect.name,
            "message": db_message
        },
        "simulation": {
            "is_running": sim_status["is_running"],
            "vehicle_count": sim_status["vehicle_count"],
            "ticks_completed": sim_status["tick_count"]
        },
        "is_simulated_system": True
    }
