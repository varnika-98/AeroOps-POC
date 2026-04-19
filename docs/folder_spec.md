# AeroOps AI — Folder & File Spec

> A complete reference for every folder and file in the project.

---

## Project Root

```
MiraclesPOC/
├── .env                    # Actual API keys (gitignored)
├── .env.example            # Template — ANTHROPIC_API_KEY placeholder
├── .gitignore              # Ignores data/, .env, __pycache__, .vs/
├── README.md               # Project overview, quick-start, tech stack
├── requirements.txt        # Python deps: streamlit, plotly, pandas, duckdb, anthropic, faker
├── .streamlit/
│   └── config.toml         # Streamlit theme (navy/blue palette) + headless server config
├── simulator/              # Data generation engine
├── pipeline/               # Bronze → Silver → Gold ETL
├── ai/                     # Claude AI integration
├── utils/                  # Shared helpers (charts, KPIs, lineage, theme)
├── app/                    # Streamlit dashboard (6 pages)
├── data/                   # Runtime-generated data (gitignored)
├── docs/                   # Architecture, demo script
└── resources/              # Interview prep notes
```

---

## `simulator/` — IoT Data Generation Engine

Generates realistic airport IoT sensor data for 6 streams, pipeline execution logs, and injectable failure scenarios.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `generate_all_events`, `write_events_to_json`, `generate_pipeline_logs`, `inject_schema_drift`, `inject_sensor_outage`, `inject_traffic_spike`, `AIRPORT_CONFIG` |
| `config.py` | Airport constants — terminals, gates, runways, airlines, aircraft types, peak hours, event rates per stream |
| `airport_generator.py` | Core event generator — produces ~66K events across 6 streams for a 24-hour window |
| `pipeline_log_generator.py` | Simulates ETL pipeline execution logs (432 entries: 24 runs × 6 streams × 3 stages) |
| `failure_injector.py` | Three failure scenarios for testing observability |

### `config.py` — Constants & Lookups

```
AIRPORT_CONFIG          Airport metadata (name, code, terminals, gates, runways, airlines, etc.)
STREAM_NAMES            ["flights", "passengers", "cargo", "environmental", "runway", "security"]
GATES                   Generated list: Gate-101 through Gate-320 (3 terminals × 20 gates)
ZONES                   Terminal zones for passenger flow (Departures-North, Arrivals-South, etc.)
CHECKPOINTS             Security + gate + check-in checkpoint names
AIRCRAFT_CAPACITY       Mapping: aircraft_type → max passenger count
```

### `airport_generator.py` — 6-Stream Event Generator

**Helper functions:**
- `_is_peak(hour)` — True if hour falls in peak ranges (7-9, 11-13, 17-19)
- `_peak_multiplier(hour)` — Returns 2-3x during peaks, 1x otherwise
- `_make_event_id(prefix, ts, seq)` — Creates IDs like "FLT-20260419-001"
- `_iso(ts)` — Formats datetime to ISO 8601
- `_diurnal_temperature(hour)` — Realistic day/night temperature curve

**Per-stream generators** (each returns `list[dict]`):
| Function | Stream | Key Behaviors |
|----------|--------|---------------|
| `generate_flight_events()` | ✈️ flights | Delays follow exponential distribution (mean 25 min), 70% on-time, 3% cancelled |
| `generate_passenger_events()` | 👥 passengers | Wait times correlate with peak hours, throughput 200-400/hr |
| `generate_cargo_events()` | 📦 cargo | 70% baggage, 20% cargo, 10% mail; weight 1-50kg realistic |
| `generate_environmental_events()` | 🌡️ environmental | Diurnal temperature curve, 95% HVAC normal, CO2 400-800 |
| `generate_runway_events()` | 🛬 runway | Weather-correlated status, friction index 0.5-0.9, visibility 5-15km |
| `generate_security_events()` | 🔒 security | 95% routine scans, 5% anomalies; response time only for non-routine |

**Orchestration:**
- `generate_all_events(base_date, hours, rate_multiplier)` — Runs all 6 generators for each simulated minute, respects peak-hour multipliers
- `write_events_to_json(all_events)` — Writes to `data/bronze/{stream}/{stream}_events.json`

**CLI:** `python -m simulator.airport_generator`

### `pipeline_log_generator.py` — ETL Log Simulator

