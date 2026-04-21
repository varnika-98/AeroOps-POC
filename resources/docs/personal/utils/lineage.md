# lineage.py

> File: `utils/lineage.py`

## Overview

Data lineage tracking across the Bronze→Silver→Gold medallion layers. Provides forward impact analysis (what breaks if a stream fails), reverse lineage (trace a KPI back to source), and Sankey diagram data for visualization.

## Data Dependencies

| Data File | Read By | Purpose |
|-----------|---------|---------|
| `data/bronze/{stream}/*.json` | `get_lineage_for_stream()` | Count files (existence + volume check) |
| `data/silver/{stream}.parquet` | `get_lineage_for_stream()` | Row count (existence + volume check) |
| `data/gold/*.parquet` | `get_lineage_for_stream()` | Existence check for lineage completeness |

**Writes:** None (read-only module)

## Lineage Model

```python
LINEAGE_MODEL = {
    "flights": {
        "bronze": "data/bronze/flights/",
        "silver": "data/silver/flights.parquet",
        "gold": ["data/gold/flight_kpis.parquet"],
        "kpis": ["Flight OTP", "Avg Delay", "Gate Utilization"]
    },
    "passengers": {
        "gold": ["data/gold/passenger_kpis.parquet"],
        "kpis": ["Throughput", "Avg Wait Time", "Checkpoint Efficiency"]
    },
    "cargo": {
        "gold": ["data/gold/passenger_kpis.parquet"],  # shares with passengers
        "kpis": ["Baggage Processing Rate"]
    },
    "environmental": {
        "gold": ["data/gold/quality_kpis.parquet"],
        "kpis": ["Environmental Compliance", "Air Quality Index"]
    },
    "runway": {
        "gold": ["data/gold/safety_kpis.parquet"],
        "kpis": ["Runway Availability", "Weather Hold Rate"]
    },
    "security": {
        "gold": ["data/gold/safety_kpis.parquet"],
        "kpis": ["Alert Resolution Rate", "Avg Response Time"]
    }
}
```

## Key Functions

### `get_lineage_for_stream(stream: str) → dict`
Returns full lineage path with existence flags and file/row counts.
- **Returns:** `{bronze: {path, exists, file_count}, silver: {path, exists, row_count}, gold: [{path, exists}], kpis: [...]}`
- **Used by:** Data Lineage page

### `get_impact_analysis(stream: str) → dict`
Identifies downstream impact if a stream fails.
- **Returns:** `{severity, affected_gold_tables, affected_kpis, shared_dependencies}`
- **Severity:** Critical (≥3 affected KPIs), High (2), Medium (1), Low (0)
- **Used by:** Data Lineage (impact section), AI Ops Center (context builder)

### `get_reverse_lineage(kpi_name: str) → list`
Traces a KPI back to its source streams.
- **Returns:** List of `{kpi, gold_table, silver_table, bronze_source, stream}`
- **Used by:** Data Lineage (reverse lineage section)

### `get_sankey_data() → dict`
Builds Sankey diagram data for B→S→G flow visualization.
- **Returns:** `{sources, targets, values, labels}`
- **Used by:** Data Lineage (Sankey chart)

## Interview Questions

1. **Q: Why is the lineage model declarative (hardcoded) instead of auto-discovered?**
   A: For a POC, declarative is faster and deterministic. In production, you'd use OpenLineage or Apache Atlas to auto-capture lineage from pipeline execution. The declarative model demonstrates the concept without infrastructure overhead.

2. **Q: How does impact analysis help in incident response?**
   A: When a stream fails, impact analysis immediately shows which KPIs become unreliable. This prioritizes remediation — a flights failure affecting 3 KPIs gets fixed before a cargo failure affecting 1 KPI. The AI Ops Center uses this for its "What's Impacted?" section.
