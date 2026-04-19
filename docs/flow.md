# AeroOps AI — End-to-End Project Flow

> How data moves from simulated IoT sensors through a medallion pipeline to an AI-powered dashboard.

---

## High-Level Flow

```
  GENERATE          INGEST          VALIDATE         AGGREGATE         VISUALIZE         DIAGNOSE
┌──────────┐    ┌──────────┐    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Simulator │───▶│  BRONZE  │───▶│  SILVER  │────▶│   GOLD   │────▶│ Streamlit│────▶│ Claude   │
│ 6 streams │    │ Raw JSON │    │ Parquet  │     │ KPI      │     │ 6 pages  │     │ AI       │
│ 66K events│    │ no xform │    │ validated│     │ Parquet  │     │ charts   │     │ grounded │
└──────────┘    └──────────┘    └────┬─────┘     └──────────┘     └──────────┘     └──────────┘
                                     │
                                     ▼
                                ┌──────────┐
                                │QUARANTINE│
                                │bad records│
                                └──────────┘
```

---

## Step-by-Step Flow

### Step 1: Data Generation (`simulator/`)

**What happens:** The simulator creates 24 hours of realistic airport IoT data across 6 sensor streams.

**Command:** `python -m simulator.airport_generator`

```
simulator/config.py          ──▶  Airport constants (terminals, gates, airlines, peak hours)
                                      │
simulator/airport_generator.py  ◀─────┘
     │
     ├── For each minute in 24h:
     │     ├── Check if peak hour (7-9, 11-13, 17-19) → 2-3x event rate
     │     └── For each of 6 streams:
     │           └── Generate N events using stream-specific generator
     │
     ├── generate_flight_events()      ──▶  ~3,770 events  (delays: exponential dist, 70% on-time)
     ├── generate_passenger_events()   ──▶ ~19,569 events  (wait times correlate with peaks)
     ├── generate_cargo_events()       ──▶  ~9,692 events  (70% baggage, 20% cargo, 10% mail)
     ├── generate_environmental_events()──▶ ~15,618 events  (diurnal temp curve, 95% HVAC normal)
     ├── generate_runway_events()      ──▶  ~5,737 events  (weather-correlated, friction 0.5-0.9)
     └── generate_security_events()    ──▶ ~11,662 events  (95% routine, 5% anomaly/breach)
                                              │
                                              ▼
                                   data/bronze/{stream}/{stream}_events.json
                                   (66,048 total events as raw JSON)
```

**Optional — Pipeline Logs:** `python -m simulator.pipeline_log_generator`
```
Generates 432 simulated ETL log entries (24 runs × 6 streams × 3 stages)
  ──▶  data/logs/pipeline_logs.parquet
```

**Optional — Failure Injection:** (via dashboard sidebar toggles)
```
inject_schema_drift()    ──▶  Multiplies runway wind_speed by 1.6 (mph reported as kph)
inject_sensor_outage()   ──▶  Removes events from 3 passenger checkpoints
inject_traffic_spike()   ──▶  Returns 3x rate_multiplier for generate_all_events()
```

---

### Step 2: Bronze Ingestion (`pipeline/bronze_ingestion.py`)

**What happens:** Raw events are written to the Bronze layer with zero transformations. Only an `_ingested_at` metadata timestamp is added.

```
data/bronze/{stream}/{stream}_events.json
     │
     ▼
ingest_to_bronze(stream_name, events)
     │
     ├── Add _ingested_at timestamp to each event
     ├── Write JSON to data/bronze/{stream}/events_{timestamp}.json
     └── No schema enforcement, no validation, no transformation
         (preserves raw data fidelity — this IS the point of Bronze)
```

**Design principle:** Bronze is your insurance policy. If Silver rules are wrong, you can always reprocess from Bronze.

---

### Step 3: Silver Transformation (`pipeline/silver_transformation.py`)

**What happens:** Each Bronze record is validated against stream-specific quality rules. Valid records go to Silver Parquet; failed records are quarantined with reasons.

