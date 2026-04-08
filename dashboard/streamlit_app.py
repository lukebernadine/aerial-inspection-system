"""
streamlit_app.py
Streamlit dashboard for the Aerial Inspection & Vulnerability Assessment System.

Run with: streamlit run dashboard/streamlit_app.py
"""

import sys
import json
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from core.storage import get_all_inspections, get_all_flights, get_inspection_with_flight

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


# ── Helpers ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_inspections():
    return get_all_inspections()


@st.cache_data(ttl=30)
def load_flights():
    return get_all_flights()


def findings_summary(findings_json: str) -> dict:
    findings = json.loads(findings_json or "[]")
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        sev = f.get("severity", "Low")
        counts[sev] = counts.get(sev, 0) + 1
    return counts, len(findings)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🚁 Aerial Inspection")
page = st.sidebar.radio("Navigation", ["Overview", "Inspections", "Flights", "Inspection Detail"])

# ── Overview page ─────────────────────────────────────────────────────────────
if page == "Overview":
    st.title("📊 Inspection Overview")

    inspections = load_inspections()
    flights     = load_flights()

    if not inspections:
        st.info("No inspections found. Run ingest_inspection.py to add your first inspection.")
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

    # Risk tier breakdown
    st.subheader("Risk Tier Breakdown")
    tier_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for i in completed:
        t = i.get("risk_tier", "Low")
        tier_counts[t] = tier_counts.get(t, 0) + 1

    tier_df = pd.DataFrame(
        {"Tier": list(tier_counts.keys()), "Count": list(tier_counts.values())}
    )
    st.bar_chart(tier_df.set_index("Tier"))

    # Recent inspections table
    st.subheader("Recent Inspections")
    rows = []
    for i in inspections[:10]:
        counts, total = findings_summary(i.get("findings") or "[]")
        rows.append({
            "ID":           i["inspection_id"],
            "Date":         i["date"],
            "Property":     i["property_address"],
            "Type":         i["inspection_type"],
            "Score":        i.get("overall_risk_score") or "—",
            "Tier":         f"{TIER_COLOURS.get(i.get('risk_tier',''), '')} {i.get('risk_tier','Draft')}",
            "Findings":     total,
            "Status":       i["status"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ── Inspections page ──────────────────────────────────────────────────────────
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
        tier = insp.get("risk_tier") or "Draft"
        icon = TIER_COLOURS.get(tier, "⚪")
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
                f_rows = [
                    {
                        "Category":    f.get("category"),
                        "Description": f.get("description"),
                        "Location":    f.get("location_on_property"),
                        "Severity":    f.get("severity"),
                        "Area (sqft)": f.get("affected_area_sqft"),
                        "Urgency":     f"{f.get('urgency_days')} days",
                        "Action":      f.get("recommended_action"),
                    }
                    for f in findings
                ]
                st.dataframe(pd.DataFrame(f_rows), use_container_width=True)


# ── Flights page ──────────────────────────────────────────────────────────────
elif page == "Flights":
    st.title("✈️ Flight Records")
    flights = load_flights()

    if not flights:
        st.info("No flights yet. Run ingest_flight.py to add a flight.")
        st.stop()

    f_rows = [
        {
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
        }
        for f in flights
    ]
    st.dataframe(pd.DataFrame(f_rows), use_container_width=True)


# ── Inspection Detail page ─────────────────────────────────────────────────────
elif page == "Inspection Detail":
    st.title("📋 Inspection Detail")
    inspections = load_inspections()
    if not inspections:
        st.info("No inspections found.")
        st.stop()

    options = {i["inspection_id"]: f"{i['inspection_id']} — {i['property_address']}" for i in inspections}
    selected_id = st.selectbox("Select inspection", list(options.keys()), format_func=lambda k: options[k])

    record = get_inspection_with_flight(selected_id)
    if not record:
        st.error("Could not load inspection.")
        st.stop()

    tier = record.get("risk_tier") or "N/A"
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
