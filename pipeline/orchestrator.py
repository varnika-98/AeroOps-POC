"""AeroOps AI — Pipeline orchestrator (Bronze → Silver → Gold)."""

import os
import time
from datetime import datetime, timezone

import pandas as pd

from pipeline.bronze_ingestion import ingest_to_bronze  # noqa: F401 (re-export)
from pipeline.gold_aggregation import aggregate_to_gold
from pipeline.silver_transformation import transform_to_silver

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(BASE_DIR, "data", "logs")

DEFAULT_STREAMS = [
    "flights",
    "passengers",
    "cargo",
    "environmental",
    "runway",
    "security",
]


def _append_pipeline_log(entry: dict) -> None:
    """Append a pipeline execution log entry to the logs Parquet file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = os.path.join(LOGS_DIR, "pipeline_logs.parquet")

    df_new = pd.DataFrame([entry])

    if os.path.isfile(log_path):
        df_existing = pd.read_parquet(log_path)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_parquet(log_path, index=False)


def run_pipeline(streams: list[str] | None = None) -> dict:
    """Execute the full Bronze → Silver → Gold pipeline.

    1. Apply Silver transformations per stream (reads from Bronze)
    2. Compute Gold aggregations
    3. Log pipeline execution metrics
    4. Return summary with timing and quality metrics
    """
    if streams is None:
        streams = DEFAULT_STREAMS

    pipeline_start = time.time()
    run_ts = datetime.now(timezone.utc).isoformat()

    silver_results: dict[str, dict] = {}
    stream_timings: dict[str, float] = {}

    # --- Silver transformations ---
    for stream in streams:
        t0 = time.time()
        try:
            result = transform_to_silver(stream)
        except Exception as exc:
            result = {
                "total_records": 0,
                "passed": 0,
                "failed": 0,
                "quarantined": 0,
                "quality_score": 0.0,
                "failure_reasons": {},
                "error": str(exc),
            }
        elapsed = round(time.time() - t0, 3)
        stream_timings[stream] = elapsed
        silver_results[stream] = result

        _append_pipeline_log({
            "run_timestamp": run_ts,
            "stage": "silver",
            "stream": stream,
            "total_records": result["total_records"],
            "passed": result["passed"],
            "failed": result["failed"],
            "quality_score": result["quality_score"],
            "duration_sec": elapsed,
        })

    # --- Gold aggregations ---
    t0 = time.time()
    try:
        gold_summary = aggregate_to_gold()
    except Exception as exc:
        gold_summary = {"error": str(exc)}
    gold_elapsed = round(time.time() - t0, 3)

    _append_pipeline_log({
        "run_timestamp": run_ts,
        "stage": "gold",
        "stream": "all",
        "total_records": sum(r["total_records"] for r in silver_results.values()),
        "passed": sum(r["passed"] for r in silver_results.values()),
        "failed": sum(r["failed"] for r in silver_results.values()),
        "quality_score": 0.0,
        "duration_sec": gold_elapsed,
    })

    total_elapsed = round(time.time() - pipeline_start, 3)

    return {
        "run_timestamp": run_ts,
        "total_duration_sec": total_elapsed,
        "streams_processed": len(streams),
        "silver_results": silver_results,
        "gold_summary": gold_summary,
        "stream_timings": stream_timings,
    }


if __name__ == "__main__":
    import json as _json

    print("AeroOps AI — Running Medallion Pipeline …")
    summary = run_pipeline()
    print(_json.dumps(summary, indent=2, default=str))
    print(f"\nPipeline completed in {summary['total_duration_sec']}s")
