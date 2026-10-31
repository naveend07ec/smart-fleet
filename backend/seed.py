import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Base, engine
from app.services.seed_service import seed_demo_data

def main():
    print("[Seed] Initializing database tables if needed...")
    Base.metadata.create_all(bind=engine)
    
    print("[Seed] Seeding demo fleet and historical synthetic telemetry...")
    db = SessionLocal()
    try:
        result = seed_demo_data(db)
        print(f"[Seed Result] Status: {result['status']}")
        print(f"[Seed Result] Newly created vehicles: {result['created_vehicles']}")
        print(f"[Seed Result] Newly created telemetry points: {result['created_telemetry']}")
        print(f"[Seed Result] Total demo vehicles present: {result['total_demo_vehicles']}")
        if result['already_seeded']:
            print("[Seed Notice] Demo fleet was already seeded. No duplicate records were created.")
        else:
            print("[Seed Success] Demo fleet successfully seeded.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
