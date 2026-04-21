# Simulator Module

> Folder: `simulator/`

## Overview

Generates realistic airport IoT telemetry for 6 data streams, simulating a 24-hour operational cycle with diurnal patterns, peak-hour traffic, and injectable failure scenarios. This module provides the synthetic data that drives the entire pipeline and dashboard demonstration.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | Airport constants, enum lookups, stream configuration |
| `airport_generator.py` | Main event generator for all 6 IoT streams |
| `failure_injector.py` | Injectable failure scenarios for testing quality pipelines |
| `pipeline_log_generator.py` | Simulates historical pipeline execution logs |
| `__init__.py` | Package marker |

---

## config.py

### Purpose
Single source of truth for all airport simulation constants. Every generator function references this config for consistent values across the system.

### Key Constants

| Constant | Content | Used By |
|----------|---------|---------|
| `AIRPORT_CONFIG` | Airport name, code, terminals, gates, runways, airlines, peak hours, events/min | All generators |
| `STREAM_NAMES` | `["flights", "passengers", "cargo", "environmental", "runway", "security"]` | Orchestrator, generators |
| `GATES` | 60 gate IDs: `Gate-110` through `Gate-320` (3 terminals × 20 gates) | Flight generator |
| `ZONES` | 12 zone IDs: `Departures-North`, `Arrivals-South`, etc. | Passenger, environmental, security |
| `CHECKPOINTS` | `Security-A` through `Security-J` (10 checkpoints) | Passenger generator |
| `AIRCRAFT_CAPACITY` | B737→189, A320→180, B777→396, A350→325, E175→76, B787→296 | Flight generator (passenger count) |
| `FLIGHT_STATUSES` | scheduled, boarding, departed, arrived, delayed, cancelled | Flight generator, quality rules |
| `CARGO_STATUSES` | checked_in, in_transit, loaded, delivered, lost | Cargo generator, quality rules |
| `ALERT_TYPES` | routine_scan, anomaly, breach, device_alert | Security generator |
| `SEVERITY_LEVELS` | low, medium, high, critical | Security generator |
| `HVAC_STATUSES` | normal, degraded, offline | Environmental generator |

### Design Pattern
Declarative config (dict/list) rather than scattered magic values. Adding a new terminal or airline is one config edit — all generators pick it up automatically.

---

## airport_generator.py

### Purpose
Main IoT event simulator — generates time-series events across 6 streams with realistic distributions, peak-hour patterns, and correlated values (e.g., HVAC degradation → temperature drift).

### Key Functions

#### `generate_all_events(base_date=None, hours=24, rate_multiplier=1.0) → dict`
Main orchestrator — iterates minute-by-minute, calls per-stream generators.

**Parameters:**
- `base_date` — Simulation start (default: today 00:00)
- `hours` — Duration to simulate (default: 24)
- `rate_multiplier` — Global volume multiplier (used by traffic spike scenario)

**Returns:** `{stream_name: [event_dicts]}`

#### `write_events_to_json(all_events, output_dir=None) → dict`
Writes each stream to `data/bronze/{stream}/{stream}_events.json`.

### Stream Generators

| Function | Events/Min (base) | Key Characteristics |
|----------|-------------------|---------------------|
| `generate_flight_events()` | 2 | 70% on-time, exponential delay distribution (mean 25min), 3% cancellation, aircraft-specific passenger capacity |
| `generate_passenger_events()` | 10 | Random checkpoint assignment, wait times 1-45min, throughput 60-350/hr |
| `generate_cargo_events()` | 5 | Weighted status distribution (20% checked_in, 30% in_transit, 25% loaded, 20% delivered, 5% lost) |
| `generate_environmental_events()` | 8 | Cosine diurnal temperature curve, HVAC correlation (degraded → +1-3°C, offline → +3-7°C, CO2 spike) |
| `generate_runway_events()` | 3 | Conditional status (visibility <6000m OR wind >65kph → weather_hold), friction 0.5-0.9 |
| `generate_security_events()` | 6 | 95% routine (no response time), 3% anomaly (10-120s response), 0.5% breach (critical, 5-30s), 1.5% device alert |

