import os
import sys

# Ensure backend folder is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Determine Test Database:
# Default: PostgreSQL test database (fleet_management_test on port 5435)
# SQLite fallback: enabled only if USE_SQLITE_TESTS is explicitly set
use_sqlite = os.environ.get("USE_SQLITE_TESTS", "").lower() in ("1", "true", "yes")

if use_sqlite:
    TEST_DATABASE_URL = "sqlite:///./test_fleet.db"
else:
    TEST_DATABASE_URL = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgrespassword@localhost:5435/fleet_management_test"
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.services.simulation_service import simulation_service

connect_args = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    simulation_service.stop()
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