- `generate_pipeline_logs(base_date, runs)` — Creates 432 log entries (24 hourly runs × 6 streams × 3 stages)
- `write_pipeline_logs(logs)` — Writes to `data/logs/pipeline_logs.parquet`

Each log entry: `run_id, timestamp, stage, stream, status, records_in, records_out, records_quarantined, duration_sec, error_message`

**CLI:** `python -m simulator.pipeline_log_generator`

### `failure_injector.py` — 3 Failure Scenarios

| Function | Scenario | What It Does |
|----------|----------|-------------|
| `inject_schema_drift(events, stream="runway")` | Runway sensor firmware bug | Multiplies `wind_speed_kph` by 1.6 (simulates mph→kph confusion). Some values exceed 0-200 range → quarantined |
| `inject_sensor_outage(events, stream="passengers", checkpoints=3)` | Checkpoint offline | Removes all events from 3 random checkpoints → throughput KPIs underreport |
| `inject_traffic_spike(multiplier=3.0)` | Holiday traffic | Returns multiplier for `generate_all_events(rate_multiplier=3.0)` → 3x volume |

---

## `pipeline/` — Medallion ETL Pipeline

Processes raw IoT events through Bronze → Silver → Gold layers with quality enforcement, quarantine, and KPI computation.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `run_pipeline`, `ingest_to_bronze`, `transform_to_silver`, `aggregate_to_gold`, `validate_record`, `QUALITY_RULES` |
| `quality_rules.py` | Validation rules per stream + generic rule checker |
| `bronze_ingestion.py` | Raw JSON → Bronze layer (append-only, no transforms) |
| `silver_transformation.py` | Bronze → Silver Parquet + quarantine bad records |
| `gold_aggregation.py` | Silver → Gold KPI Parquet via DuckDB SQL |
| `orchestrator.py` | Full pipeline runner with logging |

### `quality_rules.py` — Validation Rules

**`QUALITY_RULES`** — Dict mapping each stream to a list of rule definitions:

| Stream | Rules | Examples |
|--------|-------|---------|
| flights (5 rules) | regex, enum, range, not_null | `flight_id` matches `[A-Z0-9]{2}\d{3,4}`, `status` in 6 values, `delay_minutes >= 0` |
| passengers (4 rules) | range, not_null | `passenger_count` 0-5000, `wait_time` 0-180, `checkpoint` not null |
| cargo (4 rules) | enum, range | `item_type` in 3 values, `weight_kg` 0.1-500 |
| environmental (5 rules) | range, enum | `temperature_c` -10 to 50, `humidity` 0-100, `hvac_status` in 3 values |
| runway (6 rules) | range, enum | `wind_speed` 0-200, `friction` 0-1, `precipitation` in 4 values |
| security (4 rules) | enum, range | `alert_type` in 4 values, `severity` in 4, `response_time >= 0` |

**Functions:**
- `_check_rule(value, rule)` — Evaluates a single rule (regex, enum, range, not_null)
- `validate_record(record, stream)` → `(passed: bool, failed_rules: list[str])` — Checks all rules for a stream

### `bronze_ingestion.py` — Raw → Bronze

- `ingest_to_bronze(stream_name, events)` → file path
  - Adds `_ingested_at` timestamp to each event
  - Writes JSON to `data/bronze/{stream}/events_{timestamp}.json`
  - No transformations — preserves raw data fidelity

### `silver_transformation.py` — Bronze → Silver + Quarantine

- `_load_bronze_records(stream_name)` — Reads all JSON files from `data/bronze/{stream}/`
- `transform_to_silver(stream_name)` → `{total_records, passed, failed, quarantined, quality_score, failure_reasons}`
  - Validates each record against quality rules
  - Valid records → `data/silver/{stream}.parquet`
  - Failed records → `data/quarantine/{stream}_quarantine.parquet` (with `_quarantine_reasons` field)

### `gold_aggregation.py` — Silver → Gold KPIs (DuckDB)

- `aggregate_to_gold()` → `{flight_kpis, passenger_kpis, pipeline_kpis, quality_kpis, safety_kpis}` (row counts)

Uses DuckDB SQL-on-Parquet for analytics:

