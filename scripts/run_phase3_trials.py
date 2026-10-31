import json
from app.database import SessionLocal
from app.services.secure_transmission_service import secure_transmission_service

def main():
    db = SessionLocal()
    try:
        print("Running initial baseline vs IBE protected experiment (5 vehicles, 3 msgs each, medium payload)...")
        res = secure_transmission_service.run_batch_experiment(
            db=db,
            vehicle_count=5,
            messages_per_vehicle=3,
            mode="both",
            payload_category="medium",
            notes="Phase 3 Empirical Benchmark Trial #1"
        )
        print("Batch Complete!")
        print(f"Batch ID: {res.batch_id}")
        print(f"Attempted: {res.total_attempted}, Success: {res.total_successful}, Rejected: {res.total_rejected}")
        print("Metrics:")
        print(json.dumps(res.metrics, indent=2))

        # Also run 1 small payload experiment (3 vehicles, 2 msgs)
        print("\nRunning small payload experiment...")
        res_small = secure_transmission_service.run_batch_experiment(
            db=db,
            vehicle_count=3,
            messages_per_vehicle=2,
            mode="both",
            payload_category="small",
            notes="Phase 3 Empirical Benchmark Trial #2 (Small Payload)"
        )
        print("Small Payload Batch Complete!")

        # Also run 1 large payload experiment (3 vehicles, 2 msgs)
        print("\nRunning large payload experiment...")
        res_large = secure_transmission_service.run_batch_experiment(
            db=db,
            vehicle_count=3,
            messages_per_vehicle=2,
            mode="both",
            payload_category="large",
            notes="Phase 3 Empirical Benchmark Trial #3 (Large Payload)"
        )
        print("Large Payload Batch Complete!")

        # Also run all 6 security demo scenarios to populate audit log
        print("\nRunning security attack demonstration suite...")
        for scenario in [
            "valid_authorized",
            "unauthorized_identity",
            "tampered_ciphertext",
            "tampered_tag",
            "replay_attack",
            "cross_vehicle_substitution"
        ]:
            demo_res = secure_transmission_service.execute_security_demonstration(
                db=db,
                scenario=scenario,
                vehicle_identifier="SIM-VEH-001"
            )
            print(f"  Scenario '{scenario}': Status={demo_res.status}, RejectionReason={demo_res.rejection_reason}")

        print("\nAll empirical trial datasets generated and persisted successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
