import sqlite3
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH      = PROJECT_ROOT / "database" / "inspections.db"
SCHEMA_PATH  = PROJECT_ROOT / "database" / "schema.sql"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialise_db():
    with get_connection() as conn:
        schema = SCHEMA_PATH.read_text()
        conn.executescript(schema)
    print(f"✅ Database initialised at: {DB_PATH}")


def insert_flight_record(record):
    sql = """
    INSERT OR REPLACE INTO flight_records
        (flight_id, inspection_id, date, location_name, gps_lat, gps_lon,
         altitude_ft, duration_min, distance_ft, max_speed_mph, drone_model,
         weather_conditions, battery_start_pct, battery_end_pct, pilot_name, notes)
    VALUES
        (:flight_id, :inspection_id, :date, :location_name, :gps_lat, :gps_lon,
         :altitude_ft, :duration_min, :distance_ft, :max_speed_mph, :drone_model,
         :weather_conditions, :battery_start_pct, :battery_end_pct, :pilot_name, :notes)
    """
    with get_connection() as conn:
        conn.execute(sql, record)


def get_flight_record(flight_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM flight_records WHERE flight_id = ?", (flight_id,)).fetchone()
    return dict(row) if row else None


def get_all_flights():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM flight_records ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]


def link_inspection_to_flight(flight_id, inspection_id):
    with get_connection() as conn:
        conn.execute("UPDATE flight_records SET inspection_id = ? WHERE flight_id = ?", (inspection_id, flight_id))


def insert_inspection_record(record):
    sql = """
    INSERT OR REPLACE INTO inspection_records
        (inspection_id, flight_id, date, property_address, inspection_type,
         inspector_name, findings, overall_risk_score, risk_tier, status)
    VALUES
        (:inspection_id, :flight_id, :date, :property_address, :inspection_type,
         :inspector_name, :findings, :overall_risk_score, :risk_tier, :status)
    """
    with get_connection() as conn:
        conn.execute(sql, record)


def get_inspection_record(inspection_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM inspection_records WHERE inspection_id = ?", (inspection_id,)).fetchone()
    return dict(row) if row else None


def get_all_draft_inspections():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM inspection_records WHERE status = 'Draft'").fetchall()
    return [dict(r) for r in rows]


def get_all_inspections():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM inspection_records ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]


def update_inspection_scores(inspection_id, score, tier):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "UPDATE inspection_records SET overall_risk_score = ?, risk_tier = ?, status = 'Complete', updated_at = ? WHERE inspection_id = ?",
            (score, tier, now, inspection_id),
        )


def get_inspection_with_flight(inspection_id):
    sql = """
    SELECT i.*, f.location_name, f.gps_lat, f.gps_lon, f.altitude_ft,
           f.duration_min, f.distance_ft, f.max_speed_mph, f.drone_model,
           f.weather_conditions, f.battery_start_pct, f.battery_end_pct, f.pilot_name
    FROM inspection_records i
    LEFT JOIN flight_records f ON i.flight_id = f.flight_id
    WHERE i.inspection_id = ?
    """
    with get_connection() as conn:
        row = conn.execute(sql, (inspection_id,)).fetchone()
    return dict(row) if row else None