| Function | Output File | KPIs Computed |
|----------|-------------|---------------|
| `_compute_flight_kpis()` | `flight_kpis.parquet` | OTP% by hour, avg delay, total flights, gate utilization |
| `_compute_passenger_kpis()` | `passenger_kpis.parquet` | Throughput/hr per checkpoint, avg wait time |
| `_compute_pipeline_kpis()` | `pipeline_kpis.parquet` | Success rate, avg duration, records processed per stream |
| `_compute_quality_kpis()` | `quality_kpis.parquet` | Validation pass rate per stream (Silver vs Quarantine counts) |
| `_compute_safety_kpis()` | `safety_kpis.parquet` | Avg response time by severity, alert counts, resolution rates |

### `orchestrator.py` — Full Pipeline Runner

- `run_pipeline(streams)` → summary dict with timing, quality metrics, gold summary
  - Runs Silver transformation for each stream
  - Runs Gold aggregation
  - Appends pipeline log entries to `data/logs/pipeline_logs.parquet`
- `_append_pipeline_log(entry)` — Writes/appends to log Parquet

**CLI:** `python -m pipeline.orchestrator`

---

## `ai/` — Claude AI Integration

Provides grounded, context-aware AI diagnosis using the Anthropic Claude API.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `ClaudeClient`, `build_ai_context`, `format_context_for_prompt` |
| `prompts.py` | System prompt + 3 task-specific prompt templates |
| `context_builder.py` | Builds structured context from pipeline data for Claude |
| `claude_client.py` | Anthropic SDK wrapper with diagnose/recommend/chat methods |

### `prompts.py` — Prompt Templates

| Constant | Purpose |
|----------|---------|
| `SYSTEM_PROMPT` | Defines Claude as AeroOps AI — must be grounded, specific, actionable, structured. Knows medallion architecture, quality rules, lineage. |
| `DIAGNOSIS_PROMPT` | Template: "Analyze the following pipeline and system context..." |
| `RECOMMENDATION_PROMPT` | Template: "Based on the current system state, provide optimization recommendations..." |
| `CHAT_PROMPT` | Template: "Answer the user's question based on the provided context..." |

### `context_builder.py` — Grounding Context Assembly

Reads from Gold, Logs, and Quarantine Parquet files to build a structured context dict.

**Internal functions:**
- `_safe_read_parquet(path)` — Reads Parquet with graceful missing-file handling
- `_get_pipeline_health()` — Latest run results per stream from logs
- `_get_kpi_summary()` — Current KPI values vs 7 thresholds (Pipeline Success >99%, Quality >95%, OTP >80%, etc.)
- `_get_quality_issues()` — Top validation failures, quarantine spikes per stream
- `_get_anomalies()` — Detected anomalies (schema drift, outages, volume spikes)
- `_get_recent_alerts()` — Last N security alerts by severity

**Public API:**
- `build_ai_context()` → `{pipeline_health, kpi_summary, quality_issues, anomalies, lineage_impact, recent_alerts}`
- `format_context_for_prompt(context)` → Readable text block for Claude's user message

### `claude_client.py` — Anthropic SDK Wrapper

**`ClaudeClient` class:**
| Method | Purpose |
|--------|---------|
| `__init__()` | Loads API key from `.env`, initializes `anthropic.Anthropic` client |
| `_has_client()` | Returns False if no API key set |
| `_send_message(user_content, max_tokens)` | Core API call with system prompt, error handling |
| `diagnose(context)` | Builds context + DIAGNOSIS_PROMPT → sends to Claude → returns analysis |
| `recommend(context, question)` | Builds context + RECOMMENDATION_PROMPT → returns optimization advice |
| `chat(messages, context)` | Interactive chat with conversation history + grounding context |

