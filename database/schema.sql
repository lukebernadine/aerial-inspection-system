CREATE TABLE IF NOT EXISTS flight_records (
    flight_id       TEXT PRIMARY KEY,
    inspection_id   TEXT,
    date            TEXT NOT NULL,
    location_name   TEXT,
    gps_lat         REAL,
    gps_lon         REAL,
    altitude_ft     REAL,
    duration_min    REAL,
    distance_ft     REAL,
    max_speed_mph   REAL,
    drone_model     TEXT,
    weather_conditions TEXT,
    battery_start_pct  INTEGER,
    battery_end_pct    INTEGER,
    pilot_name      TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS inspection_records (
    inspection_id       TEXT PRIMARY KEY,
    flight_id           TEXT,
    date                TEXT NOT NULL,
    property_address    TEXT NOT NULL,
    inspection_type     TEXT CHECK(inspection_type IN ('Roof','Perimeter','Structural','General')),
    inspector_name      TEXT,
    findings            TEXT,
    overall_risk_score  REAL,
    risk_tier           TEXT CHECK(risk_tier IN ('Low','Medium','High','Critical')),
    status              TEXT DEFAULT 'Draft' CHECK(status IN ('Draft','Complete','Reviewed')),
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (flight_id) REFERENCES flight_records(flight_id)
);

CREATE INDEX IF NOT EXISTS idx_inspections_flight ON inspection_records(flight_id);
CREATE INDEX IF NOT EXISTS idx_inspections_date   ON inspection_records(date);
CREATE INDEX IF NOT EXISTS idx_inspections_status ON inspection_records(status);
