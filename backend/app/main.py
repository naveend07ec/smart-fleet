from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import Base, engine
from app.api import (
    health_router,
    vehicles_router,
    dashboard_router,
    analytics_router,
    simulation_router,
    ibe_router,
    secure_transmission_router,
    bqc_router,
    routing_router,
    optimization_router
)
from app.services.simulation_service import simulation_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist if connection is available
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Allow server to start up even if DB is still starting or mocked in tests
        pass

    # Auto-start continuous simulation so telemetry updates live in real-time
    try:
        simulation_service.start(
            vehicle_count=settings.SIMULATION_DEFAULT_VEHICLES,
            interval_seconds=settings.SIMULATION_INTERVAL_SECONDS
        )
    except Exception:
        pass

    yield
    # Shutdown: cleanly stop simulation if running
    simulation_service.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler to prevent internal credential/trace leakage
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # In production, logs go to logging facility
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected server error occurred while processing the request.",
            "error_type": exc.__class__.__name__
        }
    )

# Root endpoint
@app.get("/", tags=["Root"])
def root_info():
    return {
        "system": settings.PROJECT_NAME,
        "phase": "Phase 1 - Core Working Prototype",
        "documentation": "/api/docs",
        "health": "/api/health",
        "status": "operational",
        "simulated": True
    }

# Register API Routers
app.include_router(health_router)
app.include_router(vehicles_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)
app.include_router(simulation_router)
app.include_router(ibe_router)
app.include_router(secure_transmission_router)
app.include_router(bqc_router)
app.include_router(routing_router)
app.include_router(optimization_router)


