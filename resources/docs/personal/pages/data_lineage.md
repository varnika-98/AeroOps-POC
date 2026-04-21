# Data Lineage & Governance

> File: `app/pages/4_Data_Lineage.py`

## Overview

Data Lineage provides data governance visibility — tracing data flow from Bronze sources through Silver transformations to Gold KPIs. It includes impact analysis, quality rules catalogue, quarantine inspection, reverse lineage, and data classification. This is the governance and compliance layer of the platform.

**Supporting files:** `utils/lineage.py` (LINEAGE_MODEL, impact analysis, Sankey data), `pipeline/quality_rules.py` (QUALITY_RULES), `utils/charts.py` (sankey)

## Metrics & Sections

### Sankey Flow Diagram
- Visualizes data movement: Bronze sources → Silver tables → Gold KPIs
- Node sizes proportional to record volumes
- All 6 streams represented with their full lineage paths
- Source: `utils/lineage.py` → `get_sankey_data()`

### Impact Analysis (per selected stream)

| Field | Description |
|-------|-------------|
| **Severity** | Critical, High, Medium, Low — based on number of affected Gold tables |
| **Affected Gold Tables** | Which parquet files would be impacted |
| **Affected KPIs** | Which dashboard KPIs would show stale/incorrect data |
| **Shared Dependencies** | Other streams that feed the same Gold tables |

Source: `utils/lineage.py` → `get_impact_analysis(stream)`

### Quality Rules Catalogue

| Column | Description |
|--------|-------------|
| Stream | Data stream name |
| Rule Name | Descriptive rule identifier |
| Field | Column being validated |
| Type | `range`, `enum`, `regex`, `not_null` |
| Criteria | Validation bounds/values |
| Status | ✅ Passing / ❌ Failing (based on quarantine presence) |

Source: `pipeline/quality_rules.py` (QUALITY_RULES dict)

### Quarantine Inspector
- Per-stream quarantined record count
- Failure reason breakdown
- Expandable full record view
- Source: `quarantine/{stream}_quarantine.parquet`

### Reverse Lineage
Traces a Gold KPI back to its source: **KPI** ← Gold table ← Silver table ← Bronze source (Stream)

### Data Classification Tags

| Stream | Tags |
|--------|------|
| flights | Operational, PII |
| passengers | Operational, PII |
| cargo | Operational, Commercial |
| environmental | Operational, Regulatory |
| runway | Operational, Safety |
| security | Security, PII, Regulatory |

**Tag Colors:** Operational (Sky Blue), PII (Red), Commercial (Green), Regulatory (Navy), Safety (Orange), Security (Yellow)

## Purpose & Inference

| Section | Purpose | What to Infer |
|---------|---------|---------------|
| Sankey Diagram | End-to-end data flow visibility | Thin flows indicate low throughput; missing connections indicate pipeline failures |
| Impact Analysis | Change management risk assessment | Before modifying a stream, see all downstream effects |
| Quality Rules | Governance documentation | Which validations protect each stream; useful for compliance audits |
| Quarantine Inspector | Root cause drill-down | See exact records that failed and why |
| Reverse Lineage | KPI traceability | If a KPI looks wrong, trace it back to the source data |
| Data Classification | Compliance tagging | PII-tagged streams need special handling (encryption, access control) |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/bronze/{stream}/*.json` | Bronze | `get_lineage_for_stream()` | File count per stream (existence check) |
| `data/silver/{stream}.parquet` | Silver | `get_lineage_for_stream()` | Row count per stream (existence check) |
| `data/gold/*.parquet` | Gold | `get_lineage_for_stream()` | Existence check for lineage completeness |
| `data/quarantine/{stream}_quarantine.parquet` | Quarantine | Quarantine inspector | Failed records with tagged reasons |

**Lineage model source:** `utils/lineage.py` → `LINEAGE_MODEL` (hardcoded mapping, not derived from data)

**Write operations:** None (read-only page)

## Interview Pitch

*"Data Lineage is our governance layer. The Sankey diagram gives stakeholders a visual map of how raw sensor data becomes executive KPIs. The impact analysis is key for change management — before we modify the runway stream's schema, we can see it affects safety_kpis and 3 dashboard metrics. Reverse lineage works the other direction: if Flight OTP looks wrong, trace it back through Gold → Silver → Bronze to the raw sensor data. The data classification tags demonstrate awareness of PII and regulatory requirements."*

## Interview Questions

1. **Q: How does the lineage model work technically?**
   A: It's a declarative dictionary mapping each stream to its Bronze directory, Silver parquet, Gold outputs, and associated KPIs. Functions traverse this model to compute impact (forward) and trace (reverse) lineage. In production, you'd use Apache Atlas or OpenLineage for automated tracking.

2. **Q: Why is impact analysis important in data engineering?**
   A: When you modify a data source or transformation, you need to know what breaks downstream. Our impact analysis shows that changing the flights stream affects flight_kpis.parquet, which feeds Flight OTP, Avg Delay, and Gate Utilization KPIs. Without this, changes cause silent data quality degradation.

3. **Q: How would you implement automated lineage tracking?**
   A: Instrument each pipeline stage to emit lineage events (OpenLineage standard) — what was read, what was written, what transformations applied. Store in a lineage graph database. Our declarative model is the lightweight version of this concept.

4. **Q: What's the significance of data classification tags?**
   A: They indicate regulatory requirements — PII data (passengers, security) needs encryption at rest and access controls under GDPR/CCPA. Regulatory data (environmental) needs audit trails. Classification drives security policy enforcement.
