"""AeroOps AI — Bronze layer ingestion (raw JSON storage)."""

import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def ingest_to_bronze(stream_name: str, events: list[dict]) -> str:
    """Append raw events to Bronze layer as JSON files.

    - No transformations applied
    - Adds ``_ingested_at`` metadata timestamp to every event
    - Creates ``data/bronze/{stream_name}/`` directory if needed
    - Returns the file path of the written batch
    """
    if not events:
        raise ValueError(f"No events provided for stream '{stream_name}'")

    bronze_dir = os.path.join(BASE_DIR, "data", "bronze", stream_name)
    os.makedirs(bronze_dir, exist_ok=True)

    ingested_at = datetime.now(timezone.utc).isoformat()

    enriched: list[dict] = []
    for event in events:
        record = {**event, "_ingested_at": ingested_at}
        enriched.append(record)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"events_{timestamp}.json"
    filepath = os.path.join(bronze_dir, filename)

    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(enriched, fh, indent=2, default=str)

    return filepath
