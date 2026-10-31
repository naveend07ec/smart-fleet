import psycopg2

con = psycopg2.connect("postgresql://postgres:postgrespassword@localhost:5435/fleet_management")
cur = con.cursor()

tables = ['alembic_version', 'vehicles', 'telemetry', 'ibe_experiments']

for t in tables:
    print(f"\n================ Table: {t} ================")
    cur.execute(f"""
        SELECT column_name, data_type, is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = '{t}'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    for c in cols:
        print(f"  Column: {c[0]:<25} Type: {c[1]:<20} Nullable: {c[2]:<5} MaxLen: {c[3]}")

    cur.execute(f"""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = '{t}';
    """)
    idxs = cur.fetchall()
    print("  Indexes:")
    for idx in idxs:
        print(f"    - {idx[0]}: {idx[1]}")

con.close()
