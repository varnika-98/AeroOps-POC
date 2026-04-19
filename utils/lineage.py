"""Data lineage tracking for the medallion architecture (Bronze → Silver → Gold)."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LINEAGE_MODEL = {
    "flights": {
        "bronze": "data/bronze/flights/",
        "silver": "data/silver/flights.parquet",
        "gold": ["data/gold/flight_kpis.parquet"],
        "kpis": ["Flight OTP", "Avg Delay", "Gate Utilization"],
    },
    "passengers": {
        "bronze": "data/bronze/passengers/",
        "silver": "data/silver/passengers.parquet",
        "gold": ["data/gold/passenger_kpis.parquet"],
        "kpis": ["Passenger Throughput", "Avg Wait Time", "Checkpoint Efficiency"],
    },
    "cargo": {
        "bronze": "data/bronze/cargo/",
        "silver": "data/silver/cargo.parquet",
        "gold": ["data/gold/flight_kpis.parquet"],
        "kpis": ["Baggage Processing Rate", "Lost Baggage Rate"],
    },
    "environmental": {
        "bronze": "data/bronze/environmental/",
        "silver": "data/silver/environmental.parquet",
        "gold": ["data/gold/quality_kpis.parquet"],
        "kpis": ["Environmental Compliance", "HVAC Health"],
    },
    "runway": {
        "bronze": "data/bronze/runway/",
        "silver": "data/silver/runway.parquet",
        "gold": ["data/gold/safety_kpis.parquet"],
        "kpis": ["Runway Utilization", "Weather Safety Index"],
    },
    "security": {
        "bronze": "data/bronze/security/",
        "silver": "data/silver/security.parquet",
        "gold": ["data/gold/safety_kpis.parquet"],
        "kpis": ["Incident Response Time", "Alert Resolution Rate"],
    },
}


def get_lineage_for_stream(stream: str) -> dict:
    """Returns full lineage path for a stream.

    Args:
        stream: One of flights, passengers, cargo, environmental, runway, security.

    Returns:
        Dict with bronze, silver, gold paths and associated KPIs,
        plus existence flags for each layer.
    """
    if stream not in LINEAGE_MODEL:
        return {"error": f"Unknown stream: {stream}"}

    model = LINEAGE_MODEL[stream]
    result = {**model, "stream": stream}

    # Check file/directory existence at each layer
    bronze_path = PROJECT_ROOT / model["bronze"]
    result["bronze_exists"] = bronze_path.exists()
    if result["bronze_exists"] and bronze_path.is_dir():
        result["bronze_file_count"] = len(list(bronze_path.glob("*")))

    silver_path = PROJECT_ROOT / model["silver"]
    result["silver_exists"] = silver_path.exists()
    if result["silver_exists"]:
        try:
            df = pd.read_parquet(silver_path)
            result["silver_record_count"] = len(df)
        except Exception:
            result["silver_record_count"] = 0

    result["gold_exists"] = {}
    for gp in model["gold"]:
        gold_path = PROJECT_ROOT / gp
        result["gold_exists"][gp] = gold_path.exists()

    return result


def get_impact_analysis(stream: str) -> dict:
    """If a stream fails, which Gold KPIs are impacted?

    Args:
        stream: The stream that failed.

    Returns:
        Dict with affected_kpis, affected_gold_tables, and severity.
    """
    if stream not in LINEAGE_MODEL:
        return {"error": f"Unknown stream: {stream}"}

    model = LINEAGE_MODEL[stream]

    # Find all streams sharing the same gold tables
    shared_streams = []
    for other_stream, other_model in LINEAGE_MODEL.items():
        if other_stream != stream:
            overlap = set(model["gold"]) & set(other_model["gold"])
            if overlap:
                shared_streams.append(other_stream)

    return {
        "stream": stream,
        "affected_kpis": model["kpis"],
        "affected_gold_tables": model["gold"],
        "shared_gold_with": shared_streams,
        "severity": "high" if len(model["kpis"]) > 2 else "medium",
    }


def get_reverse_lineage(kpi_name: str) -> list:
    """Trace a Gold KPI back to its Bronze source streams.

    Args:
        kpi_name: Name of the KPI to trace.

    Returns:
        List of dicts, each describing a source stream for this KPI.
    """
    sources = []
    for stream, model in LINEAGE_MODEL.items():
        if kpi_name in model["kpis"]:
            sources.append({
                "stream": stream,
                "bronze": model["bronze"],
                "silver": model["silver"],
                "gold": model["gold"],
            })
    return sources


def get_sankey_data() -> dict:
    """Returns sources, targets, values, labels for a Sankey diagram showing B→S→G flow.

    Counts records at each layer to show flow volumes.
    """
    labels = []
    sources = []
    targets = []
    values = []

    # Build label indices: Bronze nodes, then Silver nodes, then Gold nodes
    bronze_labels = []
    silver_labels = []
    gold_labels = []
    gold_set = set()

    for stream in LINEAGE_MODEL:
        bronze_labels.append(f"Bronze: {stream}")
        silver_labels.append(f"Silver: {stream}")
        for gp in LINEAGE_MODEL[stream]["gold"]:
            gold_name = f"Gold: {Path(gp).stem}"
            if gold_name not in gold_set:
                gold_labels.append(gold_name)
                gold_set.add(gold_name)

    labels = bronze_labels + silver_labels + gold_labels
    label_idx = {label: i for i, label in enumerate(labels)}

    for stream, model in LINEAGE_MODEL.items():
        bronze_label = f"Bronze: {stream}"
        silver_label = f"Silver: {stream}"

        # Count records at bronze layer
        bronze_path = PROJECT_ROOT / model["bronze"]
        bronze_count = 0
        if bronze_path.exists() and bronze_path.is_dir():
            for f in bronze_path.glob("*.parquet"):
                try:
                    bronze_count += len(pd.read_parquet(f))
                except Exception:
                    pass
            for f in bronze_path.glob("*.json"):
                bronze_count += 1  # approximate

        # Count records at silver layer
        silver_path = PROJECT_ROOT / model["silver"]
        silver_count = 0
        if silver_path.exists():
            try:
                silver_count = len(pd.read_parquet(silver_path))
            except Exception:
                pass

        # Use max of bronze/silver or a default for display
        b_to_s = max(bronze_count, silver_count, 100)
        sources.append(label_idx[bronze_label])
        targets.append(label_idx[silver_label])
        values.append(b_to_s)

        # Silver → Gold links
        for gp in model["gold"]:
            gold_label = f"Gold: {Path(gp).stem}"
            gold_path = PROJECT_ROOT / gp
            gold_count = 0
            if gold_path.exists():
                try:
                    gold_count = len(pd.read_parquet(gold_path))
                except Exception:
                    pass
            s_to_g = max(gold_count, silver_count // 2, 50)
            sources.append(label_idx[silver_label])
            targets.append(label_idx[gold_label])
            values.append(s_to_g)

    return {
        "sources": sources,
        "targets": targets,
        "values": values,
        "labels": labels,
    }