### Peak Hour Logic
```python
peak_hours = [(7, 9), (11, 13), (17, 19)]  # Morning, midday, evening

_peak_multiplier(hour):
    if hour in peak_window: return random.uniform(2.0, 3.0)
    else: return 1.0
```

### Realistic Data Patterns

| Pattern | Implementation | Real-World Analog |
|---------|---------------|-------------------|
| Diurnal temperature | `base + amplitude × sin(π(hour-6)/12)` | Indoor HVAC follows outdoor cycle |
| Exponential delays | `random.expovariate(1/25)` capped at 300 | Most flights on-time, few with long delays |
| HVAC correlation | degraded → temp+3°C, CO2+200 | HVAC failure causes environmental drift |
| Weather-hold logic | visibility <6000m OR wind >65kph | Real airport hold criteria |
| Peak multiplier | 2-3× during rush hours | Morning/evening travel patterns |

### Libraries Used
- **Faker** (`fake = Faker()`) — Not heavily used; available for future passenger name generation
- **random** — Distributions: `uniform`, `gauss`, `expovariate`, `choices` (weighted), `randint`
- **math** — `sin()` for diurnal temperature curve

### Reproducibility
```python
Faker.seed(42)
random.seed(42)
```
Same seed → same events every run. Enables deterministic testing.

---

## failure_injector.py

### Purpose
Injects controlled failure scenarios into generated data to test and demonstrate the pipeline's quality detection, quarantine, and AI diagnosis capabilities.

### Failure Scenarios

#### 1. `inject_schema_drift(events, stream="runway") → dict`

**Mechanism:** Multiplies `wind_speed_kph` by 4.0

**Effect chain:**
```
wind_speed 0-80 kph → 0-320 kph (exceeds max 200 validation)
    → quality_rules catches range_violation
    → silver_transformation quarantines records
    → quality_kpis shows runway at ~70%
    → AI diagnoses "schema drift on wind_speed_kph"
```

**Real-world analog:** Sensor firmware update changes unit from m/s to kph without parser update.

#### 2. `inject_sensor_outage(events, stream="passengers", checkpoints=3) → dict`

**Mechanism:** Picks 3 random checkpoints, sets `checkpoint=None` and `wait_time_minutes=-1`

**Effect chain:**
```
null checkpoint + negative wait time
    → quality_rules catches not_null + range violations
    → quarantine captures affected records
    → passenger throughput chart shows gaps
    → AI diagnoses "sensor outage at checkpoints [X, Y, Z]"
```

**Real-world analog:** Security checkpoint scanners go offline.

#### 3. `inject_traffic_spike(multiplier=3.0) → float`

