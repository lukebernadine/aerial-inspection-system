"""
streamlit_app.py — Vantage
The complete aerial inspection platform.
Dark theme · Sidebar navigation · Home landing page
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
    insert_flight_record, link_inspection_to_flight,
    initialise_db, delete_inspection_record, delete_flight_record
)
from core.ingest_flight import ingest_csv
from core.score_and_merge import process_inspection
from core.report_generator import generate_report

initialise_db()

CATEGORIES       = ["Structural", "Drainage", "Surface", "Electrical", "Vegetation", "Other"]
SEVERITIES       = ["Low", "Medium", "High", "Critical"]
SEVERITY_SCORES  = {"Low": 2, "Medium": 4, "High": 7, "Critical": 10}
INSPECTION_TYPES = ["Roof", "Perimeter", "Structural", "General"]
TIER_COLORS      = {"Critical": "#f87171", "High": "#fb923c", "Medium": "#fbbf24", "Low": "#4ade80"}
TIER_BG          = {"Critical": "rgba(248,113,113,0.12)", "High": "rgba(251,146,60,0.12)",
                    "Medium": "rgba(251,191,36,0.12)", "Low": "rgba(74,222,128,0.12)"}
TIER_BORDER      = {"Critical": "rgba(248,113,113,0.3)", "High": "rgba(251,146,60,0.3)",
                    "Medium": "rgba(251,191,36,0.3)", "Low": "rgba(74,222,128,0.3)"}

NAV_ITEMS = [
    ("🏠", "Home"),
    ("📊", "Dashboard"),
    ("✚", "New Inspection"),
    ("🔍", "Inspections"),
    ("✈️", "Flights"),
    ("📈", "Analytics"),
    ("📖", "How It Works"),
    ("❓", "FAQ"),
    ("📬", "Contact"),
]

st.set_page_config(
    page_title="Vantage — Aerial Inspection Platform",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

:root {
    --bg:      #0f1117;
    --bg2:     #161b27;
    --card:    #1a2035;
    --card2:   #1f2640;
    --border:  rgba(255,255,255,0.07);
    --border2: rgba(255,255,255,0.13);
    --accent:  #4f8ef7;
    --accent2: #7aaef9;
    --text:    #e8edf5;
    --text2:   #8892a4;
    --text3:   #4a5568;
    --success: #4ade80;
    --warn:    #fbbf24;
    --danger:  #f87171;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}
.stApp {
    background: var(--bg) !important;
    background-image: radial-gradient(ellipse 70% 50% at 50% -20%,
        rgba(79,142,247,0.06) 0%, transparent 70%) !important;
}

#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
/* Hide sidebar collapse button — sidebar is always open */
[data-testid="collapsedControl"] { display: none !important; }
button[kind="header"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
    min-width: 200px !important;
    max-width: 200px !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] > div { padding-top: 1.5rem !important; }

/* Force radio buttons to look like nav items */
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
}
[data-testid="stSidebar"] .stRadio label {
    display: flex !important;
    align-items: center !important;
    padding: 0.5rem 0.75rem !important;
    border-radius: 7px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: var(--text2) !important;
    cursor: pointer !important;
    transition: all 0.12s !important;
    white-space: nowrap !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.05) !important;
    color: var(--text) !important;
}
[data-testid="stSidebar"] .stRadio [data-checked="true"] label,
[data-testid="stSidebar"] .stRadio label[aria-checked="true"] {
    background: rgba(79,142,247,0.15) !important;
    color: var(--accent2) !important;
}
/* Hide radio circles */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* ── Typography ── */
h1,h2,h3,h4,h5,h6 {
    font-family: 'Manrope', sans-serif !important;
    color: var(--text) !important;
    letter-spacing: -0.015em !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.1rem 1.25rem !important;
    transition: border-color 0.15s !important;
}
[data-testid="metric-container"]:hover { border-color: var(--border2) !important; }
[data-testid="stMetricLabel"] p {
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: var(--text3) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Manrope', sans-serif !important;
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    color: var(--text) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: var(--accent2) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid var(--border2) !important;
    color: var(--text2) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.05) !important;
    color: var(--text) !important;
    transform: none !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(79,142,247,0.15) !important;
}
label { color: var(--text2) !important; font-size: 0.85rem !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
    color: var(--text) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--card) !important;
    border: 1.5px dashed var(--border2) !important;
    border-radius: 10px !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1.25rem 0 !important; }

/* ── Download ── */
[data-testid="stDownloadButton"] > button {
    background: #15803d !important;
    color: #fff !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 7px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: var(--card) !important;
    border-radius: 8px !important;
    padding: 3px !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: var(--text2) !important;
    border-radius: 6px !important;
    white-space: nowrap !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: var(--accent) !important;
    color: #fff !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}

/* ── Custom components ── */
.v-logo {
    font-family: 'Manrope', sans-serif;
    font-size: 1.2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--accent2);
    padding: 0 0 0.25rem 0;
}
.v-logo-sub {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text3);
    margin-bottom: 1.5rem;
}
.v-nav-section {
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--text3);
    padding: 0.5rem 0.75rem 0.3rem;
    font-weight: 600;
}
.v-page-title {
    font-family: 'Manrope', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
    line-height: 1.2;
}
.v-page-sub {
    font-size: 0.875rem;
    color: var(--text3);
    margin-bottom: 1.75rem;
}
.v-section {
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text3);
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border);
    margin: 1.5rem 0 0.85rem 0;
}
.v-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.5rem;
    transition: border-color 0.12s;
}
.v-card:hover { border-color: var(--border2); }
.v-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.tier-critical { background:rgba(248,113,113,0.12); color:#f87171; border:1px solid rgba(248,113,113,0.25); }
.tier-high     { background:rgba(251,146,60,0.12);  color:#fb923c; border:1px solid rgba(251,146,60,0.25); }
.tier-medium   { background:rgba(251,191,36,0.12);  color:#fbbf24; border:1px solid rgba(251,191,36,0.25); }
.tier-low      { background:rgba(74,222,128,0.12);  color:#4ade80; border:1px solid rgba(74,222,128,0.25); }
.tier-none     { background:rgba(100,116,139,0.1);  color:#64748b; border:1px solid rgba(100,116,139,0.2); }

/* Home page */
.v-hero {
    padding: 3rem 0 2rem 0;
    text-align: center;
}
.v-hero-title {
    font-family: 'Manrope', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.1;
    color: var(--text);
    margin-bottom: 1rem;
}
.v-hero-title span { color: var(--accent2); }
.v-hero-sub {
    font-size: 1.05rem;
    color: var(--text2);
    max-width: 560px;
    margin: 0 auto 2rem auto;
    line-height: 1.65;
}
.v-feature-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    height: 100%;
    transition: border-color 0.15s, transform 0.15s;
}
.v-feature-card:hover {
    border-color: var(--border2);
    transform: translateY(-2px);
}
.v-feature-icon {
    font-size: 1.75rem;
    margin-bottom: 0.75rem;
}
.v-feature-title {
    font-family: 'Manrope', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.4rem;
}
.v-feature-desc {
    font-size: 0.83rem;
    color: var(--text2);
    line-height: 1.6;
}
.v-testimonial {
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
}
.v-testimonial-text {
    font-size: 0.9rem;
    color: var(--text2);
    line-height: 1.65;
    font-style: italic;
    margin-bottom: 0.6rem;
}
.v-testimonial-author {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text3);
}
.v-workflow-step {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 0.5rem;
}
.v-workflow-num {
    width: 30px; height: 30px; min-width: 30px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-family: 'Manrope', sans-serif;
    font-weight: 700;
    font-size: 0.82rem;
    display: flex;
    align-items: center;
    justify-content: center;
}
.v-step { display:flex; gap:0.875rem; align-items:flex-start; margin-bottom:1rem; }
.v-step-num {
    width:28px; height:28px; min-width:28px; border-radius:50%;
    background:var(--accent); color:#fff;
    font-family:'Manrope',sans-serif; font-weight:700; font-size:0.8rem;
    display:flex; align-items:center; justify-content:center;
}
.v-bar-wrap { margin-bottom:0.6rem; }
.v-bar-row  { display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.8rem; }
.v-bar-bg   { background:var(--card2); border-radius:3px; height:5px; overflow:hidden; }
.v-bar-fill { height:5px; border-radius:3px; }
.v-info-block {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    font-size: 0.85rem; color: var(--text2); line-height: 1.7;
}
.v-faq-q { font-family:'Manrope',sans-serif; font-weight:700; font-size:0.9rem; color:var(--text); margin-bottom:0.3rem; }
.v-faq-a { font-size:0.83rem; color:var(--text2); line-height:1.65; margin-bottom:1.25rem; }
.v-form-section {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.v-form-section-title {
    font-family: 'Manrope', sans-serif;
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1rem;
}
.v-stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    margin-bottom: 4px;
    border-radius: 6px;
    background: var(--card2);
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "findings" not in st.session_state:
    st.session_state.findings = [{}]


# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_inspections():
    return get_all_inspections()

@st.cache_data(ttl=30)
def load_flights():
    return get_all_flights()

def badge(tier):
    if not tier: return '<span class="v-badge tier-none">—</span>'
    return f'<span class="v-badge tier-{tier.lower()}">{tier}</span>'

def delete_inspection(iid):
    delete_inspection_record(iid)
    st.cache_data.clear()

def delete_flight(fid):
    delete_flight_record(fid)
    st.cache_data.clear()

def footer_nav(current_page):
    """Render bottom navigation bar with buttons for all pages."""
    all_pages = [
        ("🏠", "Home"), ("📊", "Dashboard"), ("✚", "New Inspection"),
        ("🔍", "Inspections"), ("✈️", "Flights"), ("📋", "Reports"),
        ("📖", "How It Works"), ("❓", "FAQ"), ("📬", "Contact"),
    ]
    st.markdown("---")
    st.markdown('<div style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#4a5568;margin-bottom:0.6rem;">Navigate to</div>', unsafe_allow_html=True)
    cols = st.columns(len(all_pages))
    for col, (icon, name) in zip(cols, all_pages):
        if name != current_page:
            with col:
                if st.button(f"{icon} {name}", key=f"footer_{name}", use_container_width=True):
                    st.session_state.page = name
                    st.session_state.last_nav_group = "main" if name not in ["How It Works", "FAQ", "Contact"] else "support"
                    st.session_state.prev_main    = f"📊  {name}" if name == "Dashboard" else st.session_state.get("prev_main", "🏠  Home")
                    st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="v-logo">⬡ Vantage</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-logo-sub">Aerial Inspection Platform</div>', unsafe_allow_html=True)

    st.markdown('<div class="v-nav-section">Platform</div>', unsafe_allow_html=True)
    main_page = st.radio(
        "Platform Navigation",
        ["🏠  Home", "📊  Dashboard", "✚  New Inspection",
         "🔍  Inspections", "✈️  Flights", "📋  Reports"],
        label_visibility="collapsed",
        key="main_nav_radio"
    )

    st.markdown('<div class="v-nav-section">Support</div>', unsafe_allow_html=True)
    support_page = st.radio(
        "Support Navigation",
        ["📖  How It Works", "❓  FAQ", "📬  Contact"],
        label_visibility="collapsed",
        key="support_nav_radio"
    )

    st.markdown("---")
    st.markdown('<div style="font-size:0.62rem;color:#1e293b;text-align:center;line-height:1.7;">Vantage v1.0<br>See everything. Miss nothing.</div>', unsafe_allow_html=True)

# Routing: track which group was last clicked
if "last_nav_group" not in st.session_state:
    st.session_state.last_nav_group = "main"

# Detect which group is active by checking session state changes
main_key    = st.session_state.get("main_nav_radio", "🏠  Home")
support_key = st.session_state.get("support_nav_radio", "📖  How It Works")

# Use a separate tracker to know which nav group the user last interacted with
if "prev_main" not in st.session_state:
    st.session_state.prev_main = main_key
if "prev_support" not in st.session_state:
    st.session_state.prev_support = support_key

if main_key != st.session_state.prev_main:
    st.session_state.last_nav_group = "main"
    st.session_state.prev_main = main_key
elif support_key != st.session_state.prev_support:
    st.session_state.last_nav_group = "support"
    st.session_state.prev_support = support_key

if st.session_state.last_nav_group == "main":
    page = main_key.split("  ")[1].strip()
else:
    page = support_key.split("  ")[1].strip()


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "Home":
    # Hero
    st.markdown("""
    <div class="v-hero">
        <div class="v-hero-title">Inspect smarter.<br><span>See everything.</span></div>
        <div class="v-hero-sub">
            Vantage turns raw drone telemetry into professional inspection reports —
            automatically. Fly, upload, and get an AI-generated PDF in minutes.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Drone imagery from Unsplash (free to use)
    img1, img2, img3 = st.columns(3)
    with img1:
        st.image("https://images.unsplash.com/photo-1473968512647-3e447244af8f?w=600&q=80",
                 caption="Aerial property inspection", use_container_width=True)
    with img2:
        st.image("https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80",
                 caption="Roof & structure analysis", use_container_width=True)
    with img3:
        st.image("https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&q=80",
                 caption="Infrastructure assessment", use_container_width=True)

    st.markdown("---")

    # Features
    st.markdown('<div style="text-align:center;margin-bottom:1.5rem;"><span class="v-page-title">Why teams choose Vantage</span></div>', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)
    features = [
        ("🛰️", "Drone-Native", "Built specifically for DJI drones and AirData telemetry. No manual data entry for flight records."),
        ("🤖", "AI-Powered Reports", "Claude AI writes professional inspection reports from your findings automatically — in seconds."),
        ("📊", "Risk Scoring", "Three-factor vulnerability model scores every finding by severity, area, and urgency."),
        ("📄", "Instant PDF", "Download a formatted, client-ready PDF report the moment you submit your inspection."),
    ]
    for col, (icon, title, desc) in zip([f1, f2, f3, f4], features):
        with col:
            st.markdown(f"""
            <div class="v-feature-card">
                <div class="v-feature-icon">{icon}</div>
                <div class="v-feature-title">{title}</div>
                <div class="v-feature-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # What we inspect
    st.markdown('<div style="text-align:center;margin-bottom:1.5rem;"><span class="v-page-title">What Vantage inspects</span></div>', unsafe_allow_html=True)

    i1, i2, i3, i4 = st.columns(4)
    inspects = [
        ("https://images.unsplash.com/photo-1599427303058-f04cbcf4756f?w=400&q=80", "Residential Roofs"),
        ("https://images.unsplash.com/photo-1486325212027-8081e485255e?w=400&q=80", "Commercial Buildings"),
        ("https://images.unsplash.com/photo-1509391366360-2e959784a276?w=400&q=80", "Solar Installations"),
        ("https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400&q=80", "Infrastructure"),
    ]
    for col, (img_url, caption) in zip([i1, i2, i3, i4], inspects):
        with col:
            st.image(img_url, caption=caption, use_container_width=True)

    st.markdown("---")

    # Workflow
    st.markdown('<div style="text-align:center;margin-bottom:1.5rem;"><span class="v-page-title">How it works</span></div>', unsafe_allow_html=True)

    w1, w2 = st.columns(2)
    steps = [
        ("Fly your drone", "Use your DJI Air 2S or Air 3 to conduct an aerial inspection of any property."),
        ("Export from AirData", "Sync your flight to airdata.com and export your telemetry as a CSV."),
        ("Submit your findings", "Upload the CSV, document every issue you observed, and hit Submit."),
        ("Download your report", "Vantage scores your findings and Claude AI generates a professional PDF report instantly."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        col = w1 if i <= 2 else w2
        with col:
            st.markdown(f"""
            <div class="v-workflow-step">
                <div class="v-workflow-num">{i}</div>
                <div>
                    <div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.88rem;
                                color:#e8edf5;margin-bottom:3px;">{title}</div>
                    <div style="font-size:0.82rem;color:#8892a4;line-height:1.55;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Testimonials
    st.markdown('<div style="text-align:center;margin-bottom:1.5rem;"><span class="v-page-title">What customers say</span></div>', unsafe_allow_html=True)

    t1, t2, t3 = st.columns(3)
    testimonials = [
        ("We used to spend 3 hours writing inspection reports. With Vantage, the AI writes it in 30 seconds and it's better than what we were producing manually.", "James R. — Property Inspector, Colorado"),
        ("The risk scoring model is exactly what we needed for insurance documentation. It gives us a defensible number we can show underwriters.", "Sarah M. — Commercial Real Estate, Texas"),
        ("Finally a tool built for drone operators, not adapted from something else. The AirData integration is seamless and the reports look completely professional.", "Derek T. — Drone Services Company, Florida"),
    ]
    for col, (text, author) in zip([t1, t2, t3], testimonials):
        with col:
            st.markdown(f"""
            <div class="v-testimonial">
                <div class="v-testimonial-text">"{text}"</div>
                <div class="v-testimonial-author">— {author}</div>
            </div>
            """, unsafe_allow_html=True)

    footer_nav("Home")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD (combined overview + analytics)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Dashboard":
    st.markdown('<div class="v-page-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">Live overview of your inspection activity, risk trends, and flight data.</div>', unsafe_allow_html=True)

    inspections = load_inspections()
    flights     = load_flights()
    completed   = [i for i in inspections if i["status"] == "Complete"]
    avg = (sum(i["overall_risk_score"] or 0 for i in completed) / len(completed)) if completed else 0
    all_findings = []
    for i in completed:
        all_findings.extend(json.loads(i.get("findings") or "[]"))

    # ── Top metrics ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Inspections", len(inspections))
    c2.metric("Completed",         len(completed))
    c3.metric("Total Flights",     len(flights))
    c4.metric("Avg Risk Score",    f"{avg:.1f}" if completed else "—")
    c5.metric("Total Findings",    len(all_findings))

    st.markdown("---")

    # ── Row 1: Recent inspections + Risk distribution ──
    left, right = st.columns([3, 1])

    with left:
        st.markdown('<div class="v-section">Recent Inspections</div>', unsafe_allow_html=True)
        if not inspections:
            st.info("No inspections yet. Click **New Inspection** in the sidebar.")
        else:
            for insp in inspections[:6]:
                tier  = insp.get("risk_tier") or ""
                score = insp.get("overall_risk_score")
                addr  = insp.get("property_address") or "Unknown"
                color = TIER_COLORS.get(tier, "#8892a4")
                st.markdown(f"""
                <div class="v-card">
                  <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;">
                    <div style="flex:1;min-width:0;">
                      <div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.9rem;
                                  margin-bottom:3px;white-space:nowrap;overflow:hidden;
                                  text-overflow:ellipsis;color:#e8edf5;">{addr}</div>
                      <div style="font-size:0.75rem;color:#4a5568;">
                        {insp['date']} &nbsp;·&nbsp; {insp.get('inspection_type','—')} &nbsp;·&nbsp; {insp.get('inspector_name','—')}
                      </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;">
                      {badge(tier)}
                      <div style="font-family:Manrope,sans-serif;font-size:1.25rem;
                                  font-weight:800;color:{color};margin-top:5px;">
                        {f"{score:.1f}" if score else "—"}
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="v-section">Risk Distribution</div>', unsafe_allow_html=True)
        tier_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for i in completed:
            t = i.get("risk_tier", "Low")
            tier_counts[t] = tier_counts.get(t, 0) + 1
        total = max(sum(tier_counts.values()), 1)
        for tier, count in tier_counts.items():
            color = TIER_COLORS[tier]
            pct   = int((count / total) * 100)
            st.markdown(f"""
            <div class="v-bar-wrap">
              <div class="v-bar-row">
                <span style="color:#8892a4;">{tier}</span>
                <span style="font-family:Manrope,sans-serif;font-weight:700;color:#e8edf5;">{count}</span>
              </div>
              <div class="v-bar-bg">
                <div class="v-bar-fill" style="width:{pct}%;background:{color};"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="v-section">Recent Flights</div>', unsafe_allow_html=True)
        for f in flights[:4]:
            st.markdown(f"""
            <div class="v-stat-row">
              <div>
                <div style="font-size:0.78rem;font-weight:600;color:#e8edf5;white-space:nowrap;
                            overflow:hidden;text-overflow:ellipsis;max-width:110px;">
                  {f.get('location_name','—')}
                </div>
                <div style="font-size:0.68rem;color:#4a5568;">{f.get('date','—')}</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:0.78rem;font-weight:600;color:#e8edf5;">
                  {f.get('duration_min',0):.1f}m
                </div>
                <div style="font-size:0.68rem;color:#4a5568;">
                  {f.get('battery_start_pct',0)}%→{f.get('battery_end_pct',0)}%
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    if not completed:
        st.info("Complete inspections to unlock charts and analytics below.")
        st.stop()

    st.markdown("---")
    st.markdown('<div class="v-page-title" style="font-size:1.1rem;">Analytics</div>', unsafe_allow_html=True)

    # ── Row 2: Charts ──
    tab1, tab2, tab3 = st.tabs(["Risk Scores", "Findings Breakdown", "Flight Stats"])

    with tab1:
        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown('<div class="v-section">Risk Score Over Time</div>', unsafe_allow_html=True)
            df_scores = pd.DataFrame([{
                "Date":  i["date"],
                "Score": i["overall_risk_score"],
            } for i in sorted(completed, key=lambda x: x["date"])])
            st.line_chart(df_scores.set_index("Date")["Score"])
        with ch2:
            st.markdown('<div class="v-section">Risk Tier Distribution</div>', unsafe_allow_html=True)
            tier_df = pd.DataFrame({"Tier": list(tier_counts.keys()), "Count": list(tier_counts.values())})
            st.bar_chart(tier_df.set_index("Tier"))

        st.markdown('<div class="v-section">Risk Score by Property</div>', unsafe_allow_html=True)
        prop_df = pd.DataFrame([{
            "Property": (i.get("property_address","—") or "")[:30],
            "Score":    i["overall_risk_score"],
        } for i in completed])
        st.bar_chart(prop_df.set_index("Property")["Score"])

    with tab2:
        if not all_findings:
            st.info("No findings data yet.")
        else:
            cat_counts = {}
            sev_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
            urgency_by_cat = {}
            count_by_cat   = {}
            for f in all_findings:
                cat = f.get("category","Other")
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                sev = f.get("severity","Low")
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
                urgency_by_cat[cat] = urgency_by_cat.get(cat, 0) + f.get("urgency_days", 90)
                count_by_cat[cat]   = count_by_cat.get(cat, 0) + 1

            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="v-section">Findings by Category</div>', unsafe_allow_html=True)
                st.bar_chart(pd.DataFrame({"Category": list(cat_counts.keys()), "Count": list(cat_counts.values())}).set_index("Category"))
            with col2:
                st.markdown('<div class="v-section">Findings by Severity</div>', unsafe_allow_html=True)
                st.bar_chart(pd.DataFrame({"Severity": list(sev_counts.keys()), "Count": list(sev_counts.values())}).set_index("Severity"))

            st.markdown('<div class="v-section">Average Days to Fix by Category</div>', unsafe_allow_html=True)
            avg_urgency = {cat: round(urgency_by_cat[cat] / count_by_cat[cat], 1) for cat in urgency_by_cat}
            st.bar_chart(pd.DataFrame({"Category": list(avg_urgency.keys()), "Avg Days": list(avg_urgency.values())}).set_index("Category"))

    with tab3:
        if not flights:
            st.info("No flight data yet.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="v-section">Battery Used per Flight (%)</div>', unsafe_allow_html=True)
                bat_df = pd.DataFrame([{
                    "Flight": (f.get("location_name","—") or "")[:20],
                    "Used":   (f.get("battery_start_pct", 0) or 0) - (f.get("battery_end_pct", 0) or 0),
                } for f in flights])
                st.bar_chart(bat_df.set_index("Flight")["Used"])
            with col2:
                st.markdown('<div class="v-section">Flight Duration (min)</div>', unsafe_allow_html=True)
                dur_df = pd.DataFrame([{
                    "Flight":   (f.get("location_name","—") or "")[:20],
                    "Duration": round(f.get("duration_min", 0), 1),
                } for f in flights])
                st.bar_chart(dur_df.set_index("Flight")["Duration"])

            st.markdown('<div class="v-section">Max Altitude per Flight (ft)</div>', unsafe_allow_html=True)
            alt_df = pd.DataFrame([{
                "Flight":   (f.get("location_name","—") or "")[:25],
                "Altitude": round(f.get("altitude_ft", 0), 0),
            } for f in flights])
            st.bar_chart(alt_df.set_index("Flight")["Altitude"])

    footer_nav("Dashboard")


# ══════════════════════════════════════════════════════════════════════════════
# NEW INSPECTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "New Inspection":
    st.markdown('<div class="v-page-title">New Inspection</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">Fill in each section and submit to score findings and generate your AI report.</div>', unsafe_allow_html=True)

    st.markdown('<div class="v-form-section">', unsafe_allow_html=True)
    st.markdown('<div class="v-form-section-title">✈️ &nbsp;Flight Data</div>', unsafe_allow_html=True)
    uploaded_csv = st.file_uploader("Upload AirData CSV export", type=["csv"],
                                    help="Export from airdata.com → your flight → Download CSV")
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("Property Address", placeholder="123 Main St, Springfield")
        pilot    = st.text_input("Pilot Name")
    with col2:
        drone   = st.selectbox("Drone Model", ["DJI Air 2S", "DJI Air 3", "Other"])
        weather = st.text_input("Weather Conditions", placeholder="Clear, 72°F, light wind SW")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="v-form-section">', unsafe_allow_html=True)
    st.markdown('<div class="v-form-section-title">📋 &nbsp;Inspection Details</div>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        inspection_type = st.selectbox("Inspection Type", INSPECTION_TYPES)
    with col4:
        inspector_name = st.text_input("Inspector Name")
    inspection_notes = st.text_area("Additional Notes (optional)",
                                    placeholder="Any additional context...", height=75)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="v-form-section">', unsafe_allow_html=True)
    st.markdown('<div class="v-form-section-title">🔍 &nbsp;Findings</div>', unsafe_allow_html=True)
    st.caption("Document every issue observed. More detail = better AI report.")

    findings_data = []
    for i, _ in enumerate(st.session_state.findings):
        with st.expander(f"Finding #{i+1}", expanded=(i == 0)):
            fc1, fc2 = st.columns(2)
            with fc1:
                category = st.selectbox("Category",            CATEGORIES, key=f"cat_{i}")
                severity = st.selectbox("Severity",            SEVERITIES, key=f"sev_{i}")
                area     = st.number_input("Affected Area (sq ft)", min_value=0.0, step=10.0, key=f"area_{i}")
                urgency  = st.number_input("Fix within (days)",     min_value=1, max_value=365, value=90, key=f"urg_{i}")
            with fc2:
                description = st.text_area("What was observed",    key=f"desc_{i}", height=90,
                                           placeholder="Describe the issue in detail...")
                location_on = st.text_input("Location on property", key=f"loc_{i}",
                                            placeholder="e.g. NW corner roof ridge")
                action      = st.text_input("Recommended action",  key=f"action_{i}",
                                            placeholder="e.g. Replace and reseal immediately")
            if len(st.session_state.findings) > 1:
                if st.button(f"Remove Finding #{i+1}", key=f"remove_{i}"):
                    st.session_state.findings.pop(i)
                    st.rerun()
            findings_data.append({
                "finding_id": f"FND-{uuid.uuid4().hex[:6].upper()}",
                "category": category, "description": description,
                "location_on_property": location_on, "severity": severity,
                "severity_score": SEVERITY_SCORES[severity],
                "affected_area_sqft": area, "recommended_action": action,
                "urgency_days": int(urgency), "photo_refs": [],
            })

    if st.button("＋  Add Finding"):
        st.session_state.findings.append({})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Submit & Generate Report", type="primary", use_container_width=True):
        errors = []
        if not uploaded_csv:           errors.append("Please upload an AirData CSV.")
        if not location.strip():       errors.append("Please enter a property address.")
        if not pilot.strip():          errors.append("Please enter a pilot name.")
        if not inspector_name.strip(): errors.append("Please enter an inspector name.")
        if not weather.strip():        errors.append("Please enter weather conditions.")
        for e in errors: st.error(e)
        if not errors:
            with st.spinner("Running pipeline — ingesting flight, scoring findings, generating AI report..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(uploaded_csv.read())
                        tmp_path = tmp.name
                    flight_record = ingest_csv(csv_path=tmp_path, location_name=location,
                                               drone_model=drone, pilot_name=pilot,
                                               weather_conditions=weather)
                    insert_flight_record(flight_record)
                    flight_id     = flight_record["flight_id"]
                    inspection_id = f"INS-{uuid.uuid4().hex[:8].upper()}"
                    insert_inspection_record({
                        "inspection_id": inspection_id, "flight_id": flight_id,
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "property_address": location, "inspection_type": inspection_type,
                        "inspector_name": inspector_name, "findings": json.dumps(findings_data),
                        "overall_risk_score": None, "risk_tier": None, "status": "Draft",
                    })
                    link_inspection_to_flight(flight_id, inspection_id)
                    result      = process_inspection(inspection_id, verbose=False)
                    report_path = generate_report(inspection_id)
                    os.unlink(tmp_path)
                    st.cache_data.clear()
                    st.session_state.findings = [{}]
                    st.success(f"✅ Inspection complete — ID: {inspection_id}")
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Risk Score", f"{result['score']} / 100")
                    r2.metric("Risk Tier",  result['tier'])
                    r3.metric("Findings",   len(findings_data))
                    with open(report_path, "rb") as f:
                        st.download_button("Download PDF Report", data=f,
                                           file_name=report_path.name,
                                           mime="application/pdf",
                                           use_container_width=True)
                except Exception as e:
                    st.error(f"Pipeline error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# INSPECTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Inspections":
    st.markdown('<div class="v-page-title">Inspections</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">All inspection records. Expand any row to view findings or manage.</div>', unsafe_allow_html=True)

    inspections = load_inspections()
    if not inspections:
        st.info("No inspections yet.")
    else:
        f1, f2, f3 = st.columns(3)
        with f1: status_filter = st.selectbox("Status", ["All", "Draft", "Complete", "Reviewed"])
        with f2: type_filter   = st.selectbox("Type", ["All"] + INSPECTION_TYPES)
        with f3: tier_filter   = st.selectbox("Risk Tier", ["All", "Critical", "High", "Medium", "Low"])

        filtered = inspections
        if status_filter != "All": filtered = [i for i in filtered if i["status"] == status_filter]
        if type_filter   != "All": filtered = [i for i in filtered if i.get("inspection_type") == type_filter]
        if tier_filter   != "All": filtered = [i for i in filtered if i.get("risk_tier") == tier_filter]

        st.caption(f"Showing {len(filtered)} of {len(inspections)} inspections")
        st.markdown("---")

        for insp in filtered:
            tier  = insp.get("risk_tier") or ""
            score = insp.get("overall_risk_score")
            addr  = insp.get("property_address") or "Unknown"
            with st.expander(f"{addr}  ·  {insp['date']}  ·  Score: {f'{score:.1f}' if score else '—'}"):
                d1, d2, d3 = st.columns(3)
                d1.markdown(f"**ID**<br><code style='font-size:0.75rem'>{insp['inspection_id']}</code>", unsafe_allow_html=True)
                d2.markdown(f"**Type**<br>{insp.get('inspection_type','—')}", unsafe_allow_html=True)
                d3.markdown(f"**Inspector**<br>{insp.get('inspector_name','—')}", unsafe_allow_html=True)
                d4, d5, d6 = st.columns(3)
                d4.markdown(f"**Status**<br>{insp.get('status','—')}", unsafe_allow_html=True)
                d5.markdown(f"**Risk Tier**<br>{badge(tier)}", unsafe_allow_html=True)
                d6.markdown(f"**Flight**<br><code style='font-size:0.75rem'>{insp.get('flight_id') or '—'}</code>", unsafe_allow_html=True)
                findings = json.loads(insp.get("findings") or "[]")
                if findings:
                    st.markdown('<div class="v-section">Findings</div>', unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame([{
                        "Category": f.get("category"), "Description": f.get("description"),
                        "Location": f.get("location_on_property"), "Severity": f.get("severity"),
                        "Area (sqft)": f.get("affected_area_sqft"),
                        "Urgency": f"{f.get('urgency_days')} days",
                        "Action": f.get("recommended_action"),
                    } for f in findings]), use_container_width=True)
                st.markdown("---")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Re-generate Report", key=f"regen_{insp['inspection_id']}", use_container_width=True):
                        with st.spinner("Generating..."):
                            try:
                                rp = generate_report(insp["inspection_id"])
                                with open(rp, "rb") as f:
                                    st.download_button("Download PDF", data=f, file_name=rp.name,
                                                       mime="application/pdf", use_container_width=True,
                                                       key=f"dl_{insp['inspection_id']}")
                            except Exception as e:
                                st.error(str(e))
                with b2:
                    if st.button("Delete", key=f"del_{insp['inspection_id']}", use_container_width=True):
                        delete_inspection(insp["inspection_id"])
                        st.success("Deleted.")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FLIGHTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Flights":
    st.markdown('<div class="v-page-title">Flight Records</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">All ingested drone flights from AirData CSV exports.</div>', unsafe_allow_html=True)

    flights = load_flights()
    if not flights:
        st.info("No flights yet.")
    else:
        f1, f2, f3 = st.columns(3)
        with f1:
            drone_filter = st.selectbox("Drone", ["All"] + sorted(set(f.get("drone_model","") for f in flights if f.get("drone_model"))))
        with f2:
            pilot_filter = st.selectbox("Pilot", ["All"] + sorted(set(f.get("pilot_name","") for f in flights if f.get("pilot_name"))))
        with f3:
            months = sorted(set(f["date"][:7] for f in flights), reverse=True)
            month_filter = st.selectbox("Month", ["All"] + months)

        filtered = flights
        if drone_filter != "All": filtered = [f for f in filtered if f.get("drone_model") == drone_filter]
        if pilot_filter != "All": filtered = [f for f in filtered if f.get("pilot_name") == pilot_filter]
        if month_filter != "All": filtered = [f for f in filtered if f["date"].startswith(month_filter)]

        st.caption(f"Showing {len(filtered)} of {len(flights)} flights")
        st.markdown("---")

        for f in filtered:
            with st.expander(f"{f.get('location_name','—')}  ·  {f['date']}  ·  {f.get('drone_model','—')}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Duration",  f"{f.get('duration_min',0):.1f} min")
                c2.metric("Max Alt",   f"{f.get('altitude_ft',0):.0f} ft")
                c3.metric("Max Speed", f"{f.get('max_speed_mph',0):.1f} mph")
                c4.metric("Battery",   f"{f.get('battery_start_pct',0)}% → {f.get('battery_end_pct',0)}%")
                st.markdown(f"**Flight ID:** `{f['flight_id']}` &nbsp;·&nbsp; **Pilot:** {f.get('pilot_name','—')} &nbsp;·&nbsp; **Weather:** {f.get('weather_conditions','—')}")
                if f.get("gps_lat"):
                    st.markdown(f"**GPS:** {f['gps_lat']:.6f}, {f['gps_lon']:.6f}")
                st.markdown("---")
                if st.button("Delete Flight", key=f"del_flt_{f['flight_id']}", use_container_width=True):
                    delete_flight(f["flight_id"])
                    st.success("Deleted.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Reports":
    st.markdown('<div class="v-page-title">Reports</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">View, download, and re-generate all AI inspection reports.</div>', unsafe_allow_html=True)

    PROJECT_ROOT = Path(__file__).parent.parent
    REPORTS_DIR  = PROJECT_ROOT / "reports"

    # Get all report files
    report_files = sorted(REPORTS_DIR.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True) if REPORTS_DIR.exists() else []
    md_files     = {f.stem: f for f in REPORTS_DIR.glob("*.md")} if REPORTS_DIR.exists() else {}

    inspections = load_inspections()
    insp_lookup = {i["inspection_id"]: i for i in inspections}

    if not report_files:
        st.info("No reports generated yet. Submit an inspection to create your first report.")
    else:
        st.caption(f"{len(report_files)} report(s) on file")
        st.markdown("---")

        for pdf_path in report_files:
            # Parse filename: 20260407-042041_INS-XXXXXXXX_address.pdf
            parts     = pdf_path.stem.split("_", 2)
            timestamp = parts[0] if len(parts) > 0 else "—"
            insp_id   = parts[1] if len(parts) > 1 else "—"
            address   = parts[2].replace("_", " ") if len(parts) > 2 else "—"

            # Format timestamp
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
                date_str = dt.strftime("%b %d, %Y at %I:%M %p")
            except Exception:
                date_str = timestamp

            # Get inspection metadata if available
            insp      = insp_lookup.get(insp_id, {})
            tier      = insp.get("risk_tier", "—")
            score     = insp.get("overall_risk_score")
            file_size = round(pdf_path.stat().st_size / 1024, 1)

            with st.expander(f"{address}  ·  {date_str}  ·  {insp_id}"):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**Generated**<br>{date_str}", unsafe_allow_html=True)
                col2.markdown(f"**Risk Score**<br>{f'{score:.1f}' if score else '—'}", unsafe_allow_html=True)
                col3.markdown(f"**Risk Tier**<br>{badge(tier)}", unsafe_allow_html=True)

                st.markdown(f"**File:** `{pdf_path.name}` &nbsp;·&nbsp; **Size:** {file_size} KB")

                # Read report markdown for preview
                md_path = md_files.get(pdf_path.stem)
                if md_path and md_path.exists():
                    with st.expander("Preview Report Text"):
                        content = md_path.read_text(encoding="utf-8")
                        st.markdown(content)

                st.markdown("---")
                b1, b2, b3 = st.columns(3)
                with b1:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "Download PDF",
                            data=f,
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"dl_{pdf_path.stem}"
                        )
                with b2:
                    if md_path and md_path.exists():
                        with open(md_path, "rb") as f:
                            st.download_button(
                                "Download Markdown",
                                data=f,
                                file_name=md_path.name,
                                mime="text/markdown",
                                use_container_width=True,
                                key=f"dlmd_{pdf_path.stem}"
                            )
                with b3:
                    if insp_id in insp_lookup:
                        if st.button("Re-generate", key=f"regen_{pdf_path.stem}", use_container_width=True):
                            with st.spinner("Generating updated report..."):
                                try:
                                    new_path = generate_report(insp_id)
                                    st.success("Report updated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "How It Works":
    st.markdown('<div class="v-page-title">How It Works</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">The complete aerial inspection workflow, from flight to final report.</div>', unsafe_allow_html=True)
    for i, (title, desc) in enumerate([
        ("Fly Your Drone", "Use your DJI Air 2S or Air 3 to conduct an aerial inspection of any property. Capture footage and sync your flight to AirData (airdata.com)."),
        ("Export AirData CSV", "Log into airdata.com, find your flight, and export it as a CSV. This contains your full telemetry — altitude, speed, GPS, battery, and more."),
        ("Submit Your Inspection", "Go to New Inspection, upload your CSV, document your findings for each issue observed, and hit Submit."),
        ("AI Report Generation", "Vantage ingests your flight data, runs the three-factor vulnerability scoring model, and generates a professional PDF report via Claude AI."),
        ("Download & Share", "Download your report instantly. Share it with property owners, insurers, or clients — fully formatted and ready to present."),
    ], 1):
        st.markdown(f'''
        <div class="v-step">
            <div class="v-step-num">{i}</div>
            <div>
                <div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.9rem;
                            margin-bottom:3px;color:#e8edf5;">{title}</div>
                <div style="font-size:0.83rem;color:#8892a4;line-height:1.6;">{desc}</div>
            </div>
        </div>''', unsafe_allow_html=True)

    st.markdown('<div class="v-section">How Vantage Calculates Risk</div>', unsafe_allow_html=True)
    st.markdown('''
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.5rem;margin-bottom:1rem;">
        <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:#e8edf5;margin-bottom:1rem;">
            Every finding is scored on three factors
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.75rem;margin-bottom:1.25rem;">
            <div style="background:rgba(79,142,247,0.08);border:1px solid rgba(79,142,247,0.2);border-radius:8px;padding:1rem;">
                <div style="font-size:1.25rem;margin-bottom:0.4rem;">⚠️</div>
                <div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.85rem;color:#e8edf5;margin-bottom:0.3rem;">Severity</div>
                <div style="font-size:0.78rem;color:#8892a4;line-height:1.5;">
                    Low = 2 &nbsp;·&nbsp; Medium = 4<br>High = 7 &nbsp;·&nbsp; Critical = 10
                </div>
            </div>
            <div style="background:rgba(79,142,247,0.08);border:1px solid rgba(79,142,247,0.2);border-radius:8px;padding:1rem;">
                <div style="font-size:1.25rem;margin-bottom:0.4rem;">📐</div>
                <div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.85rem;color:#e8edf5;margin-bottom:0.3rem;">Affected Area</div>
                <div style="font-size:0.78rem;color:#8892a4;line-height:1.5;">
                    &lt;50 sqft = 0.8×<br>50–200 sqft = 1.0×<br>&gt;200 sqft = 1.2×
                </div>
            </div>
            <div style="background:rgba(79,142,247,0.08);border:1px solid rgba(79,142,247,0.2);border-radius:8px;padding:1rem;">
                <div style="font-size:1.25rem;margin-bottom:0.4rem;">⏱️</div>
                <div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.85rem;color:#e8edf5;margin-bottom:0.3rem;">Urgency</div>
                <div style="font-size:0.78rem;color:#8892a4;line-height:1.5;">
                    ≤7 days = 1.5×<br>8–30 days = 1.2×<br>31–90 days = 1.0×<br>&gt;90 days = 0.8×
                </div>
            </div>
        </div>
        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem 1rem;margin-bottom:1rem;
                    font-size:0.82rem;color:#8892a4;font-family:monospace;">
            finding_score = severity × area_weight × urgency_weight
        </div>
        <div style="font-family:Manrope,sans-serif;font-size:0.85rem;font-weight:600;color:#e8edf5;margin-bottom:0.6rem;">Risk Tiers</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:0.5rem;">
            <div style="background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.2);border-radius:6px;
                        padding:0.5rem 0.75rem;text-align:center;">
                <div style="font-size:0.68rem;font-weight:600;color:#4ade80;text-transform:uppercase;letter-spacing:0.05em;">Low</div>
                <div style="font-size:0.8rem;color:#8892a4;margin-top:2px;">0 – 25</div>
            </div>
            <div style="background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.2);border-radius:6px;
                        padding:0.5rem 0.75rem;text-align:center;">
                <div style="font-size:0.68rem;font-weight:600;color:#fbbf24;text-transform:uppercase;letter-spacing:0.05em;">Medium</div>
                <div style="font-size:0.8rem;color:#8892a4;margin-top:2px;">26 – 50</div>
            </div>
            <div style="background:rgba(251,146,60,0.1);border:1px solid rgba(251,146,60,0.2);border-radius:6px;
                        padding:0.5rem 0.75rem;text-align:center;">
                <div style="font-size:0.68rem;font-weight:600;color:#fb923c;text-transform:uppercase;letter-spacing:0.05em;">High</div>
                <div style="font-size:0.8rem;color:#8892a4;margin-top:2px;">51 – 75</div>
            </div>
            <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.2);border-radius:6px;
                        padding:0.5rem 0.75rem;text-align:center;">
                <div style="font-size:0.68rem;font-weight:600;color:#f87171;text-transform:uppercase;letter-spacing:0.05em;">Critical</div>
                <div style="font-size:0.8rem;color:#8892a4;margin-top:2px;">76 – 100</div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FAQ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "FAQ":
    st.markdown('<div class="v-page-title">FAQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">Common questions about Vantage.</div>', unsafe_allow_html=True)
    for q, a in [
        ("What drones are supported?", "DJI Air 2S and Air 3. Any DJI drone that syncs to AirData and exports a telemetry CSV will work."),
        ("Do I need an Anthropic API key?", "Yes — report generation uses Claude AI. Get a key at console.anthropic.com. Typical cost is a few cents per report."),
        ("Where is my data stored?", "Locally in a SQLite database on the machine running Vantage. Reports are saved as PDFs in the reports/ folder."),
        ("Why is my risk score low?", "One finding, even Critical, won't push a score into High tier alone — that reflects real-world risk. Add all findings you observed for an accurate overall score."),
        ("Can I re-generate a report?", "Yes — go to Inspections, expand any record, and click Re-generate Report."),
        ("How do I delete records?", "Go to Inspections or Flights, expand any record, and click Delete. This action is permanent."),
        ("Why does flight data show 'not recorded'?", "This happens when an inspection was submitted without a linked AirData CSV. Always upload your CSV through the New Inspection form."),
    ]:
        st.markdown(f'<div class="v-faq-q">{q}</div><div class="v-faq-a">{a}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Contact":
    st.markdown('<div class="v-page-title">Contact</div>', unsafe_allow_html=True)
    st.markdown('<div class="v-page-sub">Get in touch with the Vantage team.</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.form("contact_form"):
            name    = st.text_input("Your Name")
            email   = st.text_input("Email Address")
            subject = st.selectbox("Subject", ["General Inquiry", "Bug Report", "Feature Request", "Partnership"])
            message = st.text_area("Message", height=140)
            if st.form_submit_button("Send Message", use_container_width=True):
                if name and email and message:
                    st.success("✅ Message received. We'll get back to you within 24 hours.")
                else:
                    st.error("Please fill in all fields.")
    with col2:
        st.markdown('<div class="v-section">Get in Touch</div>', unsafe_allow_html=True)
        st.markdown('''<div class="v-info-block">
            <strong style="color:#e8edf5;">Support</strong><br>
            For technical questions, bug reports, or feature requests, use the contact form.<br><br>
            <strong style="color:#e8edf5;">Response Time</strong><br>
            We typically respond within 24 hours on business days.<br><br>
            <strong style="color:#e8edf5;">Documentation</strong><br>
            See How It Works and FAQ for answers to common questions.
        </div>''', unsafe_allow_html=True)
