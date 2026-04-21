# bronze_ingestion.py

> File: `pipeline/bronze_ingestion.py`

## Overview

Raw data ingestion layer — the entry point of the medallion pipeline. Accepts event lists from the data generator and persists them as timestamped JSON files in the Bronze directory. Follows the "store raw, process later" pattern — zero transformations, only metadata enrichment.

## ETL Operations

| Operation | Type | Description |
|-----------|------|-------------|
| Metadata Enrichment | Extract → Load | Adds `_ingested_at` UTC timestamp to every event |
| Batch Write | Load | Serializes event list to JSON with indentation |

**No transformations applied.** This is intentional — Bronze preserves raw fidelity for reprocessing.

## Input Data

| Source | Format | Content |
|--------|--------|---------|
| `simulator/data_generator.py` → event lists | `list[dict]` (in-memory) | Raw IoT events from any of 6 streams |

Each event is a dictionary with stream-specific fields (e.g., `flight_id`, `delay_minutes` for flights).

**Parameters:**
- `stream_name: str` — One of: flights, passengers, cargo, environmental, runway, security
- `events: list[dict]` — Generated event records (must be non-empty)

## Output Data

| Path | Format | Content |
|------|--------|---------|
| `data/bronze/{stream_name}/events_{timestamp}.json` | JSON array | All events in one batch, each with `_ingested_at` added |

**Filename pattern:** `events_YYYYMMDD_HHMMSS_ffffff.json` (microsecond precision prevents collisions)

**Directory structure:**
```
data/bronze/
├── flights/
│   ├── events_20260420_163000_123456.json
│   └── events_20260420_170000_789012.json
├── passengers/
├── cargo/
├── environmental/
├── runway/
└── security/
```

## Purpose

- **Immutable raw store** — Source of truth for reprocessing if Silver logic changes
- **Append-only** — Each pipeline run adds a new file, never overwrites
- **Audit trail** — `_ingested_at` timestamp enables troubleshooting data delays
- **Decouples generation from processing** — Generator and Silver transform run independently

## Interview Pitch

"Bronze ingestion implements the 'store raw' principle of the medallion architecture. By persisting unmodified sensor data with only an ingestion timestamp, we maintain an immutable audit trail. If validation rules change or we discover a transformation bug, we can reprocess from Bronze without re-ingesting from source systems. This is the same pattern used at Netflix and Uber for their data lake landing zones."

## Interview Q&A

1. **Q: Why JSON instead of Parquet for Bronze?**
   A: JSON preserves schema flexibility — IoT sensors may change their payload format without notice. JSON handles schema evolution naturally (new fields, missing fields). Parquet requires a fixed schema at write time. The conversion to structured Parquet happens in Silver after validation.

2. **Q: Why batch files instead of a single append-only file?**
   A: Individual batch files enable parallel processing, easy cleanup (delete one batch), and prevent corruption from concurrent writes. If one batch is corrupt, only that batch is lost. At scale, this pattern maps to partitioned object storage (S3 prefix per stream per day).

3. **Q: How would you handle exactly-once ingestion in production?**
   A: Add a deduplication key (event_id + timestamp hash) and check against a dedup store (Redis/DynamoDB) before writing. In the POC, microsecond-precision filenames prevent duplicate files, but duplicate events within a batch are possible.

4. **Q: Why does `ingest_to_bronze` raise on empty events?**
   A: Writing an empty JSON array creates misleading artifacts — a file that looks successful but contains no data. Raising `ValueError` forces the caller (Command Center) to handle the case explicitly, making failures visible rather than silent.
