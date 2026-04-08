# Automated Aerial Inspection & Vulnerability Assessment System

A portfolio project demonstrating drone operations, automated data pipelines, AI-powered report generation, and vulnerability assessment workflows.

**Stack:** Python 3.11 · SQLite · Claude API · Streamlit · AirData · DJI Air 2S/Air 3

---

## Pipeline Overview

```
AirData CSV → ingest_flight.py → SQLite
                                     ↓
Manual entry → ingest_inspection.py → SQLite
                                     ↓
               score_and_merge.py  (risk scoring)
                                     ↓
               report_generator.py (Claude API → PDF)
                                     ↓
               streamlit_app.py    (dashboard)
```

## Quick Start

```bash
# 1. Clone and install dependencies
git clone https://github.com/YOUR_USERNAME/aerial-inspection-system
cd aerial-inspection-system
pip install -r requirements.txt

# 2. Set up environment
cp .env.template .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Initialise database
python -c "from pipeline.storage import initialise_db; initialise_db()"

# 4. Load sample data (optional — test before real flight)
python data/sample_data/load_sample_data.py

# 5. Launch dashboard
streamlit run dashboard/streamlit_app.py
```

## Running a Real Inspection

```bash
# Step 1: Enter inspection findings (interactive CLI)
python pipeline/ingest_inspection.py

# Step 2: Run full pipeline (ingest flight + score + report)
python pipeline/run_pipeline.py \
  --csv path/to/airdata-export.csv \
  --inspection-id INS-XXXXXXXX \
  --location "123 Main St" \
  --drone "DJI Air 2S" \
  --pilot "Your Name" \
  --weather "Clear, 72F, light wind"
```

## File Structure

```
aerial-inspection-system/
├── pipeline/
│   ├── ingest_flight.py       # AirData CSV parser
│   ├── ingest_inspection.py   # CLI findings entry
│   ├── score_and_merge.py     # Vulnerability scoring model
│   ├── storage.py             # SQLite read/write layer
│   ├── report_generator.py    # Claude API + PDF output
│   └── run_pipeline.py        # Master runner
├── dashboard/
│   └── streamlit_app.py       # Streamlit dashboard
├── data/
│   ├── schema.sql             # Database schema
│   ├── inspections.db         # SQLite DB (gitignored)
│   └── sample_data/
│       └── load_sample_data.py
├── reports/                   # Generated PDFs (gitignored)
├── .env.template
├── .gitignore
├── requirements.txt
└── README.md
```

## Vulnerability Scoring Model

```
finding_score  = severity_score × area_weight × urgency_weight

area_weight    : <50 sqft=0.8  |  50-200=1.0  |  >200=1.2
urgency_weight : ≤7 days=1.5   |  8-30=1.2    |  31-90=1.0  |  >90=0.8

overall_score  = min(100, (Σ finding_scores / 90) × 100)

Risk tiers: 0-25=Low | 26-50=Medium | 51-75=High | 76-100=Critical
```
