"""
score_and_merge.py
Computes the vulnerability score for one or all Draft inspections,
then links the inspection to its flight record in the database.

Scoring model:
  finding_score  = severity_score × area_weight × urgency_weight
  area_weight    : <50 sqft=0.8 | 50-200=1.0 | >200=1.2
  urgency_weight : ≤7 days=1.5 | 8-30=1.2 | 31-90=1.0 | >90=0.8
  overall_score  = min(100, (sum_of_finding_scores / 90) × 100)
  max_possible   = 90  (5 critical findings at 10×1.2×1.5)

Risk tiers:
  0-25   → Low
  26-50  → Medium
  51-75  → High
  76-100 → Critical
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.storage import (
    get_inspection_record,
    get_all_draft_inspections,
    update_inspection_scores,
    link_inspection_to_flight,
)


MAX_POSSIBLE = 90.0


def area_weight(sqft: float) -> float:
    if sqft < 50:
        return 0.8
    elif sqft <= 200:
        return 1.0
    else:
        return 1.2


def urgency_weight(days: int) -> float:
    if days <= 7:
        return 1.5
    elif days <= 30:
        return 1.2
    elif days <= 90:
        return 1.0
    else:
        return 0.8


def risk_tier(score: float) -> str:
    if score <= 25:
        return "Low"
    elif score <= 50:
        return "Medium"
    elif score <= 75:
        return "High"
    else:
        return "Critical"


def score_findings(findings: list) -> tuple[float, str]:
    """Return (overall_score, risk_tier) for a list of finding dicts."""
    if not findings:
        return 0.0, "Low"

    total = 0.0
    for f in findings:
        sev    = float(f.get("severity_score", 1))
        area   = float(f.get("affected_area_sqft", 0))
        urgency = int(f.get("urgency_days", 90))
        finding_score = sev * area_weight(area) * urgency_weight(urgency)
        total += finding_score

    overall = min(100.0, round((total / MAX_POSSIBLE) * 100, 1))
    return overall, risk_tier(overall)


def process_inspection(inspection_id: str, verbose: bool = True) -> dict:
    record = get_inspection_record(inspection_id)
    if not record:
        raise ValueError(f"Inspection '{inspection_id}' not found.")

    findings = json.loads(record["findings"] or "[]")
    score, tier = score_findings(findings)

    update_inspection_scores(inspection_id, score, tier)

    # Link flight record if inspection has a flight_id
    if record.get("flight_id"):
        link_inspection_to_flight(record["flight_id"], inspection_id)

    if verbose:
        print(f"\n  Inspection : {inspection_id}")
        print(f"  Property   : {record['property_address']}")
        print(f"  Findings   : {len(findings)}")
        print(f"  Score      : {score}")
        print(f"  Tier       : {tier}")

    return {"inspection_id": inspection_id, "score": score, "tier": tier}


def main():
    parser = argparse.ArgumentParser(description="Score inspection findings and update risk tiers.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspection-id", help="Score a specific inspection by ID")
    group.add_argument("--all-drafts", action="store_true", help="Score all Draft inspections")
    args = parser.parse_args()

    print("\n" + "="*50)
    print("  VULNERABILITY SCORING ENGINE")
    print("="*50)

    if args.inspection_id:
        result = process_inspection(args.inspection_id)
        print(f"\n✅ Done — score: {result['score']} ({result['tier']})")
    else:
        drafts = get_all_draft_inspections()
        if not drafts:
            print("\n  No Draft inspections found.")
            return
        print(f"\n  Found {len(drafts)} Draft inspection(s) to score...\n")
        for d in drafts:
            process_inspection(d["inspection_id"])
        print(f"\n✅ Scored {len(drafts)} inspection(s).")


if __name__ == "__main__":
    main()
