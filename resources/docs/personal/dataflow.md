# AeroOps Data Flow

> How data moves through the system from generation to dashboard visualization

## High-Level Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Simulator  │────▶│   Bronze    │────▶│   Silver    │────▶│    Gold     │────▶│  Dashboard  │
│  (Generate) │     │  (Raw JSON) │     │ (Validated) │     │   (KPIs)   │     │  (Display)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │ Quarantine  │
                                        │  (Invalid)  │
                                        └─────────────┘
```

## Data Streams (6 IoT Sources)

| Stream | Events/Min (base) | Peak Multiplier | Key Fields |
|--------|-------------------|-----------------|------------|
| flights | 2 | 2.5× | flight_id, delay_minutes, status, gate, scheduled_time |
| passengers | 10 | 3.0× | checkpoint, wait_time_minutes, throughput_per_hour, passenger_count |
| cargo | 5 | 2.0× | item_type, status, weight_kg, processing_time_sec |
| environmental | 8 | 1.5× | temperature_c, humidity_pct, co2_ppm, air_quality_index, hvac_status |
| runway | 3 | 1.0× | wind_speed_kph, visibility_m, friction_index, precipitation, runway_status |
| security | 6 | 2.0× | alert_type, severity, response_time_sec, resolution_status |

## Layer-by-Layer Flow

### Layer 1: Generation → Bronze

```
simulator/data_generator.py
    │
    ├── generate_flight_events()      ──┐
    ├── generate_passenger_events()   ──┤
    ├── generate_cargo_events()       ──┤
    ├── generate_environmental_events()─┤
    ├── generate_runway_events()      ──┤
    └── generate_security_events()    ──┘
                                        │
                                        ▼
                            pipeline/bronze_ingestion.py
                                        │
                                        ▼
                    data/bronze/{stream}/events_{timestamp}.json
