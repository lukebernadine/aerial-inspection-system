"""
storage.py
Supabase (PostgreSQL) storage layer for the Vantage aerial inspection system.
Replaces the SQLite implementation with cloud database calls.
"""

import os
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client = None

def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(url, key)
    return _client


def initialise_db():
    """No-op for Supabase — tables are created via SQL Editor."""
    print("✅ Supabase storage ready.")


# ── Flight Records ────────────────────────────────────────────────────────────

def insert_flight_record(record: dict):
    data = {k: v for k, v in record.items() if v is not None or k == "flight_id"}
    get_client().table("flight_records").upsert(data).execute()


def get_flight_record(flight_id: str) -> dict | None:
    res = get_client().table("flight_records").select("*").eq("flight_id", flight_id).execute()
    return res.data[0] if res.data else None


def get_all_flights() -> list[dict]:
    res = get_client().table("flight_records").select("*").order("date", desc=True).execute()
    return res.data or []


def link_inspection_to_flight(flight_id: str, inspection_id: str):
    get_client().table("flight_records").update(
        {"inspection_id": inspection_id}
    ).eq("flight_id", flight_id).execute()


# ── Inspection Records ────────────────────────────────────────────────────────

def insert_inspection_record(record: dict):
    data = {k: v for k, v in record.items()}
    get_client().table("inspection_records").upsert(data).execute()


def get_inspection_record(inspection_id: str) -> dict | None:
    res = get_client().table("inspection_records").select("*").eq("inspection_id", inspection_id).execute()
    return res.data[0] if res.data else None


def get_all_draft_inspections() -> list[dict]:
    res = get_client().table("inspection_records").select("*").eq("status", "Draft").execute()
    return res.data or []


def get_all_inspections() -> list[dict]:
    res = get_client().table("inspection_records").select("*").order("date", desc=True).execute()
    return res.data or []


def update_inspection_scores(inspection_id: str, score: float, tier: str):
    now = datetime.now(timezone.utc).isoformat()
    get_client().table("inspection_records").update({
        "overall_risk_score": score,
        "risk_tier":          tier,
        "status":             "Complete",
        "updated_at":         now,
    }).eq("inspection_id", inspection_id).execute()


def get_inspection_with_flight(inspection_id: str) -> dict | None:
    # Fetch inspection
    insp_res = get_client().table("inspection_records").select("*").eq("inspection_id", inspection_id).execute()
    if not insp_res.data:
        return None
    record = insp_res.data[0]

    # Fetch linked flight if exists
    if record.get("flight_id"):
        flt_res = get_client().table("flight_records").select("*").eq("flight_id", record["flight_id"]).execute()
        if flt_res.data:
            flight = flt_res.data[0]
            # Merge flight fields into record
            for key in ["location_name", "gps_lat", "gps_lon", "altitude_ft",
                        "duration_min", "distance_ft", "max_speed_mph", "drone_model",
                        "weather_conditions", "battery_start_pct", "battery_end_pct", "pilot_name"]:
                if key not in record or record[key] is None:
                    record[key] = flight.get(key)

    return record


def delete_inspection_record(inspection_id: str):
    get_client().table("inspection_records").delete().eq("inspection_id", inspection_id).execute()


def delete_flight_record(flight_id: str):
    get_client().table("flight_records").delete().eq("flight_id", flight_id).execute()


# ── Compatibility shim for dashboard delete functions ─────────────────────────
def get_connection():
    """Not used with Supabase — kept for import compatibility."""
    raise NotImplementedError("get_connection() is not available with Supabase storage.")