```
data/bronze/{stream}/*.json
     │
     ▼
transform_to_silver(stream_name)
     │
     ├── Load all JSON files from data/bronze/{stream}/
     │
     ├── For EACH record:
     │     │
     │     ▼
     │   validate_record(record, stream)    ◀── quality_rules.py
     │     │
     │     ├── Check each rule for this stream:
     │     │     ├── regex:    field matches pattern (e.g., flight_id ~ [A-Z0-9]{2}\d{3,4})
     │     │     ├── enum:     field in allowed values (e.g., status in [scheduled, boarding, ...])
     │     │     ├── range:    min <= field <= max (e.g., temperature -10 to 50)
     │     │     └── not_null: field is present and non-null
     │     │
     │     ├── PASSED ──▶ Add to valid_records list
     │     └── FAILED ──▶ Add to quarantine list (with _quarantine_reasons field)
     │
     ├── Write valid records ──▶ data/silver/{stream}.parquet
     └── Write failed records ──▶ data/quarantine/{stream}_quarantine.parquet
```

**Quality rules per stream:**
```
flights:       5 rules (flight_id format, status enum, delay >= 0, pax 1-600, scheduled not null)
passengers:    4 rules (pax 0-5000, wait 0-180 min, throughput >= 0, checkpoint not null)
cargo:         4 rules (item_type enum, status enum, weight 0.1-500 kg, processing_time >= 0)
environmental: 5 rules (temp -10 to 50, humidity 0-100, CO2 200-5000, AQI 0-500, hvac enum)
runway:        6 rules (wind 0-200, visibility 0-20000, friction 0-1, direction 0-360, precip enum, status enum)
security:      4 rules (alert_type enum, severity enum, resolution enum, response_time >= 0)
```

**Output:**
```
Returns: {
  total_records: 3770,
  passed: 3770,
  failed: 0,
  quarantined: 0,
  quality_score: 1.0,        # passed / total
  failure_reasons: {}         # {rule_name: count} when failures occur
}
```

---

### Step 4: Gold Aggregation (`pipeline/gold_aggregation.py`)

**What happens:** DuckDB runs SQL analytics on Silver Parquet files to compute business KPIs. Results are written as Gold Parquet files.

```
data/silver/*.parquet
     │
     ▼
aggregate_to_gold()
     │
     ├── Open DuckDB in-memory connection
     │
     ├── _compute_flight_kpis()
     │     SQL: SELECT DATE_TRUNC('hour', timestamp), COUNT(*), OTP%, avg delay
     │     FROM read_parquet('data/silver/flights.parquet')
     │     ──▶ data/gold/flight_kpis.parquet (25 rows — hourly KPIs)
     │
     ├── _compute_passenger_kpis()
     │     SQL: SELECT checkpoint, AVG(throughput), AVG(wait_time)
     │     FROM read_parquet('data/silver/passengers.parquet')
     │     ──▶ data/gold/passenger_kpis.parquet (10 rows — per checkpoint)
     │
     ├── _compute_pipeline_kpis()
     │     SQL: SELECT stream, success_rate, avg_duration, total_records
     │     FROM read_parquet('data/logs/pipeline_logs.parquet')
     │     ──▶ data/gold/pipeline_kpis.parquet (6 rows — per stream)
     │
     ├── _compute_quality_kpis()
     │     Reads Silver record counts + Quarantine record counts per stream
     │     Computes: quality_score = silver_count / (silver_count + quarantine_count)
     │     ──▶ data/gold/quality_kpis.parquet (6 rows — per stream)
     │
     └── _compute_safety_kpis()
           SQL: SELECT severity, AVG(response_time), COUNT(*), resolution rates
           FROM read_parquet('data/silver/security.parquet')
           ──▶ data/gold/safety_kpis.parquet (4 rows — per severity)
```

---

### Step 5: Pipeline Orchestrator (`pipeline/orchestrator.py`)

**What happens:** Runs the full pipeline end-to-end and logs execution metrics.

**Command:** `python -m pipeline.orchestrator`

```
run_pipeline(streams=["flights","passengers","cargo","environmental","runway","security"])
     │
     ├── For each stream:
     │     ├── Start timer
     │     ├── transform_to_silver(stream)
     │     ├── Stop timer
     │     └── Log: {run_id, timestamp, stage, stream, status, records, duration}
     │
     ├── aggregate_to_gold()
     │     └── Log gold aggregation metrics
     │
     └── Append all log entries ──▶ data/logs/pipeline_logs.parquet
```

