"""
streamlit_app.py
Streamlit dashboard for the Aerial Inspection & Vulnerability Assessment System.

Run with: streamlit run dashboard/streamlit_app.py
"""

import sys
import json
import os
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))
from core.storage import (
    get_all_inspections, get_all_flights,
    get_inspection_with_flight, insert_inspection_record,
    initialise_db
)
from core.ingest_flight import ingest_csv
from core.storage import insert_flight_record, link_inspection_to_flight
from core.score_and_merge import process_inspection
from core.report_generator import generate_report

# Ensure DB exists
initialise_db()

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Aerial Inspection Dashboard",
    page_icon="🚁",
    layout="wide",
)

TIER_COLOURS = {
    "Critical": "🔴",
    "High":     "🟠",
    "Medium":   "🟡",
    "Low":      "🟢",
}

CATEGORIES     = ["Structural", "Drainage", "Surface", "Electrical", "Vegetation", "Other"]
SEVERITIES     = ["Low", "Medium", "High", "Critical"]
SEVERITY_SCORES = {"Low": 2, "Medium": 4, "High": 7, "Critical": 10}
INSPECTION_TYPES = ["Roof", "Perimeter", "Structural", "General"]


# ── Helpers ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_inspections():
    return get_all_inspections()


@st.cache_data(ttl=30)
def load_flights():
    return get_all_flights()


def findings_summary(findings_json):
    findings = json.loads(findings_json or "[]")
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        sev = f.get("severity", "Low")
        counts[sev] = counts.get(sev, 0) + 1
    return counts, len(findings)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🚁 Aerial Inspection")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "New Inspection", "Inspections", "Flights", "Inspection Detail"]
)

