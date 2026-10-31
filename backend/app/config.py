import os
import json
from typing import List, Any, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "IoT-Driven Smart Transportation and Fleet Management System"
    VERSION: str = "1.0.0-phase1"
    DESCRIPTION: str = (
        "Phase 1 Core Working Prototype: Simulated IoT fleet telemetry, "
        "real-time monitoring, vehicle management, and fleet analytics."
    )
    ENVIRONMENT: str = "development"
    
    # Primary Database: PostgreSQL (port 5435 for isolated container setup)
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgrespassword@localhost:5435/fleet_management",
        description="Database connection string (PostgreSQL primary; SQLite strictly for isolated test fixtures)"
    )
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Origins (accepts list or comma-separated string)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    # Simulation defaults & geographic demo bounding box (Chennai region demo coordinates)
    SIMULATION_DEFAULT_VEHICLES: int = 25
    SIMULATION_INTERVAL_SECONDS: float = 3.0
    SIMULATION_BOUNDS_MIN_LAT: float = 12.9000
    SIMULATION_BOUNDS_MAX_LAT: float = 13.1500
    SIMULATION_BOUNDS_MIN_LNG: float = 80.1000
    SIMULATION_BOUNDS_MAX_LNG: float = 80.3000
    
    # Optional internal token for protecting write / simulation endpoints in hosted deployments
    API_WRITE_KEY: str = ""
    
    # Security guard: prevent accidental master secret reinitialization in IBE
    ALLOW_IBE_REINIT: bool = False

    model_config = SettingsConfigDict(
        env_file=(".env", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
