"""
report_generator.py
Generates a professional inspection report via the Claude API,
then saves it as both a Markdown file and a PDF.

Usage:
  python report_generator.py --inspection-id INS-XXXXXXXX
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv
load_dotenv()
from dotenv import load_dotenv
load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))
from core.storage import get_inspection_with_flight

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR  = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


SYSTEM_PROMPT = """You are a professional infrastructure inspection report writer.
Only report what is in the data provided. Do not speculate, invent findings, or add recommendations
not supported by the data. Format your response in clean, professional Markdown.
Use tables where specified. Be concise and factual."""


def build_user_prompt(record: dict, findings: list) -> str:
    severity_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for f in findings:
        sev = f.get("severity", "Low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    findings_table = ""
    for i, f in enumerate(findings, 1):
        findings_table += (
            f"| {i} | {f.get('category','')} | {f.get('description','')} | "
            f"{f.get('location_on_property','')} | {f.get('severity','')} | "
            f"{f.get('affected_area_sqft',0)} sqft | {f.get('urgency_days','')} days | "
            f"{f.get('recommended_action','')} |\n"
        )

    recommendations = sorted(findings, key=lambda x: x.get("urgency_days", 999))
    rec_list = "\n".join(
        f"- [{f.get('severity')} | {f.get('urgency_days')} days] {f.get('recommended_action')} "
        f"— {f.get('location_on_property')}"
        for f in recommendations
    )

    return f"""Generate a professional aerial inspection report using ONLY the data below.

## INSPECTION METADATA
- Inspection ID: {record.get('inspection_id')}
- Property: {record.get('property_address')}
- Date: {record.get('date')}
- Inspector: {record.get('inspector_name')}
- Inspection Type: {record.get('inspection_type')}
- Drone: {record.get('drone_model', 'Not recorded')}
- Weather: {record.get('weather_conditions', 'Not recorded')}

## FLIGHT DATA
- Max Altitude: {record.get('altitude_ft', 'N/A')} ft
- Duration: {record.get('duration_min', 'N/A')} min
- Max Distance: {record.get('distance_ft', 'N/A')} ft
- Max Speed: {record.get('max_speed_mph', 'N/A')} mph
- Battery Start: {record.get('battery_start_pct', 'N/A')}%
- Battery End: {record.get('battery_end_pct', 'N/A')}%
- GPS: {record.get('gps_lat', 'N/A')}, {record.get('gps_lon', 'N/A')}

## RISK ASSESSMENT
- Overall Score: {record.get('overall_risk_score')} / 100
- Risk Tier: {record.get('risk_tier')}
- Total Findings: {len(findings)}
- Critical: {severity_counts['Critical']} | High: {severity_counts['High']} | Medium: {severity_counts['Medium']} | Low: {severity_counts['Low']}

## FINDINGS TABLE
| # | Category | Description | Location | Severity | Area | Urgency | Recommended Action |
|---|----------|-------------|----------|----------|------|---------|-------------------|
{findings_table}
## PRIORITISED RECOMMENDATIONS (sorted by urgency, most urgent first)
{rec_list}

---
Generate the report with these EXACT sections in this order:
1. Executive Summary
2. Flight Operations Summary (use a markdown table)
3. Findings & Risk Analysis (use the findings table above)
4. Risk Score Breakdown
5. Prioritised Recommendations (by urgency, most urgent first)
6. Conclusion
"""


def generate_report(inspection_id: str) -> Path:
    record = get_inspection_with_flight(inspection_id)
    if not record:
        raise ValueError(f"Inspection '{inspection_id}' not found.")
    if not record.get("overall_risk_score"):
        raise ValueError("Run score_and_merge.py first — inspection has no risk score.")

    findings = json.loads(record.get("findings") or "[]")

    print(f"\n🤖 Sending to Claude API...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(record, findings)}],
    )

    report_md = message.content[0].text

    # Save Markdown
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_addr = record.get("property_address", "unknown").replace(" ", "_").replace(",", "")[:40]
    filename_stem = f"{timestamp}_{inspection_id}_{safe_addr}"

    md_path = REPORTS_DIR / f"{filename_stem}.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"📄 Markdown saved: {md_path}")

    # Convert to PDF via markdown-pdf (install: pip install markdown-pdf)
    try:
        import markdown_pdf  # type: ignore
        pdf_path = REPORTS_DIR / f"{filename_stem}.pdf"
        pdf = markdown_pdf.MarkdownPdf()
        pdf.meta["title"] = f"Inspection Report — {record.get('property_address')}"
        pdf.add_section(markdown_pdf.Section(report_md))
        pdf.save(str(pdf_path))
        print(f"📑 PDF saved:      {pdf_path}")
        return pdf_path
    except ImportError:
        print("⚠️  markdown-pdf not installed — PDF skipped. Run: pip install markdown-pdf")
        return md_path


def main():
    parser = argparse.ArgumentParser(description="Generate an inspection report via Claude API.")
    parser.add_argument("--inspection-id", required=True, help="Inspection ID to report on")
    args = parser.parse_args()

    output = generate_report(args.inspection_id)
    print(f"\n✅ Report complete: {output}")


if __name__ == "__main__":
    main()
