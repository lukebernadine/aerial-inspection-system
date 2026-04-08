"""
ingest_flight.py
Parses an AirData CSV export and inserts a flight record into the database.

AirData column mapping (verified against Jul-14th-2023-01-32PM-Flight-Airdata.csv):
  datetime(utc)           -> date
  latitude                -> gps_lat        (first non-zero value)
  longitude               -> gps_lon        (first non-zero value)
  max_altitude(feet)      -> altitude_ft
  time(millisecond)       -> duration_min   (max value / 60000)
  max_distance(feet)      -> distance_ft
  max_speed(mph)          -> max_speed_mph
  battery_percent         -> battery_start_pct (first row) / battery_end_pct (last row)
"""

import csv
import sys
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from project root
sys.path.append(str(Path(__file__).parent.parent))
from core.storage import insert_flight_record


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return default


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return default


def ingest_csv(
    csv_path: str,
    location_name: str,
    drone_model: str,
    pilot_name: str,
    weather_conditions: str,
    notes: str = "",
    flight_id: str = None,
) -> dict:
    """
    Parse an AirData CSV and return a flight_record dict ready for storage.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        raise ValueError("CSV is empty — no data rows found.")

    # Strip whitespace from all keys (AirData sometimes adds spaces)
    rows = [{k.strip(): v for k, v in row.items()} for row in rows]

    first_row = rows[0]
    last_row = rows[-1]

    # --- Date: take from first row datetime(utc) ---
    raw_dt = first_row.get("datetime(utc)", "")
    try:
        dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y-%m-%d")
    except ValueError:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # --- GPS: first row with non-zero lat/lon ---
    gps_lat, gps_lon = 0.0, 0.0
    for row in rows:
        lat = parse_float(row.get("latitude", "0"))
        lon = parse_float(row.get("longitude", "0"))
        if lat != 0.0 and lon != 0.0:
            gps_lat, gps_lon = lat, lon
            break

    # --- Altitude: max_altitude(feet) from last row (cumulative max) ---
    altitude_ft = parse_float(last_row.get("max_altitude(feet)", "0"))

    # --- Duration: max time(millisecond) -> minutes ---
    max_ms = max(parse_float(row.get("time(millisecond)", "0")) for row in rows)
    duration_min = round(max_ms / 60000, 2)

    # --- Distance: max_distance(feet) from last row ---
    distance_ft = parse_float(last_row.get("max_distance(feet)", "0"))

    # --- Max speed ---
    max_speed_mph = parse_float(last_row.get("max_speed(mph)", "0"))

    # --- Battery ---
    battery_start_pct = parse_int(first_row.get("battery_percent", "0"))
    battery_end_pct   = parse_int(last_row.get("battery_percent", "0"))

    flight_record = {
        "flight_id":          flight_id or f"FLT-{uuid.uuid4().hex[:8].upper()}",
        "inspection_id":      None,  # linked later via score_and_merge.py
        "date":               date_str,
        "location_name":      location_name,
        "gps_lat":            gps_lat,
        "gps_lon":            gps_lon,
        "altitude_ft":        altitude_ft,
        "duration_min":       duration_min,
        "distance_ft":        distance_ft,
        "max_speed_mph":      max_speed_mph,
        "drone_model":        drone_model,
        "weather_conditions": weather_conditions,
        "battery_start_pct":  battery_start_pct,
        "battery_end_pct":    battery_end_pct,
        "pilot_name":         pilot_name,
        "notes":              notes,
    }

    return flight_record


def main():
    parser = argparse.ArgumentParser(description="Ingest an AirData CSV into the inspection database.")
    parser.add_argument("csv_path",           help="Path to AirData CSV export")
    parser.add_argument("--location",         required=True, help="Human-readable location name")
    parser.add_argument("--drone",            required=True, help="Drone model (e.g. 'DJI Air 2S')")
    parser.add_argument("--pilot",            required=True, help="Pilot name")
    parser.add_argument("--weather",          required=True, help="Weather conditions")
    parser.add_argument("--notes",            default="",   help="Optional notes")
    parser.add_argument("--flight-id",        default=None, help="Optional manual flight ID override")
    parser.add_argument("--dry-run", action="store_true",   help="Parse only — do not write to DB")
    args = parser.parse_args()

    print(f"\n📂 Parsing: {args.csv_path}")
    record = ingest_csv(
        csv_path=args.csv_path,
        location_name=args.location,
        drone_model=args.drone,
        pilot_name=args.pilot,
        weather_conditions=args.weather,
        notes=args.notes,
        flight_id=args.flight_id,
    )

    print("\n✅ Parsed flight record:")
    for k, v in record.items():
        print(f"   {k:<22} {v}")

    if args.dry_run:
        print("\n⚠️  Dry run — not written to database.")
    else:
        insert_flight_record(record)
        print(f"\n💾 Saved to database with flight_id: {record['flight_id']}")

    return record


if __name__ == "__main__":
    main()
