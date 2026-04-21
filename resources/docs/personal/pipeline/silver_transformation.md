# silver_transformation.py

> File: `pipeline/silver_transformation.py`

## Overview

Validation and cleansing engine — transforms raw Bronze JSON into validated Silver Parquet. This is the data quality gate of the pipeline. Records pass validation rules and enter Silver; records that fail are quarantined with tagged failure reasons for root cause analysis.

## ETL Operations

| Operation | Type | Description |
|-----------|------|-------------|
| Bronze Read | Extract | Aggregates all JSON batch files from `data/bronze/{stream}/` into one list |
| Record Validation | Transform | Applies stream-specific rules from `quality_rules.py` to each record |
| Schema Enforcement | Transform | Valid records conform to expected field types and ranges |
| Quarantine Tagging | Transform | Failed records get `_quarantine_reasons` JSON column |
| Silver Write | Load | Valid records → `data/silver/{stream}.parquet` |
| Quarantine Write | Load | Failed records → `data/quarantine/{stream}_quarantine.parquet` |

## Input Data

| Path | Format | Content |
|------|--------|---------|
| `data/bronze/{stream}/*.json` | JSON arrays | All batch files for the stream (accumulated across runs) |

Each JSON file contains a list of event dicts with `_ingested_at` metadata from Bronze ingestion.

## Output Data

| Path | Format | Content |
|------|--------|---------|
| `data/silver/{stream}.parquet` | Parquet | Validated records (full replacement per run) |
| `data/quarantine/{stream}_quarantine.parquet` | Parquet | Invalid records with `_quarantine_reasons` column |

**Return value:**
```python
{
    "total_records": 14400,
    "passed": 13900,
    "failed": 500,
    "quarantined": 500,
    "quality_score": 0.9653,  # passed / total
    "failure_reasons": {"wind_speed_range": 320, "friction_range": 180}
}
```

## Purpose

- **Data quality gate** — Only validated data reaches Gold aggregation
- **Root cause analysis** — Quarantine records retain failure reasons for diagnostics
- **Quality scoring** — `quality_score = passed / total` feeds Pipeline Health and KPI Metrics
- **Reprocessing** — Reads ALL Bronze files on each run (full recompute from source)
- **Schema contract** — Enforces field presence, types, ranges, and enums per stream

## Key Logic

```python
for record in records:
    passed, failed_rules = validate_record(record, stream_name)
    if passed:
        valid_records.append(record)
    else:
        quarantine_records.append({**record, "_quarantine_reasons": failed_rules})
```

## Interview Pitch

"Silver transformation is where data quality is enforced. Every record passes through stream-specific validation rules — range checks, enum constraints, regex patterns, null checks. Valid records become Silver (trusted analytical data). Invalid records are quarantined with machine-readable failure tags like `wind_speed_range` or `checkpoint_not_null`. This enables automated root cause analysis — when the runway quality score drops, we immediately see which rule is triggering, pointing to the exact sensor or schema issue."

## Interview Q&A

1. **Q: Why full replacement instead of incremental append for Silver?**
   A: The POC reprocesses all Bronze on each run for simplicity and correctness. If a validation rule changes, the full Silver table reflects the new rules immediately. In production, you'd use incremental processing with high-water marks and periodic full rebuilds.

2. **Q: How does the quarantine pattern differ from just dropping bad records?**
   A: Dropped records are invisible — you can't diagnose why quality is dropping. Quarantine preserves the original record plus failure reasons, enabling: (1) root cause analysis (which rule failed most?), (2) source system feedback (tell the sensor team), (3) recovery (re-validate after rule fix).

3. **Q: What happens if Bronze has no files for a stream?**
   A: Returns `{total_records: 0, quality_score: 1.0}`. The Silver file is NOT updated — previous Silver data remains intact. This is safe because no new data ≠ bad data.

4. **Q: How does `_quarantine_reasons` get stored in Parquet?**
   A: The list of failed rule names is JSON-serialized to a string column. Parquet handles strings efficiently. Downstream analysis (KPI Metrics page) uses `json.loads()` to parse reasons for aggregation.
