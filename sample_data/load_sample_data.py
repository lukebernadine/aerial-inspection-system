"""
load_sample_data.py
Loads realistic sample data into the database so you can test the full pipeline
before running a real inspection. Safe to run multiple times (uses fixed IDs).

Run from project root:
  python data/sample_data/load_sample_data.py
"""

import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.storage import initialise_db, insert_flight_record, insert_inspection_record
from core.score_and_merge import process_inspection

FLIGHT = {
    "flight_id":          "FLT-SAMPLE01",
    "inspection_id":      None,
    "date":               "2023-07-14",
    "location_name":      "123 Maple Street, Springfield",
    "gps_lat":            41.157454,
    "gps_lon":            -105.312164,
    "altitude_ft":        370.7,
    "duration_min":       17.07,
    "distance_ft":        5485.2,
    "max_speed_mph":      44.1,
    "drone_model":        "DJI Air 2S",
    "weather_conditions": "Clear, 85°F, light breeze 5mph SW",
    "battery_start_pct":  79,
    "battery_end_pct":    2,
    "pilot_name":         "Alex Johnson",
    "notes":              "Sample flight from AirData export. Used for pipeline testing.",
}

FINDINGS = [
    {
        "finding_id":           "FND-S001",
        "category":             "Structural",
        "description":          "Cracked ridge cap tiles along NW roof section, approximately 3 tiles displaced",
        "location_on_property": "NW roof ridge",
        "severity":             "High",
        "severity_score":       7,
        "affected_area_sqft":   12.0,
        "recommended_action":   "Replace displaced ridge cap tiles and inspect underlying sheathing for moisture damage",
        "urgency_days":         14,
        "photo_refs":           ["ridge_crack_01.jpg", "ridge_crack_02.jpg"],
    },
    {
        "finding_id":           "FND-S002",
        "category":             "Drainage",
        "description":          "Clogged gutters on south elevation — significant debris buildup, standing water visible",
        "location_on_property": "South elevation gutters",
        "severity":             "Medium",
        "severity_score":       4,
        "affected_area_sqft":   80.0,
        "recommended_action":   "Full gutter clean and flush. Install gutter guards to prevent recurrence.",
        "urgency_days":         30,
        "photo_refs":           ["gutter_south_01.jpg"],
    },
    {
        "finding_id":           "FND-S003",
        "category":             "Vegetation",
        "description":          "Tree branches overhanging roof within 3ft — abrasion risk to shingles",
        "location_on_property": "East side, large oak",
        "severity":             "Low",
        "severity_score":       2,
        "affected_area_sqft":   25.0,
        "recommended_action":   "Trim branches to maintain minimum 6ft clearance from roof surface",
        "urgency_days":         90,
        "photo_refs":           ["tree_overhang_east.jpg"],
    },
    {
        "finding_id":           "FND-S004",
        "category":             "Surface",
        "description":          "Granule loss on 3 asphalt shingles, SE quadrant — end-of-life indicator",
        "location_on_property": "SE roof quadrant",
        "severity":             "Medium",
        "severity_score":       4,
        "affected_area_sqft":   18.0,
        "recommended_action":   "Monitor quarterly. Full roof replacement likely required within 2 years.",
        "urgency_days":         60,
        "photo_refs":           ["granule_loss_se_01.jpg"],
    },
]

INSPECTION = {
    "inspection_id":      "INS-SAMPLE01",
    "flight_id":          "FLT-SAMPLE01",
    "date":               "2023-07-14",
    "property_address":   "123 Maple Street, Springfield",
    "inspection_type":    "Roof",
    "inspector_name":     "Alex Johnson",
    "findings":           json.dumps(FINDINGS),
    "overall_risk_score": None,
    "risk_tier":          None,
    "status":             "Draft",
}


def main():
    print("\n📦 Loading sample data...")
    initialise_db()
    insert_flight_record(FLIGHT)
    print("  ✅ Flight record inserted: FLT-SAMPLE01")
    insert_inspection_record(INSPECTION)
    print("  ✅ Inspection record inserted: INS-SAMPLE01")

    result = process_inspection("INS-SAMPLE01")
    print(f"  ✅ Scored: {result['score']} — {result['tier']}")

    print("\n🎉 Sample data loaded. You can now:")
    print("   • Run the dashboard: streamlit run dashboard/streamlit_app.py")
    print("   • Generate a report: python pipeline/report_generator.py --inspection-id INS-SAMPLE01")


if __name__ == "__main__":
    main()
