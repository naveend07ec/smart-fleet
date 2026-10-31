from app.services.seed_service import seed_demo_data
from app.models.vehicle import Vehicle

def test_seed_command_idempotency(db_session):
    # First seed run
    run1 = seed_demo_data(db_session)
    assert run1["status"] == "success"
    assert run1["created_vehicles"] > 0
    assert run1["created_telemetry"] > 0
    assert run1["is_idempotent"] is True

    count_after_run1 = db_session.query(Vehicle).count()

    # Second seed run (should be idempotent)
    run2 = seed_demo_data(db_session)
    assert run2["status"] == "success"
    assert run2["created_vehicles"] == 0
    assert run2["created_telemetry"] == 0
    assert run2["already_seeded"] is True

    count_after_run2 = db_session.query(Vehicle).count()
    assert count_after_run1 == count_after_run2