Gracefully handles: missing API key (returns helpful message), API errors (returns error text, doesn't crash).

---

## `utils/` — Shared Utilities

Reusable helpers for theming, charting, KPI calculation, and lineage tracking.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports all public functions and constants |
| `theme.py` | Airport-themed Streamlit styling, metric cards, status indicators |
| `charts.py` | 8 reusable Plotly chart builders |
| `kpi_calculator.py` | 7 KPI reader functions (read from Gold/Silver Parquet) |
| `lineage.py` | Lineage model + forward/reverse lineage + Sankey data |

### `theme.py` — Streamlit Theme & UI Components

**Constants:**
- `COLORS` — Navy, sky blue, safety orange, success green, warning yellow, danger red, etc.
- `STATUS_COLORS` — healthy=green, warning=yellow, critical=red
- `STREAM_ICONS` — flights=✈️, passengers=👥, cargo=📦, environmental=🌡️, runway=🛬, security=🔒

**Functions:**
| Function | Returns |
|----------|---------|
| `apply_theme(st)` | Injects custom CSS into Streamlit (compact metrics, card styling) |
| `metric_card(label, value, delta, status)` | HTML string for a styled metric card with color coding |
| `status_indicator(status)` | 🟢/🟡/🔴 emoji based on status string |
| `page_header(title, icon)` | Styled page header with icon |

### `charts.py` — Plotly Chart Builders

All functions return `plotly.graph_objects.Figure` with consistent airport theme styling.

| Function | Chart Type | Used For |
|----------|-----------|----------|
| `gauge_chart(value, title, max_val, thresholds)` | Gauge/Indicator | OTP, quality scores, compliance |
| `time_series_chart(df, x_col, y_col, title)` | Line chart | OTP trends, throughput over time |
| `bar_chart(df, x_col, y_col, title, horizontal)` | Bar chart | Wait times, event counts per stream |
| `stacked_bar_chart(df, x_col, y_cols, title)` | Stacked bar | Medallion layer health, success/failure |
| `heatmap_chart(df, x_col, y_col, z_col, title)` | Heatmap | Passenger flow by terminal/zone |
| `funnel_chart(labels, values, title)` | Funnel | Baggage: checked_in → loaded → delivered |
| `sankey_chart(sources, targets, values, labels)` | Sankey diagram | Bronze → Silver → Gold data flow |
| `gantt_chart(df, start_col, end_col, label_col)` | Timeline/Gantt | Pipeline run timelines |

### `kpi_calculator.py` — KPI Reader Functions

Each reads from Gold/Silver/Logs Parquet and returns a dict. All handle missing files gracefully.

| Function | Data Source | Returns |
|----------|-----------|---------|
| `get_pipeline_health()` | `pipeline_kpis.parquet` | success_rate, avg_duration, total_records, total_runs |
| `get_data_quality_scores()` | `quality_kpis.parquet` | quality_score per stream |
| `get_flight_kpis()` | `flight_kpis.parquet` | otp_pct, avg_delay, total_flights |
| `get_passenger_kpis()` | `passenger_kpis.parquet` | avg_throughput, avg_wait_time |
| `get_safety_kpis()` | `safety_kpis.parquet` | avg_response_time, total_alerts |
| `get_environmental_compliance()` | `silver/environmental.parquet` | compliance_pct, readings_in_range |
| `get_overall_system_health()` | All of the above | Aggregate health summary |

### `lineage.py` — Data Lineage Tracking

**`LINEAGE_MODEL`** — Static dict mapping each stream to its Bronze → Silver → Gold path + affected KPIs:
```
flights     → flight_kpis.parquet     → [Flight OTP, Avg Delay, Gate Utilization]
passengers  → passenger_kpis.parquet  → [Passenger Throughput, Avg Wait Time, Checkpoint Efficiency]
cargo       → flight_kpis.parquet     → [Baggage Processing Rate, Lost Baggage Rate]
environmental → quality_kpis.parquet  → [Environmental Compliance, HVAC Health]
runway      → safety_kpis.parquet     → [Runway Utilization, Weather Safety Index]
security    → safety_kpis.parquet     → [Incident Response Time, Alert Resolution Rate]
```

**Functions:**
| Function | Purpose |
|----------|---------|
| `get_lineage_for_stream(stream)` | Full path: Bronze dir → Silver file → Gold files → KPI names |
| `get_impact_analysis(stream)` | If this stream fails, which Gold KPIs become unreliable? |
| `get_reverse_lineage(kpi_name)` | Trace a Gold KPI back through Silver to Bronze source |
| `get_sankey_data()` | Returns sources/targets/values/labels for Sankey diagram |

---

## `app/` — Streamlit Dashboard (6 Pages)

| File | Page | Description |
|------|------|-------------|
| `🏠_Command_Center.py` | **Main entry point** | System health, event counts, medallion layers, alerts |
| `pages/1_✈️_Flight_Passenger.py` | Flight & Passenger | OTP gauge, delay histogram, passenger throughput, baggage funnel |
| `pages/2_🔧_Pipeline_Health.py` | Pipeline Health | Gantt timeline, success/failure trends, duration by stage, log viewer |
| `pages/3_📈_KPI_Metrics.py` | KPI Metrics | Quality gauges per stream, quarantine breakdown, freshness, compliance |
| `pages/4_🔗_Data_Lineage.py` | Data Lineage | Sankey flow, impact analysis, quality rules table, quarantine inspector |
| `pages/5_🤖_AI_Ops_Center.py` | AI Ops Center | Claude diagnosis, incident analysis, chat interface, context panel |

### Command Center (`🏠_Command_Center.py`)

The main Streamlit entry point. Sets `page_config(layout="wide")`.

**Sidebar controls:**
- Failure scenario toggles (3 checkboxes)
- "Generate New Data" button (with failure injection)
- "Run Pipeline" button
- Auto-refresh slider (10-300s)

**Dashboard sections:**
1. **4 metric cards** — Total flights, passengers processed, pipeline success rate, data quality score
2. **6-stream health grid** — Traffic light indicators (🟢/🟡/🔴) per stream
3. **Medallion layer chart** — Stacked bar: Bronze/Silver/Gold record counts
4. **Two-column layout** — Recent security alerts (left) + events per stream bar chart (right)

### Flight & Passenger (`1_✈️_Flight_Passenger.py`)

1. Top metrics: OTP%, total flights, avg delay, passenger throughput
2. OTP trend line with 80% threshold
3. Delay distribution histogram + flight status pie chart
4. Checkpoint wait times bar chart + throughput vs capacity line
5. Baggage processing funnel (checked_in → in_transit → loaded → delivered)

### Pipeline Health (`2_🔧_Pipeline_Health.py`)

1. Top metrics: success rate, total runs, avg duration, records processed
2. Gantt-style pipeline run timeline (colored by status)
3. Success/failure trend + duration by stage per stream
4. Multi-line throughput chart
5. Filterable log viewer (stream, status, stage dropdowns)

### KPI Metrics (`3_📈_KPI_Metrics.py`)

1. Quality gauges per stream (green/yellow/red)
2. Schema validation rate bar chart
3. Quarantine records trend + failure reasons breakdown
4. Gold table freshness with traffic lights
5. Environmental compliance gauge
6. KPI summary table with ✅/⚠️/❌ status

### Data Lineage (`4_🔗_Data_Lineage.py`)

1. Sankey diagram: Bronze → Silver → Gold flow
2. Impact analysis (select stream → see affected KPIs)
3. Quality rules catalogue with pass/fail status
4. Quarantine inspector (browse rejected records)
5. Reverse lineage (select KPI → trace to Bronze)
6. Data classification tags (Operational, PII, Security, Regulatory)

### AI Ops Center (`5_🤖_AI_Ops_Center.py`)

1. Status banner (green/yellow/red based on system state)
2. "Generate System Diagnosis" button → Claude analysis
3. Incident analysis expanders: What Changed / Broke / Impacted / Recommended
4. Chat interface with starter questions + conversation history
5. Grounding context panel (shows exactly what data Claude received)

---

## `data/` — Runtime Data (gitignored)

Generated at runtime by simulator and pipeline. All gitignored.

```
data/
├── bronze/              # Raw JSON events per stream
│   ├── flights/         # flights_events.json
│   ├── passengers/      # passengers_events.json
│   ├── cargo/           # cargo_events.json
│   ├── environmental/   # environmental_events.json
│   ├── runway/          # runway_events.json
│   └── security/        # security_events.json
├── silver/              # Validated Parquet per stream
│   ├── flights.parquet
│   ├── passengers.parquet
│   ├── cargo.parquet
│   ├── environmental.parquet
│   ├── runway.parquet
│   └── security.parquet
├── gold/                # Aggregated KPI Parquet
│   ├── flight_kpis.parquet
│   ├── passenger_kpis.parquet
│   ├── pipeline_kpis.parquet
│   ├── quality_kpis.parquet
│   └── safety_kpis.parquet
├── quarantine/          # Failed validation records
│   └── {stream}_quarantine.parquet
└── logs/                # Pipeline execution logs
    └── pipeline_logs.parquet
```

---

## `docs/` — Documentation

| File | Content |
|------|---------|
| `architecture.md` | ~920 lines: full architecture, schemas, KPIs, component specs, Q&A prep |
| `demo_script.md` | Step-by-step demo walkthrough: Detect → Diagnose → Assess → Recommend |

## `resources/`

| File | Content |
|------|---------|
| `NOTES_AND_NEXT_STEPS.md` | Original interview prep notes and ideas |
