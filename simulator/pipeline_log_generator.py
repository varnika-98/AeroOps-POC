"""AeroOps AI — Pipeline execution log generator.

Simulates ETL pipeline run logs across bronze → silver → gold stages
for each data stream. Writes output to data/logs/pipeline_logs.parquet.
"""

import os
import random
import uuid
from datetime import datetime, timedelta

import pandas as pd

from simulator.config import STREAM_NAMES

random.seed(42)

STAGES = ["bronze_ingestion", "silver_transformation", "gold_aggregation"]

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs")


def generate_pipeline_logs(
    base_date: datetime | None = None,
    runs: int = 24,
) -> list[dict]:
    """Generate pipeline execution logs.

    Args:
        base_date: Starting datetime for the first run.
        runs: Number of pipeline runs to simulate (default: 24, one per hour).

    Returns:
        List of log-entry dicts.
    """
    if base_date is None:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    logs: list[dict] = []

    for run_idx in range(runs):
        run_ts = base_date + timedelta(hours=run_idx)
        run_id = str(uuid.uuid4())

        for stream in STREAM_NAMES:
            records_in = random.randint(500, 5000)
            remaining = records_in

            for stage_idx, stage in enumerate(STAGES):
                # Small failure probability that increases per stage
                fail_prob = 0.02 * (stage_idx + 1)
                partial_prob = 0.05 * (stage_idx + 1)

                roll = random.random()
                if roll < fail_prob:
                    status = "failed"
                elif roll < fail_prob + partial_prob:
                    status = "partial"
                else:
                    status = "success"

                if status == "success":
                    quarantined = random.randint(0, max(1, int(remaining * 0.02)))
                    records_out = remaining - quarantined
                elif status == "partial":
                    quarantined = random.randint(
                        int(remaining * 0.05), int(remaining * 0.15)
                    )
                    records_out = remaining - quarantined
                else:  # failed
                    quarantined = 0
                    records_out = 0

                duration = round(random.uniform(0.5, 30.0), 2)
                error_msg = None
                if status == "failed":
                    error_msg = random.choice(
                        [
                            "Connection timeout to source system",
                            "Schema validation failed: unexpected column",
                            "Out of memory during transformation",
                            "Parquet write error: disk full",
                            "Null key constraint violation",
                        ]
                    )
                elif status == "partial":
                    error_msg = random.choice(
                        [
                            "Partial records skipped: malformed timestamps",
                            "Data quality check flagged outlier batch",
                            "Late-arriving records quarantined",
                        ]
                    )

                stage_ts = run_ts + timedelta(
                    minutes=stage_idx * 5, seconds=random.randint(0, 59)
                )

                logs.append(
                    {
                        "run_id": run_id,
                        "timestamp": stage_ts.isoformat(),
                        "stage": stage,
                        "stream": stream,
                        "status": status,
                        "records_in": remaining,
                        "records_out": records_out,
                        "records_quarantined": quarantined,
                        "duration_sec": duration,
                        "error_message": error_msg,
                    }
                )

                # Next stage ingests what the previous stage output
                remaining = records_out

    return logs


def write_pipeline_logs(
    logs: list[dict],
    output_dir: str | None = None,
) -> str:
    """Write pipeline logs to a Parquet file.

    Returns:
        Path to the written file.
    """
    if output_dir is None:
        output_dir = LOG_DIR

    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "pipeline_logs.parquet")
    df = pd.DataFrame(logs)
    df.to_parquet(file_path, index=False, engine="pyarrow")
    print(f"  ✓ Pipeline logs: {len(df):,} entries → {file_path}")
    return file_path


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("AeroOps AI — Pipeline Log Generator")
    print("=" * 60)
    print()

    logs = generate_pipeline_logs()
    print(f"Generated {len(logs):,} pipeline log entries.\n")
    print("Writing to data/logs/ …")
    write_pipeline_logs(logs)
    print("\nDone ✓")