```

**Transformation:** Add `_ingested_at` timestamp. No other modifications.

**Volume (24hr simulation):**
| Stream | ~Records |
|--------|----------|
| flights | ~3,600 |
| passengers | ~18,000 |
| cargo | ~9,000 |
| environmental | ~14,400 |
| runway | ~4,320 |
| security | ~10,800 |

### Layer 2: Bronze → Silver (+ Quarantine)

```
data/bronze/{stream}/*.json
        │
        ▼
pipeline/silver_transformation.py
        │
        ├── validate_record(record, stream)  ◀── pipeline/quality_rules.py
        │       │
        │       ├── PASS ──▶ data/silver/{stream}.parquet
        │       │
        │       └── FAIL ──▶ data/quarantine/{stream}_quarantine.parquet
        │                       (includes _quarantine_reasons)
        │
        ▼
Returns: {total_records, passed, failed, quality_score, failure_reasons}
```

**Transformation:**
- Field validation (28 rules across 6 streams)
- Type coercion for range checks (`float(value)`)
- Quarantine tagging (`_quarantine_reasons: ["rule_name", ...]`)

### Layer 3: Silver → Gold

```
data/silver/flights.parquet        ──┐
data/silver/passengers.parquet     ──┤
data/silver/cargo.parquet          ──┤    DuckDB
data/silver/environmental.parquet  ──┤    In-Memory
data/silver/runway.parquet         ──┤    SQL Engine
data/silver/security.parquet       ──┤       │
data/logs/pipeline_logs.parquet    ──┤       │
data/quarantine/*.parquet          ──┘       │
                                             ▼
                            ┌────────────────────────────────┐
                            │  data/gold/flight_kpis.parquet  │
                            │  data/gold/passenger_kpis.parquet│
                            │  data/gold/pipeline_kpis.parquet │
                            │  data/gold/quality_kpis.parquet  │
                            │  data/gold/safety_kpis.parquet   │
                            └────────────────────────────────┘
```

**Transformation (SQL aggregations):**
| Gold Table | SQL Pattern | Grouping |
|------------|-------------|----------|
| flight_kpis | COUNT, AVG, FILTER | Hourly |
| passenger_kpis | AVG, SUM, MAX | Per-checkpoint |
| pipeline_kpis | COUNT, AVG, SUM/NULLIF | Per-stream |
| quality_kpis | Silver count + Quarantine count | Per-stream |
| safety_kpis | COUNT, AVG, FILTER | Per-severity |

### Layer 4: Gold → Dashboard

```
data/gold/flight_kpis.parquet      ──▶ Command Center, Passenger Analytics
data/gold/passenger_kpis.parquet   ──▶ Command Center, Passenger Analytics
data/gold/quality_kpis.parquet     ──▶ Command Center, KPI Metrics
data/gold/safety_kpis.parquet      ──▶ KPI Metrics
data/gold/pipeline_kpis.parquet    ──▶ Pipeline Health
data/logs/pipeline_logs.parquet    ──▶ Pipeline Health, AI Ops Center
data/logs/ai_metrics.json          ──▶ AI Performance Monitor
data/quarantine/*.parquet          ──▶ KPI Metrics, Data Lineage
```

### Layer 5: Gold → AI Context → LLM → Response

```
data/gold/*.parquet          ──┐
data/logs/pipeline_logs.parquet──┤    ai/context_builder.py
data/logs/alerts.parquet     ──┤         │
data/quarantine/*.parquet    ──┘         ▼
                                  build_ai_context()
                                         │
                                         ▼
                                  format_context_for_prompt()
                                         │
                                         ▼
                              ai/claude_client.py ──▶ Claude API / Ollama
                                         │
                                         ├──▶ Response to user (chat/diagnose/recommend)
                                         │
                                         └──▶ data/logs/ai_metrics.json (append metrics)
```

## Failure Scenario Data Flows

### Scenario 1: Schema Drift (Runway)

```
data_generator → runway events (normal)
         │
         ▼
failure_injector.inject_schema_drift()
         │  wind_speed_kph × 4.0
         ▼
bronze_ingestion → data/bronze/runway/events_*.json (corrupted values)
         │
         ▼
silver_transformation → validate_record()
         │  FAIL: wind_speed_range (value > 200)
         ▼
data/quarantine/runway_quarantine.parquet (320+ records)
         │
         ▼
gold_aggregation → quality_kpis.parquet (runway validation_rate drops to ~70%)
         │
         ▼
Dashboard: KPI Metrics shows red runway quality gauge
AI Ops Center: "Runway stream has schema drift on wind_speed_kph"
```

### Scenario 2: Sensor Outage (Passengers)

```
data_generator → passenger events (normal)
         │
         ▼
failure_injector.inject_sensor_outage(checkpoints=3)
         │  checkpoint=null, wait_time=-1 for 3 checkpoints
         ▼
silver_transformation → validate_record()
         │  FAIL: checkpoint_not_null, wait_time_range
         ▼
data/quarantine/passengers_quarantine.parquet
         │
         ▼
gold_aggregation → passenger_kpis (fewer checkpoints), quality_kpis (lower rate)
         │
         ▼
Passenger Analytics: gaps in checkpoint throughput chart
KPI Metrics: passenger quality gauge drops
```

### Scenario 3: Traffic Spike (All Streams)

```
data_generator(rate_multiplier=3.0) → 3× normal event volume
         │
         ▼
bronze_ingestion → 3× larger JSON files
         │
         ▼
silver_transformation → All records pass (valid data, just more of it)
         │
         ▼
gold_aggregation → Higher counts, same averages
         │
         ▼
Pipeline Health: duration increases (processing more records)
Command Center: higher throughput numbers
```

## Data Freshness

| Layer | Refresh Trigger | Staleness |
|-------|----------------|-----------|
| Bronze | "Generate Data" button | Fresh per generation |
| Silver | "Run Pipeline" button | Fresh per pipeline run |
| Gold | "Run Pipeline" button | Recomputed every run |
| AI Metrics | Every LLM call | Real-time append |
| Dashboard | Page load / rerun | Reads current files |

## File Size Estimates (24hr simulation)

| Path | Approx Size | Records |
|------|-------------|---------|
| data/bronze/ (all streams) | ~15 MB | ~60,000 events |
| data/silver/ (all streams) | ~8 MB | ~58,000 records |
| data/quarantine/ | ~500 KB | ~2,000 records |
| data/gold/ (all tables) | ~50 KB | ~50 aggregated rows |
| data/logs/pipeline_logs.parquet | ~20 KB | ~7 entries/run |
| data/logs/ai_metrics.json | ~5 KB | ~20 entries |

## Interview Pitch

"The data flow follows the medallion architecture — Bronze stores immutable raw JSON preserving schema flexibility, Silver applies 28 validation rules across 6 IoT streams with quarantine for failed records, and Gold uses DuckDB SQL to compute pre-aggregated KPIs. Each layer adds value: Bronze enables reprocessing, Silver ensures trust, Gold enables sub-second dashboard loads. The AI layer adds a fifth dimension — reading Gold KPIs as RAG context to generate grounded operational insights."

## Interview Q&A

1. **Q: Why three layers instead of just raw → aggregated?**
   A: Silver (validation) is critical for data trust. Without it, corrupt sensor data flows directly into KPIs — a wind speed sensor glitch would report impossible OTP numbers. The three-layer pattern also enables independent evolution: change validation rules without changing aggregation, or add new Gold tables without touching ingestion.

2. **Q: How does data flow when the pipeline runs?**
   A: Sequential per stream: Read ALL Bronze JSON → Validate each record → Write Silver + Quarantine → After all streams, DuckDB reads all Silver → Computes 5 Gold tables → Logs execution. Dashboard reads Gold on next page load. Total time: ~5-10 seconds for 60K records.

3. **Q: What's the difference between pipeline_logs and ai_metrics?**
   A: `pipeline_logs.parquet` tracks ETL execution (was the data pipeline successful?). `ai_metrics.json` tracks LLM usage (how much did AI calls cost?). Different concerns, different consumers, different write patterns (parquet append vs JSON append).

4. **Q: How would you scale this to real-time?**
   A: Replace batch Bronze (JSON files) with Kafka topics. Replace batch Silver transform with Flink/Spark Structured Streaming for continuous validation. Gold becomes materialized views refreshing on a schedule. The dashboard switches from file reads to database queries. The architecture pattern stays identical — only the execution engine changes.

5. **Q: Why does Gold recompute everything instead of incremental updates?**
   A: For POC simplicity and correctness — no stale aggregates possible. With 60K records, full recompute takes <5 seconds. In production at scale, you'd track high-water marks and process only deltas, with periodic full rebuilds for drift correction.
