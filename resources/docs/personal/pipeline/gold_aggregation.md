# gold_aggregation.py

> File: `pipeline/gold_aggregation.py`

## Overview

KPI computation engine using DuckDB in-memory SQL. Reads validated Silver parquet tables and produces Gold-layer business KPIs via analytical SQL queries. This is the analytical core — transforming operational records into executive-level metrics consumed by every dashboard page.

## ETL Operations

| Operation | Type | Description |
|-----------|------|-------------|
| Silver Read | Extract | DuckDB `read_parquet()` reads Silver tables directly |
| Quarantine Count | Extract | Counts quarantined records per stream for quality KPIs |
| Flight Aggregation | Transform | Hourly GROUP BY: OTP%, avg delay, max delay, gates used |
| Passenger Aggregation | Transform | Per-checkpoint GROUP BY: avg wait, throughput, totals |
| Pipeline Stats | Transform | Per-stream: run count, avg duration, quality % |
| Quality Scoring | Transform | Per-stream: validation rate = valid / (valid + quarantine) |
| Safety Aggregation | Transform | Per-severity: alert count, avg response time, resolution rate |
| Gold Write | Load | Each KPI table → `data/gold/{name}.parquet` |

## Input Data

| Path | Format | Content |
|------|--------|---------|
| `data/silver/flights.parquet` | Parquet | Flight records: scheduled_time, delay_minutes, status, gate |
| `data/silver/passengers.parquet` | Parquet | Checkpoint throughput: checkpoint, wait_time_minutes, throughput_per_hour, passenger_count |
| `data/silver/cargo.parquet` | Parquet | Cargo tracking: item_type, status, weight_kg |
| `data/silver/environmental.parquet` | Parquet | Sensor readings: temperature_c, humidity_pct, co2_ppm, aqi |
| `data/silver/runway.parquet` | Parquet | Runway conditions: wind_speed_kph, visibility_m, friction_index |
| `data/silver/security.parquet` | Parquet | Security alerts: severity, alert_type, response_time_sec, resolution_status |
| `data/logs/pipeline_logs.parquet` | Parquet | Pipeline execution history: stream, duration_sec, quality_score |
| `data/quarantine/{stream}_quarantine.parquet` | Parquet | Failed record counts per stream |

## Output Data

| Path | Rows From | Key Columns |
|------|-----------|-------------|
| `data/gold/flight_kpis.parquet` | Hourly groups | hour, total_flights, otp_pct, avg_delay_min, max_delay_min, gates_used |
| `data/gold/passenger_kpis.parquet` | Per-checkpoint | checkpoint, avg_wait_min, max_wait_min, avg_throughput, total_passengers |
| `data/gold/pipeline_kpis.parquet` | Per-stream | stream, run_count, avg_duration_sec, avg_quality_pct, records_per_sec |
| `data/gold/quality_kpis.parquet` | Per-stream | stream, total_records, valid_records, quarantined_records, validation_rate_pct |
| `data/gold/safety_kpis.parquet` | Per-severity | severity, alert_count, avg_response_sec, auto_cleared, escalated, resolution_rate_pct |

**Return value:**
```python
{"flight_kpis": 24, "passenger_kpis": 8, "pipeline_kpis": 6, "quality_kpis": 6, "safety_kpis": 4}
```

## Purpose

- **Business intelligence layer** — Transforms operational data into decision-ready KPIs
- **Dashboard source** — Every metric card, gauge, and chart reads from Gold tables
- **Efficient reads** — Pre-computed aggregates = fast dashboard loads (no raw data scanning)
- **DuckDB advantage** — SQL-based analytics without persistent database infrastructure

## Key SQL Patterns

**OTP Calculation (flights):**
```sql
COUNT(*) FILTER (WHERE delay_minutes <= 15) * 100.0 / COUNT(*) AS otp_pct
```

**Quality Score (cross-table):**
```python
validation_rate_pct = silver_count * 100.0 / (silver_count + quarantine_count)
```

**Safety Resolution Rate:**
```sql
COUNT(*) FILTER (WHERE resolution_status != 'escalated') * 100.0 / COUNT(*) AS resolution_rate_pct
```

## Interview Pitch

"Gold aggregation uses DuckDB as an in-memory analytical engine to compute business KPIs via SQL. DuckDB reads parquet natively — no ETL tool or database server needed. Each pipeline run recomputes 5 Gold tables from Silver: flight OTP, passenger throughput, pipeline health, data quality, and safety metrics. The dashboard reads these pre-computed tables for sub-second page loads. This is the same pattern as dbt models materializing into a data warehouse, but zero-infrastructure."

## Interview Q&A

1. **Q: Why DuckDB instead of pandas for aggregation?**
   A: DuckDB's columnar engine is optimized for GROUP BY and window functions. For queries like "OTP% by hour across 14,000 flights," SQL is more readable and often 10-100× faster than pandas groupby. DuckDB also reads parquet without loading the full file into memory (pushdown predicates).

2. **Q: Why in-memory DuckDB instead of a persistent database?**
   A: Gold tables are fully recomputed each run — there's no state to persist between runs. The parquet files ARE the durable store. In-memory DuckDB is just the computation engine. This means zero admin (no backup, no schema migrations, no vacuum).

3. **Q: How does `_compute_quality_kpis` work differently from the other compute functions?**
   A: It's the only one that reads TWO sources (Silver + Quarantine) across all 6 streams in a Python loop. The others use a single DuckDB SQL query. This is because quality is a cross-table metric: valid records in Silver vs invalid in Quarantine.

4. **Q: How would you add incremental processing for scale?**
   A: Track a high-water mark (last processed timestamp). On each run, read only new Silver records. Merge new aggregates with existing Gold using DuckDB MERGE or pandas concat + re-aggregate. Periodic full rebuilds ensure drift correction.

5. **Q: What's the `FILTER (WHERE ...)` syntax?**
   A: DuckDB/PostgreSQL aggregate filter — applies a condition to a specific aggregate without affecting others. `COUNT(*) FILTER (WHERE delay <= 15)` counts only on-time flights while `COUNT(*)` in the same query counts all flights. Cleaner than CASE WHEN.