**Output:**
```json
{
  "run_timestamp": "2026-04-19T19:18:32Z",
  "total_duration_sec": 1.139,
  "streams_processed": 6,
  "silver_results": { "flights": {quality_score: 1.0, ...}, ... },
  "gold_summary": { "flight_kpis": 25, "passenger_kpis": 10, ... }
}
```

---

### Step 6: Dashboard Visualization (`app/`)

**What happens:** Streamlit reads Gold/Silver/Quarantine/Logs Parquet files and renders 6 interactive pages.

**Command:** `streamlit run app/🏠_Command_Center.py`

```
                    ┌────────────────────────────────────┐
                    │         Streamlit Dashboard          │
                    │        http://localhost:8501         │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
 data/gold/*.parquet│  │  🏠 Command Center          │    │
 ─────────────────▶ │  │  System health overview      │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
 data/silver/       │  ┌─────────────────────────────┐    │
 *.parquet ────────▶│  │  ✈️ Flight & Passenger       │    │
                    │  │  OTP, throughput, delays      │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
 data/logs/         │  ┌─────────────────────────────┐    │
 pipeline_logs ────▶│  │  🔧 Pipeline Health          │    │
 .parquet           │  │  ETL runs, durations, errors  │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
 data/quarantine/   │  ┌─────────────────────────────┐    │
 *.parquet ────────▶│  │  📈 KPI Metrics              │    │
                    │  │  Quality, SLA, compliance     │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
 LINEAGE_MODEL      │  ┌─────────────────────────────┐    │
 (static dict) ────▶│  │  🔗 Data Lineage             │    │
                    │  │  Sankey, impact, governance    │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │  🤖 AI Ops Center            │────▶ Step 7
                    │  │  Claude diagnosis & chat      │    │
                    │  └─────────────────────────────┘    │
                    └────────────────────────────────────┘
```

**Sidebar controls:**
```
Failure Scenario Toggles:
  ☐ Runway Schema Drift      ──▶ inject_schema_drift() on next data gen
  ☐ Passenger Sensor Outage  ──▶ inject_sensor_outage() on next data gen
  ☐ Holiday Traffic Spike    ──▶ inject_traffic_spike() on next data gen

Pipeline Controls:
  [Generate New Data]  ──▶ Runs simulator with any active failure toggles
  [Run Pipeline]       ──▶ Runs Bronze→Silver→Gold pipeline

Auto Refresh: slider 10-300 seconds
```

---

### Step 7: AI Diagnosis (`ai/`)

**What happens:** Claude AI analyzes the current system state and provides grounded diagnosis and recommendations.

```
User clicks "Generate System Diagnosis"
     │
     ▼
build_ai_context()                           ◀── context_builder.py
     │
     ├── Read data/gold/*.parquet            ──▶ KPI values vs thresholds
     ├── Read data/logs/pipeline_logs.parquet ──▶ Pipeline success/failure
     ├── Read data/quarantine/*.parquet      ──▶ Validation failures
     │
     ▼
context = {
  pipeline_health:  {stream: {status, duration, records}, ...}
  kpi_summary:      {otp: {value: 82%, threshold: 80%, status: healthy}, ...}
  quality_issues:   {stream: {quarantine_count, top_failures}, ...}
  anomalies:        [{type: "schema_drift", stream: "runway", detail: ...}]
  lineage_impact:   {runway: ["Runway Utilization", "Weather Safety Index"]}
  recent_alerts:    [{severity: "high", type: "breach", checkpoint: "SEC-T1-A"}]
}
     │
     ▼
format_context_for_prompt(context)           ◀── Converts dict to readable text
     │
     ▼
ClaudeClient.diagnose(context)               ◀── claude_client.py
     │
     ├── System prompt: SYSTEM_PROMPT        ◀── Defines Claude as AeroOps AI
     │     (grounded, specific, actionable, structured)
     │
     ├── User prompt: DIAGNOSIS_PROMPT + formatted context
     │
     ├── API call: anthropic.Anthropic().messages.create(
     │     model="claude-sonnet-4-20250514",
     │     system=SYSTEM_PROMPT,
     │     messages=[{role: "user", content: prompt}]
     │   )
     │
     └── Returns structured analysis:
           - What changed: [specific metric shift]
           - What broke: [pipeline stage, validation rule]
           - What's impacted: [downstream Gold KPIs]
           - Recommended action: [remediation steps]
```