# ══════════════════════════════════════════════════════════════════════════════
# NEW INSPECTION PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page == "New Inspection":
    st.title("📋 New Inspection")
    st.caption("Fill in all sections below and click Submit to run the full pipeline and generate your report.")

    # ── Section 1: Flight Data ───────────────────────────────────────────────
    st.subheader("1. Flight Data")
    uploaded_csv = st.file_uploader("Upload AirData CSV", type=["csv"])

    col1, col2 = st.columns(2)
    with col1:
        location    = st.text_input("Location / Property Address")
        pilot       = st.text_input("Pilot Name")
    with col2:
        drone       = st.selectbox("Drone Model", ["DJI Air 2S", "DJI Air 3", "Other"])
        weather     = st.text_input("Weather Conditions (e.g. Clear, 72°F, light wind)")

    st.divider()

    # ── Section 2: Inspection Metadata ──────────────────────────────────────
    st.subheader("2. Inspection Details")
    col3, col4 = st.columns(2)
    with col3:
        inspection_type = st.selectbox("Inspection Type", INSPECTION_TYPES)
    with col4:
        inspector_name  = st.text_input("Inspector Name")

    st.divider()

    # ── Section 3: Findings ──────────────────────────────────────────────────
    st.subheader("3. Findings")
    st.caption("Add as many findings as needed. Click 'Add Another Finding' to add more.")

    if "findings" not in st.session_state:
        st.session_state.findings = [{}]

    def add_finding():
        st.session_state.findings.append({})

    def remove_finding(idx):
        st.session_state.findings.pop(idx)

    findings_data = []
    for i, _ in enumerate(st.session_state.findings):
        with st.expander(f"Finding #{i+1}", expanded=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                category = st.selectbox("Category", CATEGORIES, key=f"cat_{i}")
                severity = st.selectbox("Severity", SEVERITIES, key=f"sev_{i}")
                area     = st.number_input("Affected Area (sq ft)", min_value=0.0, value=0.0, key=f"area_{i}")
            with fc2:
                description = st.text_area("Description (what was observed)", key=f"desc_{i}", height=80)
                location_on = st.text_input("Location on Property", key=f"loc_{i}")
                urgency     = st.number_input("Fix within (days)", min_value=1, max_value=365, value=90, key=f"urg_{i}")

            action = st.text_input("Recommended Action", key=f"action_{i}")

            if len(st.session_state.findings) > 1:
                if st.button(f"Remove Finding #{i+1}", key=f"remove_{i}"):
                    remove_finding(i)
                    st.rerun()

            findings_data.append({
                "finding_id":           f"FND-{uuid.uuid4().hex[:6].upper()}",
                "category":             category,
                "description":          description,
                "location_on_property": location_on,
                "severity":             severity,
                "severity_score":       SEVERITY_SCORES[severity],
                "affected_area_sqft":   area,
                "recommended_action":   action,
                "urgency_days":         urgency,
                "photo_refs":           [],
            })

    st.button("➕ Add Another Finding", on_click=add_finding)

    st.divider()

    # ── Submit ───────────────────────────────────────────────────────────────
    if st.button("🚀 Submit & Generate Report", type="primary", use_container_width=True):

        # Validation
        errors = []
        if not uploaded_csv:
            errors.append("Please upload an AirData CSV file.")
        if not location.strip():
            errors.append("Please enter a location / property address.")
        if not pilot.strip():
            errors.append("Please enter a pilot name.")
        if not inspector_name.strip():
            errors.append("Please enter an inspector name.")
        if not weather.strip():
            errors.append("Please enter weather conditions.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            with st.spinner("Running pipeline... this may take 20-30 seconds."):
                try:
                    # Save uploaded CSV to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(uploaded_csv.read())
                        tmp_path = tmp.name

                    # Ingest flight
                    flight_record = ingest_csv(
                        csv_path=tmp_path,
                        location_name=location,
                        drone_model=drone,
                        pilot_name=pilot,
                        weather_conditions=weather,
                    )
                    insert_flight_record(flight_record)
                    flight_id = flight_record["flight_id"]

                    # Create inspection record
                    inspection_id = f"INS-{uuid.uuid4().hex[:8].upper()}"
                    inspection_record = {
                        "inspection_id":      inspection_id,
                        "flight_id":          flight_id,
                        "date":               datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "property_address":   location,
                        "inspection_type":    inspection_type,
                        "inspector_name":     inspector_name,
                        "findings":           json.dumps(findings_data),
                        "overall_risk_score": None,
                        "risk_tier":          None,
                        "status":             "Draft",
                    }
                    insert_inspection_record(inspection_record)

                    # Link flight to inspection
                    link_inspection_to_flight(flight_id, inspection_id)

                    # Score
                    result = process_inspection(inspection_id, verbose=False)

                    # Generate report
                    report_path = generate_report(inspection_id)

                    # Clean up temp file
                    os.unlink(tmp_path)

                    # Clear cache so dashboard updates
                    st.cache_data.clear()

                    # Success
                    st.success(f"✅ Inspection complete! ID: {inspection_id}")

                    col_a, col_b = st.columns(2)
                    col_a.metric("Risk Score", f"{result['score']} / 100")
                    col_b.metric("Risk Tier",  f"{TIER_COLOURS.get(result['tier'], '')} {result['tier']}")

                    # PDF download
                    if report_path.suffix == ".pdf":
                        with open(report_path, "rb") as f:
                            st.download_button(
                                label="📥 Download PDF Report",
                                data=f,
                                file_name=report_path.name,
                                mime="application/pdf",
                                use_container_width=True,
                            )
                    else:
                        with open(report_path, "r") as f:
                            st.download_button(
                                label="📥 Download Markdown Report",
                                data=f,
                                file_name=report_path.name,
                                mime="text/markdown",
                                use_container_width=True,
                            )

                except Exception as e:
                    st.error(f"Pipeline error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Overview":
    st.title("📊 Inspection Overview")

    inspections = load_inspections()
    flights     = load_flights()

    if not inspections:
        st.info("No inspections yet. Go to 'New Inspection' to add your first one.")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Inspections", len(inspections))
    col2.metric("Total Flights",     len(flights))

    completed = [i for i in inspections if i["status"] == "Complete"]
    col3.metric("Completed", len(completed))

    if completed:
        avg_score = sum(i["overall_risk_score"] or 0 for i in completed) / len(completed)
        col4.metric("Avg Risk Score", f"{avg_score:.1f}")

    st.divider()

    st.subheader("Risk Tier Breakdown")
    tier_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for i in completed:
        t = i.get("risk_tier", "Low")
        tier_counts[t] = tier_counts.get(t, 0) + 1

    tier_df = pd.DataFrame({"Tier": list(tier_counts.keys()), "Count": list(tier_counts.values())})
    st.bar_chart(tier_df.set_index("Tier"))

    st.subheader("Recent Inspections")
    rows = []
    for i in inspections[:10]:
        counts, total = findings_summary(i.get("findings") or "[]")
        rows.append({
            "ID":       i["inspection_id"],
            "Date":     i["date"],
            "Property": i["property_address"],
            "Type":     i["inspection_type"],
            "Score":    i.get("overall_risk_score") or "—",
            "Tier":     f"{TIER_COLOURS.get(i.get('risk_tier',''), '')} {i.get('risk_tier','Draft')}",
            "Findings": total,
            "Status":   i["status"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# INSPECTIONS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Inspections":
    st.title("🔍 All Inspections")
    inspections = load_inspections()

    if not inspections:
        st.info("No inspections yet.")
        st.stop()

    status_filter = st.selectbox("Filter by status", ["All", "Draft", "Complete", "Reviewed"])
    if status_filter != "All":
        inspections = [i for i in inspections if i["status"] == status_filter]

    for insp in inspections:
        tier  = insp.get("risk_tier") or "Draft"
        icon  = TIER_COLOURS.get(tier, "⚪")
        score = insp.get("overall_risk_score")
        score_str = f"{score:.1f}" if score is not None else "—"
        with st.expander(f"{icon} {insp['property_address']} | {insp['date']} | Score: {score_str}"):
            col1, col2 = st.columns(2)
            col1.write(f"**ID:** {insp['inspection_id']}")
            col1.write(f"**Type:** {insp['inspection_type']}")
            col1.write(f"**Inspector:** {insp['inspector_name']}")
            col2.write(f"**Status:** {insp['status']}")
            col2.write(f"**Risk Tier:** {tier}")
            col2.write(f"**Linked Flight:** {insp.get('flight_id') or 'None'}")

            findings = json.loads(insp.get("findings") or "[]")
            if findings:
                st.write(f"**{len(findings)} Finding(s):**")
                f_rows = [{
                    "Category":    f.get("category"),
                    "Description": f.get("description"),
                    "Location":    f.get("location_on_property"),
                    "Severity":    f.get("severity"),
                    "Area (sqft)": f.get("affected_area_sqft"),
                    "Urgency":     f"{f.get('urgency_days')} days",
                    "Action":      f.get("recommended_action"),
                } for f in findings]
                st.dataframe(pd.DataFrame(f_rows), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# FLIGHTS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Flights":
    st.title("✈️ Flight Records")
    flights = load_flights()

    if not flights:
        st.info("No flights yet.")
        st.stop()

    f_rows = [{
        "Flight ID":   f["flight_id"],
        "Date":        f["date"],
        "Location":    f["location_name"],
        "Drone":       f["drone_model"],
        "Duration":    f"{f.get('duration_min', 0):.1f} min",
        "Max Alt":     f"{f.get('altitude_ft', 0):.0f} ft",
        "Max Speed":   f"{f.get('max_speed_mph', 0):.1f} mph",
        "Battery":     f"{f.get('battery_start_pct',0)}% → {f.get('battery_end_pct',0)}%",
        "Pilot":       f["pilot_name"],
        "Linked Insp": f.get("inspection_id") or "—",
    } for f in flights]
    st.dataframe(pd.DataFrame(f_rows), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# INSPECTION DETAIL PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Inspection Detail":
    st.title("📋 Inspection Detail")
    inspections = load_inspections()

    if not inspections:
        st.info("No inspections found.")
        st.stop()

    options    = {i["inspection_id"]: f"{i['inspection_id']} — {i['property_address']}" for i in inspections}
    selected_id = st.selectbox("Select inspection", list(options.keys()), format_func=lambda k: options[k])

    record = get_inspection_with_flight(selected_id)
    if not record:
        st.error("Could not load inspection.")
        st.stop()

    tier  = record.get("risk_tier") or "N/A"
    score = record.get("overall_risk_score")

    st.subheader(f"{TIER_COLOURS.get(tier, '')} {record['property_address']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score", f"{score:.1f}" if score else "—")
    col2.metric("Risk Tier",  tier)
    col3.metric("Status",     record["status"])

    st.divider()
    col4, col5 = st.columns(2)
    with col4:
        st.write("**Inspection Info**")
        st.write(f"Date: {record['date']}")
        st.write(f"Type: {record['inspection_type']}")
        st.write(f"Inspector: {record['inspector_name']}")
    with col5:
        st.write("**Flight Info**")
        st.write(f"Drone: {record.get('drone_model') or '—'}")
        st.write(f"Duration: {record.get('duration_min') or '—'} min")
        st.write(f"Max Altitude: {record.get('altitude_ft') or '—'} ft")
        st.write(f"Weather: {record.get('weather_conditions') or '—'}")

    findings = json.loads(record.get("findings") or "[]")
    if findings:
        st.divider()
        st.subheader(f"Findings ({len(findings)})")
        sorted_findings = sorted(findings, key=lambda x: x.get("urgency_days", 999))
        for f in sorted_findings:
            sev = f.get("severity", "Low")
            with st.expander(f"{TIER_COLOURS.get(sev,'⚪')} [{sev}] {f.get('description')}"):
                st.write(f"**Category:** {f.get('category')}")
                st.write(f"**Location:** {f.get('location_on_property')}")
                st.write(f"**Affected Area:** {f.get('affected_area_sqft')} sqft")
                st.write(f"**Urgency:** Fix within {f.get('urgency_days')} days")
                st.write(f"**Recommended Action:** {f.get('recommended_action')}")
                if f.get("photo_refs"):
                    st.write(f"**Photos:** {', '.join(f['photo_refs'])}")

        # Re-generate report button
        st.divider()
        if st.button("🔄 Re-generate PDF Report", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    report_path = generate_report(selected_id)
                    with open(report_path, "rb") as f:
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=f,
                            file_name=report_path.name,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(f"Report generation failed: {e}")
