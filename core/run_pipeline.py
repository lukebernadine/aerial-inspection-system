"""
run_pipeline.py
Master runner — executes the full pipeline for one inspection.

Steps:
  1. Ingest AirData CSV  (ingest_flight.py)
  2. Score findings      (score_and_merge.py)
  3. Generate report     (report_generator.py)

The CLI findings entry (ingest_inspection.py) is intentionally
NOT automated here — it requires human input.

Usage:
  python run_pipeline.py \\
    --csv path/to/airdata.csv \\
    --inspection-id INS-XXXXXXXX \\
    --location "123 Main St" \\
    --drone "DJI Air 2S" \\
    --pilot "Jane Smith" \\
    --weather "Clear, 72F, light wind"
"""

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.ingest_flight import ingest_csv
from core.storage import insert_flight_record, get_inspection_record, link_inspection_to_flight
from core.score_and_merge import process_inspection
from core.report_generator import generate_report


def run_pipeline(
    csv_path: str,
    inspection_id: str,
    location: str,
    drone: str,
    pilot: str,
    weather: str,
    notes: str = "",
):
    print("\n" + "="*55)
    print("  AERIAL INSPECTION PIPELINE — FULL RUN")
    print("="*55)

    # Step 1: Ingest flight
    print("\n[1/3] Ingesting flight data...")
    flight = ingest_csv(
        csv_path=csv_path,
        location_name=location,
        drone_model=drone,
        pilot_name=pilot,
        weather_conditions=weather,
        notes=notes,
    )
    insert_flight_record(flight)
    flight_id = flight["flight_id"]
    print(f"      Flight ID: {flight_id}")

    # Link flight to inspection
    inspection = get_inspection_record(inspection_id)
    if not inspection:
        print(f"\n❌ Inspection '{inspection_id}' not found. Run ingest_inspection.py first.")
        sys.exit(1)

    link_inspection_to_flight(flight_id, inspection_id)

    # Step 2: Score
    print("\n[2/3] Scoring findings...")
    result = process_inspection(inspection_id)
    print(f"      Score: {result['score']} ({result['tier']})")

    # Step 3: Generate report
    print("\n[3/3] Generating report...")
    output_path = generate_report(inspection_id)

    print("\n" + "="*55)
    print(f"  ✅ PIPELINE COMPLETE")
    print(f"  Report: {output_path}")
    print("="*55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run the full aerial inspection pipeline.")
    parser.add_argument("--csv",           required=True,  help="Path to AirData CSV")
    parser.add_argument("--inspection-id", required=True,  help="Existing inspection ID (from ingest_inspection.py)")
    parser.add_argument("--location",      required=True,  help="Location name")
    parser.add_argument("--drone",         required=True,  help="Drone model")
    parser.add_argument("--pilot",         required=True,  help="Pilot name")
    parser.add_argument("--weather",       required=True,  help="Weather conditions")
    parser.add_argument("--notes",         default="",     help="Optional notes")
    args = parser.parse_args()

    run_pipeline(
        csv_path=args.csv,
        inspection_id=args.inspection_id,
        location=args.location,
        drone=args.drone,
        pilot=args.pilot,
        weather=args.weather,
        notes=args.notes,
    )


if __name__ == "__main__":
    main()
