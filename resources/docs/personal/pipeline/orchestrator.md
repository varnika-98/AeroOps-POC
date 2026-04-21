# orchestrator.py

> File: `pipeline/orchestrator.py`

## Overview

Main pipeline coordinator — executes the full Bronze→Silver→Gold flow with per-stream timing, error isolation, and execution logging. This is the entry point triggered from the Command Center's "Run Pipeline" button. Ensures each stream processes independently (one failure doesn't cascade) and logs every execution for trend analysis.

## ETL Operations

| Operation | Type | Description |
|-----------|------|-------------|
| Silver Transform (per stream) | Orchestration | Calls `transform_to_silver(stream)` for each of 6 streams |
| Gold Aggregation | Orchestration | Calls `aggregate_to_gold()` after all Silver transforms |
| Execution Timing | Monitoring | Measures per-stream and total elapsed time |
| Pipeline Logging | Load | Appends per-stage entries to `data/logs/pipeline_logs.parquet` |
| Error Isolation | Control | Catches per-stream exceptions, continues with remaining streams |

## Input Data

| Source | Format | Content |
|--------|--------|---------|
| `data/bronze/{stream}/*.json` | JSON | Consumed indirectly via `transform_to_silver()` |

The orchestrator doesn't read data directly — it delegates to Silver and Gold modules.

## Output Data

| Path | Format | Content |
|------|--------|---------|
| `data/silver/{stream}.parquet` | Parquet | Via `transform_to_silver()` — validated records |
| `data/quarantine/{stream}_quarantine.parquet` | Parquet | Via `transform_to_silver()` — failed records |
| `data/gold/*.parquet` | Parquet | Via `aggregate_to_gold()` — 5 KPI tables |
| `data/logs/pipeline_logs.parquet` | Parquet | Execution log (append-only) |

**Pipeline log entry schema:**
```python
{
    "run_timestamp": "2026-04-20T16:30:00+00:00",  # ISO UTC
    "stage": "silver",                              # "silver" or "gold"
    "stream": "runway",                             # stream name or "all" for gold
    "total_records": 4320,
    "passed": 4000,
    "failed": 320,
    "quality_score": 0.926,
    "duration_sec": 1.234
}
```

**Return value:**
```python
{
    "run_timestamp": "2026-04-20T16:30:00+00:00",
    "total_duration_sec": 8.542,
    "streams_processed": 6,
    "silver_results": {"flights": {...}, "passengers": {...}, ...},
    "gold_summary": {"flight_kpis": 24, "passenger_kpis": 8, ...},
    "stream_timings": {"flights": 1.2, "passengers": 0.9, ...}
}
```

## Purpose

- **Single entry point** — One function call executes the entire pipeline
- **Error isolation** — Stream failures are caught and logged; other streams continue
- **Execution history** — Every run is logged for Pipeline Health trend analysis
- **Timing visibility** — Per-stream duration enables bottleneck identification
- **CLI support** — `if __name__ == "__main__"` enables `python -m pipeline.orchestrator`

## Pipeline Flow

```
run_pipeline(streams=None)
│
├── For each stream in [flights, passengers, cargo, environmental, runway, security]:
│   ├── t0 = time.time()
│   ├── try: result = transform_to_silver(stream)
│   │   except: result = {error: str(exc), quality_score: 0.0}
│   ├── elapsed = time.time() - t0
│   ├── _append_pipeline_log({stage: "silver", stream, duration, quality_score, ...})
│   └── silver_results[stream] = result
│
├── t0 = time.time()
├── gold_summary = aggregate_to_gold()
├── _append_pipeline_log({stage: "gold", stream: "all", duration, ...})
│
└── Return {run_timestamp, total_duration_sec, silver_results, gold_summary, stream_timings}
```

## Interview Pitch

"The orchestrator implements fault-isolated sequential processing — each stream runs independently with try/catch, so a runway sensor failure doesn't block passenger or flight processing. Every execution is timed and logged to a pipeline_logs table, enabling the Pipeline Health dashboard to show success rates, duration trends, and throughput over time. In production, this maps to an Airflow DAG with parallel tasks and SLA monitoring."

## Interview Q&A

1. **Q: Why sequential processing instead of parallel?**
   A: For the POC, sequential is simpler and deterministic. Streams ARE independent (no cross-stream dependencies in Silver), so parallelization is straightforward. In production, use `concurrent.futures.ThreadPoolExecutor` or Airflow parallel tasks. Gold must wait for all Silver to complete.

2. **Q: How does `_append_pipeline_log` prevent data loss?**
   A: It reads existing parquet → concatenates new entry → writes back. If the file doesn't exist (first run), it creates it. The read-concat-write pattern is safe for single-writer scenarios (which this POC is). For multi-writer, you'd use a proper database or partitioned writes.

3. **Q: What happens when a stream fails?**
   A: The exception is caught, and a result with `quality_score: 0.0` and an `error` field is recorded. The pipeline continues with remaining streams. Gold aggregation runs with whatever Silver data is available. Pipeline Health shows the failure as a red entry.

4. **Q: How would you add retry logic?**
   A: Wrap the `transform_to_silver()` call in a retry decorator with exponential backoff (e.g., `tenacity` library). Limit to 2-3 retries. Log each attempt. After max retries, record the failure and move on. Alert via the alerts system if a stream fails consistently.
