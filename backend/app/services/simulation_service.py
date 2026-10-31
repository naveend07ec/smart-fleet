import time
import math
import random
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry

class SimulationService:
    _instance: Optional["SimulationService"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SimulationService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.is_running = False
        self.vehicle_count = settings.SIMULATION_DEFAULT_VEHICLES
        self.interval_seconds = settings.SIMULATION_INTERVAL_SECONDS
        self.random_seed: Optional[int] = None
        self.tick_count = 0
        self.started_at: Optional[datetime] = None
        self.last_tick_at: Optional[datetime] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._rng = random.Random()
        self._vehicle_states: Dict[int, Dict[str, Any]] = {}
        self._state_lock = threading.Lock()

    def get_status(self) -> Dict[str, Any]:
        with self._state_lock:
            return {
                "is_running": self.is_running,
                "vehicle_count": self.vehicle_count,
                "interval_seconds": self.interval_seconds,
                "tick_count": self.tick_count,
                "random_seed": self.random_seed,
                "started_at": self.started_at,
                "last_tick_at": self.last_tick_at,
                "message": (
                    "Simulation is actively producing synthetic telemetry."
                    if self.is_running
                    else "Simulation is stopped."
                ),
                "is_simulated": True
            }

    def start(
        self,
        vehicle_count: int = 25,
        interval_seconds: float = 3.0,
        random_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        with self._state_lock:
            if self.is_running:
                self.vehicle_count = vehicle_count
                self.interval_seconds = max(0.5, min(interval_seconds, 60.0))
                if random_seed is not None:
                    self.random_seed = random_seed
                    self._rng = random.Random(random_seed)
                return {
                    "is_running": True,
                    "vehicle_count": self.vehicle_count,
                    "interval_seconds": self.interval_seconds,
                    "tick_count": self.tick_count,
                    "random_seed": self.random_seed,
                    "started_at": self.started_at,
                    "last_tick_at": self.last_tick_at,
                    "message": "Simulation parameters updated.",
                    "is_simulated": True
                }

            self.vehicle_count = vehicle_count
            self.interval_seconds = max(0.5, min(interval_seconds, 60.0))
            self.random_seed = random_seed
            self.tick_count = 0
            self.started_at = datetime.now(timezone.utc)
            self.last_tick_at = None
            self._stop_event.clear()

            if random_seed is not None:
                self._rng = random.Random(random_seed)
            else:
                self._rng = random.Random()

            self._vehicle_states.clear()
            self.is_running = True

            self._thread = threading.Thread(
                target=self._run_loop,
                name="FleetSimulationThread",
                daemon=True
            )
            self._thread.start()

            return {
                "is_running": True,
                "vehicle_count": self.vehicle_count,
                "interval_seconds": self.interval_seconds,
                "tick_count": self.tick_count,
                "random_seed": self.random_seed,
                "started_at": self.started_at,
                "last_tick_at": self.last_tick_at,
                "message": f"Simulation started successfully with {vehicle_count} vehicles.",
                "is_simulated": True
            }

    def stop(self) -> Dict[str, Any]:
        with self._state_lock:
            if not self.is_running:
                return {
                    "is_running": False,
                    "vehicle_count": self.vehicle_count,
                    "interval_seconds": self.interval_seconds,
                    "tick_count": self.tick_count,
                    "random_seed": self.random_seed,
                    "started_at": self.started_at,
                    "last_tick_at": self.last_tick_at,
                    "message": "Simulation is already stopped.",
                    "is_simulated": True
                }

            self._stop_event.set()
            self.is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        with self._state_lock:
            return {
                "is_running": False,
                "vehicle_count": self.vehicle_count,
                "interval_seconds": self.interval_seconds,
                "tick_count": self.tick_count,
                "random_seed": self.random_seed,
                "started_at": self.started_at,
                "last_tick_at": self.last_tick_at,
                "message": "Simulation stopped cleanly.",
                "is_simulated": True
            }

    def _ensure_vehicles(self, db: Session, target_count: int) -> List[Vehicle]:
        """Ensure at least target_count simulated vehicles exist in the database."""
        vehicles = db.query(Vehicle).order_by(Vehicle.id.asc()).all()
        current_count = len(vehicles)
        if current_count < target_count:
            needed = target_count - current_count
            new_vehicles = []
            for i in range(1, needed + 1):
                idx = current_count + i
                v_ident = f"SIM-VEH-{idx:03d}"
                new_v = Vehicle(
                    vehicle_identifier=v_ident,
                    name=f"Simulated Transport Unit {idx}",
                    status="idle"
                )
                db.add(new_v)
                new_vehicles.append(new_v)
            db.commit()
            for v in new_vehicles:
                db.refresh(v)
            vehicles = db.query(Vehicle).order_by(Vehicle.id.asc()).all()
        return vehicles[:target_count]

    def _initialize_states(self, vehicles: List[Vehicle]):
        for v in vehicles:
            if v.id not in self._vehicle_states:
                lat = self._rng.uniform(
                    settings.SIMULATION_BOUNDS_MIN_LAT,
                    settings.SIMULATION_BOUNDS_MAX_LAT
                )
                lng = self._rng.uniform(
                    settings.SIMULATION_BOUNDS_MIN_LNG,
                    settings.SIMULATION_BOUNDS_MAX_LNG
                )
                heading = self._rng.uniform(0.0, 360.0)
                status_choice = self._rng.choices(
                    ["moving", "idle", "offline"],
                    weights=[0.65, 0.25, 0.10]
                )[0]
                speed = self._rng.uniform(25.0, 65.0) if status_choice == "moving" else 0.0
                battery = round(self._rng.uniform(40.0, 98.0), 1)

                self._vehicle_states[v.id] = {
                    "lat": lat,
                    "lng": lng,
                    "heading": heading,
                    "status": status_choice,
                    "speed": speed,
                    "battery": battery,
                }

    def _run_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()
            try:
                db: Session = SessionLocal()
                try:
                    vehicles = self._ensure_vehicles(db, self.vehicle_count)
                    self._initialize_states(vehicles)

                    now = datetime.now(timezone.utc)
                    new_records = []

                    for v in vehicles:
                        st = self._vehicle_states[v.id]
                        # Occasional status transitions
                        if self._rng.random() < 0.08:
                            if st["status"] == "moving":
                                st["status"] = "idle"
                                st["speed"] = 0.0
                            elif st["status"] == "idle":
                                st["status"] = "moving" if self._rng.random() < 0.8 else "offline"
                                st["speed"] = self._rng.uniform(20.0, 60.0) if st["status"] == "moving" else 0.0
                            elif st["status"] == "offline":
                                st["status"] = "idle"
                                st["speed"] = 0.0

                        if st["status"] == "moving":
                            # Speed fluctuation within realistic transit range
                            st["speed"] = max(25.0, min(85.0, st["speed"] + self._rng.uniform(-2.5, 2.5)))
                            # Gentle heading variation to simulate following roads/corridors
                            st["heading"] = (st["heading"] + self._rng.uniform(-5.0, 5.0)) % 360.0
                            rad = math.radians(st["heading"])
                            
                            # Visual motion scale factor for noticeable real-time vehicle movement
                            VISUAL_MOTION_FACTOR = 4.5
                            dist_km = (st["speed"] / 3600.0) * self.interval_seconds * VISUAL_MOTION_FACTOR
                            delta_lat = (dist_km / 111.0) * math.cos(rad)
                            delta_lng = (dist_km / (111.0 * math.cos(math.radians(st["lat"])))) * math.sin(rad)

                            st["lat"] += delta_lat
                            st["lng"] += delta_lng

                            # Boundary bounce
                            if st["lat"] < settings.SIMULATION_BOUNDS_MIN_LAT or st["lat"] > settings.SIMULATION_BOUNDS_MAX_LAT:
                                st["heading"] = (180.0 - st["heading"]) % 360.0
                                st["lat"] = max(settings.SIMULATION_BOUNDS_MIN_LAT, min(st["lat"], settings.SIMULATION_BOUNDS_MAX_LAT))
                            if st["lng"] < settings.SIMULATION_BOUNDS_MIN_LNG or st["lng"] > settings.SIMULATION_BOUNDS_MAX_LNG:
                                st["heading"] = (360.0 - st["heading"]) % 360.0
                                st["lng"] = max(settings.SIMULATION_BOUNDS_MIN_LNG, min(st["lng"], settings.SIMULATION_BOUNDS_MAX_LNG))

                            # Simulated power indicator consumption
                            st["battery"] = max(5.0, round(st["battery"] - self._rng.uniform(0.05, 0.15), 1))
                        elif st["status"] == "idle":
                            st["speed"] = 0.0
                            # Idle slow charge or tiny drain
                            if st["battery"] < 30.0:
                                st["battery"] = min(100.0, round(st["battery"] + 0.5, 1))
                            else:
                                st["battery"] = max(5.0, round(st["battery"] - 0.01, 1))
                        else:  # offline
                            st["speed"] = 0.0

                        # Update Vehicle status in DB
                        v.status = st["status"]

                        # Append Telemetry record
                        telemetry = Telemetry(
                            vehicle_id=v.id,
                            timestamp=now,
                            latitude=round(st["lat"], 6),
                            longitude=round(st["lng"], 6),
                            speed=round(st["speed"], 2),
                            status=st["status"],
                            battery_level=st["battery"]
                        )
                        new_records.append(telemetry)

                    db.add_all(new_records)
                    db.commit()

                    with self._state_lock:
                        self.tick_count += 1
                        self.last_tick_at = now

                finally:
                    db.close()
            except Exception as e:
                # Log or handle error cleanly without crashing background thread
                pass

            # Sleep remaining time
            elapsed = time.time() - start_time
            sleep_duration = max(0.05, self.interval_seconds - elapsed)
            self._stop_event.wait(timeout=sleep_duration)

simulation_service = SimulationService()
