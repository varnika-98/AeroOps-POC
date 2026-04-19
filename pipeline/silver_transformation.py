"""AeroOps AI — Silver layer transformation (validated Parquet output)."""

import glob
import json
import os

import pandas as pd

from pipeline.quality_rules import validate_record

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_bronze_records(stream_name: str) -> list[dict]:
    """Read all JSON batch files from the Bronze directory for a stream."""
    bronze_dir = os.path.join(BASE_DIR, "data", "bronze", stream_name)
    if not os.path.isdir(bronze_dir):
        return []

    records: list[dict] = []
    for path in sorted(glob.glob(os.path.join(bronze_dir, "*.json"))):
        with open(path, "r", encoding="utf-8") as fh:
            batch = json.load(fh)
            if isinstance(batch, list):
                records.extend(batch)
    return records


def transform_to_silver(stream_name: str) -> dict:
    """Read Bronze JSON files, validate each record, write valid records to
    Silver Parquet and quarantine bad records.

    Returns:
        Dictionary with quality metrics for this stream.
    """
    records = _load_bronze_records(stream_name)
    total = len(records)

    if total == 0:
        return {
            "total_records": 0,
            "passed": 0,
            "failed": 0,
            "quarantined": 0,
            "quality_score": 1.0,
            "failure_reasons": {},
        }

    valid_records: list[dict] = []
    quarantine_records: list[dict] = []
    failure_counts: dict[str, int] = {}

    for record in records:
        passed, failed_rules = validate_record(record, stream_name)
        if passed:
            valid_records.append(record)
        else:
            quarantine_record = {**record, "_quarantine_reasons": failed_rules}
            quarantine_records.append(quarantine_record)
            for rule in failed_rules:
                failure_counts[rule] = failure_counts.get(rule, 0) + 1

    # Write valid records to Silver
    silver_dir = os.path.join(BASE_DIR, "data", "silver")
    os.makedirs(silver_dir, exist_ok=True)

    if valid_records:
        df_valid = pd.DataFrame(valid_records)
        df_valid.to_parquet(
            os.path.join(silver_dir, f"{stream_name}.parquet"), index=False
        )

    # Write quarantined records
    quarantine_dir = os.path.join(BASE_DIR, "data", "quarantine")
    os.makedirs(quarantine_dir, exist_ok=True)

    if quarantine_records:
        df_quarantine = pd.DataFrame(quarantine_records)
        # Store reasons as JSON string for Parquet compatibility
        df_quarantine["_quarantine_reasons"] = df_quarantine[
            "_quarantine_reasons"
        ].apply(json.dumps)
        df_quarantine.to_parquet(
            os.path.join(quarantine_dir, f"{stream_name}_quarantine.parquet"),
            index=False,
        )

    quality_score = round(len(valid_records) / total, 4) if total > 0 else 1.0

    return {
        "total_records": total,
        "passed": len(valid_records),
        "failed": len(quarantine_records),
        "quarantined": len(quarantine_records),
        "quality_score": quality_score,
        "failure_reasons": failure_counts,
    }
