"""
ingest_inspection.py
Interactive CLI tool for entering inspection findings.
Walks the inspector through each finding one at a time,
then saves the complete inspection record to the database.
"""

import sys
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.storage import insert_inspection_record, get_flight_record


CATEGORIES  = ["Structural", "Drainage", "Surface", "Electrical", "Vegetation", "Other"]
SEVERITIES  = ["Low", "Medium", "High", "Critical"]
SEVERITY_SCORES = {"Low": 2, "Medium": 4, "High": 7, "Critical": 10}
INSPECTION_TYPES = ["Roof", "Perimeter", "Structural", "General"]


def prompt(label: str, default: str = None, options: list = None) -> str:
    if options:
        print(f"\n  {label}")
        for i, opt in enumerate(options, 1):
            print(f"    {i}. {opt}")
        while True:
            raw = input(f"  Enter number [1-{len(options)}]: ").strip()
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(options):
                    return options[idx]
            except ValueError:
                pass
            print("  ❌ Invalid choice — try again.")
    else:
        suffix = f" [{default}]" if default else ""
        raw = input(f"  {label}{suffix}: ").strip()
        return raw if raw else (default or "")


def prompt_int(label: str, min_val: int, max_val: int, default: int = None) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {label} ({min_val}-{max_val}){suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
        except ValueError:
            pass
        print(f"  ❌ Enter a number between {min_val} and {max_val}.")


def prompt_float(label: str, default: float = None) -> float:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {label}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("  ❌ Enter a valid number.")


def collect_finding() -> dict:
    print("\n  ── New Finding ──────────────────────────")
    category    = prompt("Category",          options=CATEGORIES)
    severity    = prompt("Severity",          options=SEVERITIES)
    description = prompt("Description (what was observed)")
    location    = prompt("Location on property (e.g. 'NW corner roof ridge')")
    area_sqft   = prompt_float("Affected area (sq ft)", default=0.0)
    urgency     = prompt_int("Urgency — fix within how many days?", 1, 365, default=90)
    action      = prompt("Recommended action")
    photos_raw  = prompt("Photo filenames (comma-separated, or leave blank)", default="")
    photo_refs  = [p.strip() for p in photos_raw.split(",") if p.strip()] if photos_raw else []

    return {
        "finding_id":          f"FND-{uuid.uuid4().hex[:6].upper()}",
        "category":            category,
        "description":         description,
        "location_on_property": location,
        "severity":            severity,
        "severity_score":      SEVERITY_SCORES[severity],
        "affected_area_sqft":  area_sqft,
        "recommended_action":  action,
        "urgency_days":        urgency,
        "photo_refs":          photo_refs,
    }


def run():
    print("\n" + "="*55)
    print("  AERIAL INSPECTION — FINDINGS ENTRY")
    print("="*55)

    # --- Inspection metadata ---
    print("\n📋 INSPECTION METADATA\n")
    inspection_id   = f"INS-{uuid.uuid4().hex[:8].upper()}"
    date_str        = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    property_addr   = prompt("Property address")
    inspection_type = prompt("Inspection type", options=INSPECTION_TYPES)
    inspector_name  = prompt("Inspector name")

    # --- Optional flight link ---
    flight_id = prompt("Flight ID to link (leave blank to skip)", default="")
    if flight_id:
        flight = get_flight_record(flight_id)
        if flight:
            print(f"  ✅ Linked to flight: {flight['location_name']} on {flight['date']}")
        else:
            print(f"  ⚠️  Flight ID '{flight_id}' not found — saving without link.")
            flight_id = None

    # --- Findings loop ---
    findings = []
    print("\n🔍 FINDINGS ENTRY")
    print("  Enter each finding one at a time. Type 'done' at any finding prompt to finish.\n")

    while True:
        add_more = input(f"  Add finding #{len(findings)+1}? [Y/n]: ").strip().lower()
        if add_more in ("n", "no", "done"):
            break
        findings.append(collect_finding())
        print(f"  ✅ Finding recorded ({len(findings)} total so far)")

    if not findings:
        print("\n⚠️  No findings entered. Saving inspection with empty findings list.")

    record = {
        "inspection_id":    inspection_id,
        "flight_id":        flight_id or None,
        "date":             date_str,
        "property_address": property_addr,
        "inspection_type":  inspection_type,
        "inspector_name":   inspector_name,
        "findings":         json.dumps(findings),
        "overall_risk_score": None,  # computed by score_and_merge.py
        "risk_tier":          None,
        "status":             "Draft",
    }

    insert_inspection_record(record)
    print(f"\n💾 Inspection saved — ID: {inspection_id}")
    print("   Run score_and_merge.py to compute risk scores.")
    return inspection_id


if __name__ == "__main__":
    run()
