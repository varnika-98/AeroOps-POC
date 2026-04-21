# Pipeline Health

> File: `app/pages/2_Pipeline_Health.py`

## Overview

Pipeline Health monitors the data pipeline's execution — success rates, processing duration, throughput, and run timelines. It's the DevOps/DataOps view that ensures the medallion pipeline (Bronze→Silver→Gold) is running reliably and efficiently.

**Supporting files:** `utils/kpi_calculator.py` (`get_pipeline_health`), `utils/charts.py` (stacked_bar, gantt, time_series), `pipeline/orchestrator.py`

## Metrics

### KPI Cards

| Metric | Calculation | Thresholds | Data Source |
|--------|-------------|------------|-------------|
| **Pipeline Success Rate** | `success_runs / total_runs × 100` | 🟢 ≥95% · 🟡 ≥80% · 🔴 <80% | `logs/pipeline_logs.parquet` |
| **Total Runs** | Count of unique `run_timestamp` | Neutral | `logs/pipeline_logs.parquet` |
| **Avg Duration (sec)** | Mean of `duration_sec` | 🟢 ≤20s · 🟡 ≤40s · 🔴 >40s | `logs/pipeline_logs.parquet` |
| **Records Processed** | Sum of `total_records` | Neutral | `logs/pipeline_logs.parquet` |

Success rate calculation: a run is "successful" if it reaches the Gold stage or has status=success.

### Charts

| Chart | Type | Key Details |
|-------|------|-------------|
| **Pipeline Run Timeline** | Gantt | Per-stream timeline, green=success, red=failed, yellow=partial |
| **Success/Failure Trend** | Stacked Bar | Hourly run counts by status |
| **Duration by Stage** | Grouped Bar | Avg duration per stage (bronze/silver/gold) grouped by stream |
| **Throughput per Stream** | Multi-line | Records processed over time, one line per stream |

### Color Mappings
- **Gantt status:** Green (success), Red (failed), Yellow (partial)
- **Stacked bar:** Green (success), Red (failed), Yellow (warning), Blue (other)
- **Stage bars:** Sky Blue, Green, Orange, Navy, Yellow

### Pipeline Log Viewer
Filterable table with columns: run_id, run_timestamp, stage, stream, status, total_records, passed, failed, quality_score, duration_sec. Filters by stream, status, and stage.

## Purpose & Inference

| Metric | Purpose | What to Infer |
|--------|---------|---------------|
| Success Rate | Pipeline reliability tracking | <95% indicates systematic issues; correlate with specific streams |
| Avg Duration | Performance monitoring | Increasing duration suggests data volume growth or processing bottleneck |
| Gantt Timeline | Visual execution flow | Overlapping failures across streams suggest shared infrastructure issue vs isolated stream problem |
| Duration by Stage | Bottleneck identification | If Gold takes 10× longer than Silver, the DuckDB aggregation may need optimization |
| Throughput | Volume trend tracking | Dropping throughput + high success rate = data generation issue, not pipeline issue |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/logs/pipeline_logs.parquet` | Logs | `load_pipeline_logs()` | run_timestamp, stage, stream, status, total_records, passed, failed, quality_score, duration_sec |

Each row represents one stage execution for one stream in one pipeline run. Multiple rows per run (one per stream × stage).

**Write operations:** None (read-only page)

## Interview Pitch

*"Pipeline Health gives us DataOps observability. The Gantt chart shows execution flow across all 6 streams — if I inject a schema drift failure, you see the runway stream turn red while others stay green. The duration-by-stage chart helps identify which layer is the bottleneck. Combined with the filterable log viewer, we can drill from 'pipeline is slow' to 'Gold aggregation on environmental stream took 45 seconds because quarantine had 10K records.'"*

## Interview Questions

1. **Q: How do you determine if a pipeline run is successful?**
   A: A run is successful if all stages (Bronze→Silver→Gold) complete. We check if the run reaches the Gold stage OR has an explicit success status. Partial means some streams passed validation but not all.

2. **Q: What would cause the average duration to spike?**
   A: Three common causes — (1) traffic spike scenario generating 3× normal volume, (2) high quarantine rates forcing more validation processing, (3) DuckDB Gold aggregation on larger Silver tables. The duration-by-stage chart isolates which layer is responsible.

3. **Q: How is the pipeline log accumulated?**
   A: Each pipeline run appends entries to `pipeline_logs.parquet` via the orchestrator. Each entry includes stream, stage, timing, record counts, and quality score. It's append-only — we never overwrite, enabling full execution history.

4. **Q: How would you add alerting for pipeline failures?**
   A: In production, I'd add a post-run check in the orchestrator: if success_rate < threshold, emit an alert to `alerts.parquet` with severity based on how many streams failed. The AI Ops Center already reads alerts for context-building.