**Mechanism:** Returns multiplier value (doesn't modify events directly)

**Usage:** `generate_all_events(rate_multiplier=inject_traffic_spike())`

**Effect chain:**
```
3× event volume (all valid data)
    → No quality failures
    → Pipeline duration increases
    → Throughput charts show volume spike
    → Tests scalability, not quality
```

**Real-world analog:** Holiday travel rush.

### Design Pattern
- Schema drift and sensor outage **mutate events in-place** (modify the dict)
- Traffic spike **returns a config value** (multiplier for generation)
- All three print status messages for CLI visibility

---

## pipeline_log_generator.py

### Purpose
Creates synthetic historical pipeline execution logs (independent of actual pipeline runs). Used to pre-populate `data/logs/pipeline_logs.parquet` with 24 hours of realistic execution history for the Pipeline Health dashboard to display on first load.

### Key Functions

#### `generate_pipeline_logs(base_date=None, runs=24) → list[dict]`

**Simulates:** 24 pipeline runs (one per hour), each processing 6 streams through 3 stages.

**Per-stage failure probabilities (increase with stage):**
| Stage | Fail Prob | Partial Prob |
|-------|-----------|--------------|
| bronze_ingestion | 2% | 5% |
| silver_transformation | 4% | 10% |
| gold_aggregation | 6% | 15% |

**Log entry schema:**
```python
{
    "run_id": "uuid",
    "timestamp": "ISO 8601",
    "stage": "bronze_ingestion | silver_transformation | gold_aggregation",
    "stream": "flights | passengers | ...",
    "status": "success | partial | failed",
    "records_in": int,
    "records_out": int,
    "records_quarantined": int,
    "duration_sec": float,
    "error_message": str | None
}
```

**Error messages (realistic):**
- Failed: "Connection timeout to source system", "Schema validation failed", "Out of memory", "Parquet write error: disk full", "Null key constraint violation"
- Partial: "Partial records skipped: malformed timestamps", "Data quality check flagged outlier batch", "Late-arriving records quarantined"

#### `write_pipeline_logs(logs, output_dir=None) → str`
Writes to `data/logs/pipeline_logs.parquet` using PyArrow engine.

### Usage Context
This generator is typically run **once** during initial setup to seed the Pipeline Health dashboard. After that, the real orchestrator (`pipeline/orchestrator.py`) appends actual execution logs via `_append_pipeline_log()`.

---

## Data Output Summary

| Generator | Output Path | Format | Volume (24hr) |
|-----------|-------------|--------|---------------|
| airport_generator | `data/bronze/{stream}/{stream}_events.json` | JSON | ~60,000 events total |
| pipeline_log_generator | `data/logs/pipeline_logs.parquet` | Parquet | ~432 entries (24 runs × 6 streams × 3 stages) |

---

## Interview Pitch

"The simulator generates realistic airport IoT telemetry with statistically meaningful patterns — exponential flight delay distributions, cosine diurnal temperature curves, HVAC-correlated environmental drift, and peak-hour traffic multipliers. The failure injector creates three controlled scenarios (schema drift, sensor outage, traffic spike) that exercise different pipeline capabilities without requiring real infrastructure. This turns a static demo into an interactive testing platform where you can inject a failure, run the pipeline, and watch the entire observability stack — from quarantine to KPI dashboards to AI diagnosis — respond in real-time."

## Interview Q&A

1. **Q: Why use fixed random seeds?**
   A: Reproducibility — same seed produces identical events every run. This is critical for testing (expected outputs don't change), debugging (reproduce exact scenario), and demos (consistent data for screenshots/presentations). In production, you'd remove the seed for true randomness.

2. **Q: How do you make simulated data realistic?**
   A: Multiple techniques: (1) Domain-appropriate distributions (exponential for delays, cosine for temperature). (2) Correlated values (HVAC degradation → temperature drift). (3) Conditional logic (low visibility → weather hold). (4) Peak-hour patterns matching real airport schedules. (5) Realistic proportions (95% routine security scans, 0.5% breaches).

3. **Q: Why are failure scenarios separate from data generation?**
   A: Separation of concerns — generators produce valid, realistic data. Injectors corrupt specific fields post-generation. This means: (1) Generators stay simple and correct. (2) Scenarios can be toggled independently via UI. (3) You can compose scenarios (schema drift + traffic spike simultaneously). (4) Easy to add new scenarios without touching generation logic.

4. **Q: How does the pipeline_log_generator differ from actual pipeline logs?**
   A: The generator creates synthetic historical data with realistic failure distributions. The real orchestrator writes actual execution metrics. The synthetic logs seed the dashboard for demos; real logs accumulate over usage. Both write to the same parquet file but use slightly different schemas (generator has more stages; real has quality_score column).

5. **Q: How would you replace this simulator with real data?**
   A: Swap `data_generator.py` with a Kafka consumer that reads from actual IoT sensor topics. The Bronze ingestion interface stays the same — it accepts `list[dict]` regardless of source. The rest of the pipeline (Silver validation, Gold aggregation, dashboards) works unchanged because it reads from Bronze files, not from the generator directly.

6. **Q: Why does `inject_traffic_spike` return a value instead of modifying events?**
   A: It's a different failure mode — it affects generation volume, not data quality. You need the multiplier BEFORE events are generated (pass to `generate_all_events(rate_multiplier=3.0)`). Schema drift and sensor outage modify events AFTER generation because they corrupt specific field values.

7. **Q: What's the Faker library used for here?**
   A: Currently minimal — it's imported and seeded but the generators use `random` directly for domain-specific values. Faker is available for future extensions (passenger names, addresses, booking references) without adding a new dependency. The seed ensures Faker output is also reproducible.
