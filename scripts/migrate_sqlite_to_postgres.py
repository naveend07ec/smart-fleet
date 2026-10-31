import sys
import os
import argparse
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "fleet_management.db")
DEFAULT_PG_URL = "postgresql://postgres:postgrespassword@localhost:5435/fleet_management"

def parse_args():
    parser = argparse.ArgumentParser(description="Safely migrate records from legacy SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", default=SQLITE_PATH, help="Path to SQLite database file")
    parser.add_argument("--pg-url", default=os.environ.get("DATABASE_URL", DEFAULT_PG_URL), help="Target PostgreSQL connection URL")
    parser.add_argument("--execute", action="store_true", help="Actually execute the migration (default is dry-run)")
    return parser.parse_args()

def inspect_source_and_target(sqlite_conn, pg_conn):
    s_cur = sqlite_conn.cursor()
    p_cur = pg_conn.cursor()

    tables = ["vehicles", "telemetry", "ibe_experiments"]
    summary = {}

    for t in tables:
        s_count = s_cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        p_cur.execute(f"SELECT count(*) FROM {t}")
        p_count = p_cur.fetchone()[0]
        summary[t] = {"sqlite_count": s_count, "postgres_count": p_count}

    return summary

def main():
    args = parse_args()
    print("==================================================================")
    print("       SQLITE -> POSTGRESQL DATA MIGRATION AUDIT & TOOL           ")
    print("==================================================================")
    print(f"Source SQLite:      {args.sqlite_path}")
    print(f"Target PostgreSQL:  {args.pg_url.split('@')[-1] if '@' in args.pg_url else args.pg_url}")
    print(f"Execution Mode:     {'LIVE EXECUTION' if args.execute else 'DRY RUN ONLY (No changes written)'}")
    print("==================================================================\n")

    if not os.path.exists(args.sqlite_path):
        print(f"[Error] SQLite source database not found at '{args.sqlite_path}'.")
        sys.exit(1)

    s_conn = sqlite3.connect(args.sqlite_path)
    try:
        p_conn = psycopg2.connect(args.pg_url)
    except Exception as e:
        print(f"[Error] Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    summary = inspect_source_and_target(s_conn, p_conn)
    print("[Pre-Migration State Assessment]")
    for t, c in summary.items():
        print(f"  - Table '{t}': SQLite = {c['sqlite_count']} records | PostgreSQL = {c['postgres_count']} records")

    if not args.execute:
        print("\n[Notice] Running in DRY-RUN mode. No data was transferred.")
        print("[Notice] To execute the migration, run with the '--execute' flag.")
        s_conn.close()
        p_conn.close()
        return

    # Live migration with transaction
    s_cur = s_conn.cursor()
    p_cur = p_conn.cursor()

    try:
        # 1. Migrate vehicles
        print("\n[Step 1/3] Migrating vehicles...")
        vehicles = s_cur.execute("SELECT id, vehicle_identifier, name, status, created_at, updated_at FROM vehicles ORDER BY id").fetchall()
        migrated_v = 0
        for v in vehicles:
            p_cur.execute("""
                INSERT INTO vehicles (id, vehicle_identifier, name, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (vehicle_identifier) DO NOTHING
            """, v)
            if p_cur.rowcount > 0:
                migrated_v += 1
        # Reset vehicles sequence
        p_cur.execute("SELECT setval(pg_get_serial_sequence('vehicles', 'id'), COALESCE(MAX(id), 1)) FROM vehicles")
        print(f"  -> Migrated {migrated_v} new vehicles (total in source: {len(vehicles)})")

        # 2. Migrate telemetry
        print("\n[Step 2/3] Migrating telemetry records...")
        telemetries = s_cur.execute("SELECT id, vehicle_id, timestamp, latitude, longitude, speed, status, battery_level FROM telemetry ORDER BY id").fetchall()
        migrated_t = 0
        if telemetries:
            # Batch insert in chunks of 1000
            chunk_size = 1000
            for i in range(0, len(telemetries), chunk_size):
                chunk = telemetries[i:i + chunk_size]
                execute_values(p_cur, """
                    INSERT INTO telemetry (id, vehicle_id, timestamp, latitude, longitude, speed, status, battery_level)
                    VALUES %s
                    ON CONFLICT (id) DO NOTHING
                """, chunk)
                migrated_t += len(chunk)
            p_cur.execute("SELECT setval(pg_get_serial_sequence('telemetry', 'id'), COALESCE(MAX(id), 1)) FROM telemetry")
        print(f"  -> Inserted {migrated_t} telemetry rows")

        # 3. Migrate ibe_experiments
        print("\n[Step 3/3] Migrating IBE experiment records...")
        exps = s_cur.execute("""
            SELECT id, experiment_id, timestamp, scheme, recipient_identity, unauthorized_identity,
                   payload_size_bytes, ciphertext_size_bytes, encryption_duration_ms, decryption_duration_ms,
                   authorized_success, unauthorized_rejected, tamper_check_passed, status, notes
            FROM ibe_experiments ORDER BY id
        """).fetchall()
        migrated_e = 0
        for exp in exps:
            # Convert SQLite boolean ints (0/1) to Python bools
            exp_list = list(exp)
            exp_list[10] = bool(exp_list[10])
            exp_list[11] = bool(exp_list[11])
            exp_list[12] = bool(exp_list[12])
            p_cur.execute("""
                INSERT INTO ibe_experiments (
                    id, experiment_id, timestamp, scheme, recipient_identity, unauthorized_identity,
                    payload_size_bytes, ciphertext_size_bytes, encryption_duration_ms, decryption_duration_ms,
                    authorized_success, unauthorized_rejected, tamper_check_passed, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (experiment_id) DO NOTHING
            """, exp_list)
            if p_cur.rowcount > 0:
                migrated_e += 1
        p_cur.execute("SELECT setval(pg_get_serial_sequence('ibe_experiments', 'id'), COALESCE(MAX(id), 1)) FROM ibe_experiments")
        print(f"  -> Migrated {migrated_e} new IBE experiments")

        p_conn.commit()
        print("\n[Success] Migration transaction committed successfully!")

        post_summary = inspect_source_and_target(s_conn, p_conn)
        print("\n[Post-Migration State]")
        for t, c in post_summary.items():
            print(f"  - Table '{t}': SQLite = {c['sqlite_count']} | PostgreSQL = {c['postgres_count']}")

    except Exception as e:
        p_conn.rollback()
        print(f"\n[Error] Migration failed: {e}. Transaction rolled back.")
        sys.exit(1)
    finally:
        s_conn.close()
        p_conn.close()

if __name__ == "__main__":
    main()
