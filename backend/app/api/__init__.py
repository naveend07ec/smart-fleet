from app.api.health import router as health_router
from app.api.vehicles import router as vehicles_router
from app.api.dashboard import router as dashboard_router
from app.api.analytics import router as analytics_router
from app.api.simulation import router as simulation_router
from app.api.ibe import router as ibe_router
from app.api.secure_transmission import router as secure_transmission_router
from app.api.bqc import router as bqc_router
from app.api.routing import router as routing_router
from app.api.optimization import router as optimization_router

__all__ = [
    "health_router",
    "vehicles_router",
    "dashboard_router",
    "analytics_router",
    "simulation_router",
    "ibe_router",
    "secure_transmission_router",
    "bqc_router",
    "routing_router",
    "optimization_router"
]


