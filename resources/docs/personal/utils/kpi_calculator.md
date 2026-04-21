# kpi_calculator.py

> File: `utils/kpi_calculator.py`

## Overview

Central KPI computation engine that reads Gold/Silver/Quarantine parquet files and returns aggregated metrics for all dashboard pages. Every KPI card on every page ultimately calls a function in this module.

## Data Dependencies

| Data File | Read By | Content |
|-----------|---------|---------|
| `data/gold/flight_kpis.parquet` | `get_flight_kpis()` | OTP%, avg_delay_min, total_flights, gate utilization |
| `data/gold/passenger_kpis.parquet` | `get_passenger_kpis()` | throughput_per_hour, avg_wait_time, total_passengers |
| `data/gold/quality_kpis.parquet` | `get_data_quality_scores()` | Per-stream quality_score, validation_rate_pct |
| `data/gold/safety_kpis.parquet` | `get_safety_kpis()` | response_time, alert counts, resolution rates |
| `data/logs/pipeline_logs.parquet` | `get_pipeline_health()` | Pipeline success rate, avg duration, throughput |
| `data/logs/ai_metrics.json` | `get_ai_kpis()` | LLM usage: tokens, cost, latency by prompt type |

**Writes:** None (read-only module)

## Key Functions

### `get_pipeline_health() → dict`
Computes pipeline reliability metrics from execution logs.
- **Returns:** `success_rate`, `avg_duration_sec`, `total_runs`, `records_processed`
- **Success logic:** Run reaches Gold stage OR has status=success
- **Used by:** Command Center, Pipeline Health

### `get_data_quality_scores() → dict`
Per-stream quality scores from Gold quality table.
- **Returns:** `{stream: {"quality_score": float, "validation_rate_pct": float}}`
- **Used by:** Command Center, KPI Metrics

### `get_flight_kpis() → dict`
Flight operations metrics.
- **Returns:** `otp_pct`, `avg_delay_min`, `total_flights`, `gate_utilization`
- **Used by:** Command Center, Passenger Analytics

### `get_passenger_kpis() → dict`
Terminal throughput metrics.
- **Returns:** `throughput_per_hour`, `avg_wait_time`, `total_passengers`
- **Used by:** Command Center, Passenger Analytics

### `get_safety_kpis() → dict`
Security and safety response metrics.
- **Returns:** `avg_response_time`, `alert_count`, `resolution_rate`
- **Used by:** KPI Metrics summary table

### `get_environmental_compliance() → dict`
Environmental regulatory compliance check.
- **Returns:** `compliance_pct`, per-parameter compliance
- **Used by:** KPI Metrics

### `get_ai_kpis() → dict`
LLM usage aggregates from ai_metrics.json.
- **Returns:** `total_requests`, `avg_latency_sec`, `total_tokens`, `total_input_tokens`, `total_output_tokens`, `total_cost_usd`, `error_rate_pct`, `by_prompt_type` (with input_tokens, output_tokens, count, cost, avg_latency per type)
- **Used by:** AI Performance Monitor

### `get_overall_system_health() → dict`
Aggregates all KPIs with health status determination.
- **Used by:** AI Ops Center (severity banner)

### `_safe_read(relative_path: str) → pd.DataFrame | None`
Safe parquet reader — returns None if file missing or corrupt.

## Threshold Reference

| KPI | Green | Yellow | Red |
|-----|-------|--------|-----|
| Pipeline Success Rate | ≥95% | 80-94% | <80% |
| Pipeline Avg Duration | ≤20s | 21-40s | >40s |
| Data Quality Score | ≥95% | 85-94% | <85% |
| Flight OTP % | ≥80% | 60-79% | <60% |
| Avg Delay | ≤10 min | 11-20 min | >20 min |
| Environmental Compliance | ≥95% | 85-94% | <85% |
| AI Avg Latency | <5s | 5-10s | ≥10s |
| AI Error Rate | <5% | 5-20% | ≥20% |

## Interview Questions

1. **Q: Why compute KPIs on-demand instead of pre-computing?**
   A: Gold tables are already pre-computed aggregates. This module reads them and applies thresholds. The computation is lightweight (read parquet + compare values). Pre-computing thresholds would add staleness without performance benefit.

2. **Q: How does `_safe_read` handle missing data gracefully?**
   A: Returns None on any exception (FileNotFoundError, corrupt parquet). Callers check for None and show "No data available" messages. This prevents the entire dashboard from crashing if one data file is missing.