**Chat flow:**
```
User types question in chat interface
     │
     ▼
ClaudeClient.chat(messages=conversation_history, context=current_context)
     │
     ├── Appends grounding context to conversation
     ├── Sends full history to Claude for multi-turn awareness
     └── Returns response (displayed in st.chat_message)
```

---

## Failure Scenario Flow (Example: Schema Drift)

This demonstrates the **Detect → Diagnose → Assess → Recommend** narrative.

```
1. USER: Enables "Runway Schema Drift" toggle → clicks "Generate New Data"

2. SIMULATOR: generate_all_events() produces normal data
   inject_schema_drift(events) ──▶ Multiplies wind_speed_kph × 1.6
   write_events_to_json() ──▶ data/bronze/runway/runway_events.json
                                   (values like 120, 140, 160 kph — some over 200)

3. USER: Clicks "Run Pipeline"

4. SILVER: transform_to_silver("runway")
   validate_record() checks wind_speed_range rule (0-200)
   Values > 200 ──▶ QUARANTINED with reason "wind_speed_range"
   Result: quality_score drops from 1.0 to ~0.85

5. GOLD: aggregate_to_gold()
   _compute_quality_kpis() ──▶ runway quality score = 85%
   _compute_safety_kpis() ──▶ Fewer runway records → degraded KPIs

6. DASHBOARD REACTS:
   🏠 Command Center  ──▶ Runway stream: 🟡 yellow (was 🟢 green)
   📈 KPI Metrics      ──▶ Runway quality gauge drops to 85%
   🔗 Data Lineage     ──▶ Quarantine inspector shows wind_speed failures
   🔧 Pipeline Health  ──▶ Runway quarantine count spike in logs

7. AI DIAGNOSIS:
   build_ai_context() detects:
     - anomaly: runway quarantine spike
     - quality_issues: wind_speed_range failures
     - lineage_impact: Runway Utilization + Weather Safety KPIs affected

   Claude responds:
     "Runway sensor RWY-09L values anomalous since 14:32 UTC.
      Wind speed readings inconsistent — values suggest mph not kph.
      Recommend firmware version check and unit conversion rule.
      Affected KPIs: Runway Utilization, Weather Safety Index."
```

---

## Complete Execution Sequence

```bash
# 1. Setup
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env              # Add ANTHROPIC_API_KEY

# 2. Generate data (creates Bronze layer)
python -m simulator.airport_generator        # 66K events → data/bronze/
python -m simulator.pipeline_log_generator   # 432 log entries → data/logs/

# 3. Run pipeline (creates Silver + Gold layers)
python -m pipeline.orchestrator              # Bronze→Silver→Gold in ~1 second

# 4. Launch dashboard
streamlit run app/🏠_Command_Center.py       # Opens at http://localhost:8501

# 5. Explore
#    - View all 6 pages
#    - Toggle failure scenarios in sidebar
#    - Click "Generate New Data" then "Run Pipeline"
#    - Watch KPIs react to injected failures
#    - Ask Claude AI for diagnosis
```

---

## Data Dependencies

```
simulator/config.py
     │
     ▼
simulator/airport_generator.py ──▶ data/bronze/{stream}/*.json
simulator/pipeline_log_generator.py ──▶ data/logs/pipeline_logs.parquet
     │
     ▼
pipeline/quality_rules.py ──▶ (used by silver_transformation)
pipeline/bronze_ingestion.py ──▶ data/bronze/ (writes)
pipeline/silver_transformation.py ──▶ data/silver/*.parquet + data/quarantine/*.parquet
pipeline/gold_aggregation.py ──▶ data/gold/*.parquet
pipeline/orchestrator.py ──▶ data/logs/pipeline_logs.parquet (appends)
     │
     ▼
utils/kpi_calculator.py ◀── data/gold/*.parquet
utils/lineage.py ◀── LINEAGE_MODEL (static) + data/ counts
utils/charts.py ◀── DataFrames from kpi_calculator
utils/theme.py ◀── (standalone)
     │
     ▼
app/*.py ◀── utils/* + data/gold/*.parquet + data/silver/*.parquet + data/logs/*.parquet
     │
     ▼
ai/context_builder.py ◀── data/gold/*.parquet + data/logs/*.parquet + data/quarantine/*.parquet
ai/claude_client.py ◀── context_builder + prompts.py + Anthropic API
```
