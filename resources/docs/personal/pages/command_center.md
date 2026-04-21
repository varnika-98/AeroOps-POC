# Command Center

> Entry point: `app/Command_Center.py`

## Overview

The Command Center is the main dashboard and control hub for AeroOps airport operations. It provides a real-time overview of all airport systems — flights, passengers, pipeline health, and data quality — in a single view. It also serves as the control panel for running the data pipeline, generating new simulation data, and injecting failure scenarios for testing.

**Supporting files:** `utils/kpi_calculator.py` (all KPI functions), `utils/theme.py` (styling), `simulator/data_generator.py` (data generation), `simulator/failure_injector.py` (fault injection), `pipeline/orchestrator.py` (pipeline execution)

## Metrics

| Metric | Calculation | Thresholds | Data Source |
|--------|-------------|------------|-------------|
| **Total Flights Today** | `flight_kpis.get("total_flights")` | Always healthy | `gold/flight_kpis.parquet` |
| **Passengers Processed** | `passenger_kpis.get("total_passengers")` | Always healthy | `gold/passenger_kpis.parquet` |
| **Pipeline Success Rate** | `success_runs / total_runs × 100` | 🟢 ≥95% · 🟡 ≥80% · 🔴 <80% | `logs/pipeline_logs.parquet` |
| **Data Quality Score** | Average `quality_score` across all streams | 🟢 ≥90% · 🟡 ≥70% · 🔴 <70% | `gold/quality_kpis.parquet` |

### Medallion Layer Health (Bar Chart)
- Shows record counts at Bronze, Silver, and Gold layers
- Bronze counts from `bronze/**/*.json` file sizes
- Silver counts from `silver/*.parquet` row counts
- Gold counts from `gold/*.parquet` row counts
- **Inference:** A healthy pipeline shows decreasing counts B→S→G (filtering/aggregation). If Bronze >> Silver, many records are being quarantined. If Gold is empty, aggregation may have failed.

### Sidebar Controls
- **Failure Scenarios:** 3 toggles (Runway Schema Drift, Passenger Sensor Outage, Holiday Traffic Spike)
- **Pipeline Controls:** "Run Pipeline" and "Generate New Data" buttons
- **Auto Refresh:** 10-300 second interval slider

## Purpose & Inference

| Metric | Purpose | What to Infer |
|--------|---------|---------------|
| Total Flights | Operational volume indicator | Low count may indicate data generation hasn't run or pipeline stalled |
| Passengers Processed | Throughput tracking | Should correlate with flight count; discrepancy suggests sensor issues |
| Pipeline Success Rate | Pipeline reliability | <95% indicates systematic failures; check Pipeline Health for details |
| Data Quality Score | Overall data trustworthiness | <90% means downstream KPIs may be unreliable |
| Layer Health | Pipeline flow verification | Disproportionate layer sizes indicate bottlenecks or failures at a specific stage |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/gold/flight_kpis.parquet` | Gold | `load_flight_kpis()` | Hourly flight aggregates: OTP%, avg delay, gate count |
| `data/gold/passenger_kpis.parquet` | Gold | `load_passenger_kpis()` | Checkpoint throughput, wait times, passenger totals |
| `data/gold/quality_kpis.parquet` | Gold | `load_quality_scores()` | Per-stream quality score, validation rate |
| `data/gold/safety_kpis.parquet` | Gold | `load_safety_kpis()` | Alert counts, response times, resolution rates |
| `data/logs/pipeline_logs.parquet` | Logs | `load_pipeline_health()` | Per-run: stream, stage, status, duration, records |
| `data/silver/*.parquet` | Silver | `load_silver_counts()` | All 6 stream Silver tables (row counts) |
| `data/bronze/**/*.json` | Bronze | `load_bronze_counts()` | Raw event JSON batches (file counts) |
| `data/gold/*.parquet` | Gold | `load_gold_counts()` | All Gold KPI tables (row counts) |

**Write operations:** Triggers `data_generator.py` (writes Bronze), `orchestrator.py` (writes Silver/Gold/Logs)

## Interview Pitch

*"The Command Center is our single-pane-of-glass for airport operations. It aggregates KPIs from 6 IoT data streams processed through a medallion architecture. What makes it powerful is the integrated failure injection — I can toggle schema drift or sensor outages in real-time, watch quality scores drop, then trace the root cause through our lineage system. It demonstrates the full observability loop: detect → diagnose → remediate."*

## Interview Questions

1. **Q: Why a medallion architecture (Bronze/Silver/Gold) instead of a single ETL step?**
   A: Separation of concerns — Bronze preserves raw data for replay, Silver handles validation and quarantine, Gold computes business KPIs. If a quality rule changes, we re-process Silver→Gold without re-ingesting. It also enables data lineage tracing.

2. **Q: How do you handle data quality in the pipeline?**
   A: Each record passes through stream-specific validation rules (range checks, regex, enums, not-null). Failed records are quarantined with tagged failure reasons rather than dropped, enabling root cause analysis. Quality scores propagate to the dashboard in real-time.

3. **Q: What happens when a failure scenario is injected?**
   A: The failure injector modifies events before Bronze ingestion — e.g., schema drift multiplies wind_speed by 4× to exceed range validation. The pipeline quarantines these records, quality score drops, the Command Center reflects it immediately, and the AI Ops Center can diagnose the root cause.

4. **Q: How would you scale this for a production airport?**
   A: Replace the JSON-based Bronze layer with a message queue (Kafka/Kinesis), Silver with Spark/Flink streaming, and Gold with a persistent DuckDB or data warehouse. The architecture is the same — only the infrastructure changes.
