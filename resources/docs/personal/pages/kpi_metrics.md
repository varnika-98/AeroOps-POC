# KPI Metrics & Data Quality

> File: `app/pages/3_KPI_Metrics.py`

## Overview

KPI Metrics provides comprehensive data quality monitoring — per-stream quality gauges, schema validation rates, quarantine analysis, table freshness, and environmental regulatory compliance. It's the data governance dashboard that ensures data trustworthiness before downstream consumption.

**Supporting files:** `utils/kpi_calculator.py` (`get_data_quality_scores`, `get_environmental_compliance`), `utils/charts.py` (gauge), `pipeline/quality_rules.py` (validation ruleset)

## Metrics

### Data Quality Gauges (6 streams)

| Stream | Gauge Range | Thresholds | Data Source |
|--------|-------------|------------|-------------|
| **Flights** | 0-100% | 🟢 ≥95% · 🟡 ≥85% · 🔴 <85% | `gold/quality_kpis.parquet` |
| **Passengers** | 0-100% | 🟢 ≥95% · 🟡 ≥85% · 🔴 <85% | `gold/quality_kpis.parquet` |
| **Cargo** | 0-100% | 🟢 ≥95% · 🟡 ≥85% · 🔴 <85% | `gold/quality_kpis.parquet` |
| **Environmental** | 0-100% | 🟢 ≥95% · 🟡 ≥85% · 🔴 <85% | `gold/quality_kpis.parquet` |
| **Runway** | 0-100% | 🟢 ≥95% · 🟡 ≥85% · 🔴 <85% | `gold/quality_kpis.parquet` |
| **Security** | 0-100% | 🟢 ≥95% · 🟡 ≥85% · 🔴 <85% | `gold/quality_kpis.parquet` |

### Schema Validation Rate (Bar Chart)
- Per-stream validation rate with conditional coloring: Green ≥95%, Yellow 85-94%, Red <85%
- Source: `gold/quality_kpis.parquet`

### Quarantine Analysis
- **Left:** Quarantined records count per stream (from `quarantine/{stream}_quarantine.parquet`)
- **Right:** Top failure reasons extracted from `_quarantine_reasons` column

### Gold Table Freshness

| Status | Age | Indicator |
|--------|-----|-----------|
| 🟢 Fresh | <5 minutes | Data is current |
| 🟡 Stale | 5-15 minutes | Pipeline may need to run |
| 🔴 Outdated | ≥15 minutes | Data is stale, pipeline hasn't run recently |

Source: File modification timestamps of `gold/*.parquet`

### Environmental Compliance
- **Gauge:** Compliance % (0-100), thresholds same as quality gauges
- **Bounds Table:**

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| temperature_c | -10 | 50 | °C |
| humidity | 0 | 100 | % |
| co2 | 200 | 5000 | ppm |
| aqi | 0 | 500 | index |

Source: `silver/environmental.parquet` validated against bounds

### KPI Summary Table

| KPI | Green | Yellow | Red | Icon |
|-----|-------|--------|-----|------|
| Pipeline Success Rate | >95% | >85% | ≤85% | ✅/⚠️/❌ |
| Data Quality (per stream) | >95% | >85% | ≤85% | ✅/⚠️/❌ |
| Flight OTP | >90% | >80% | ≤80% | ✅/⚠️/❌ |
| Checkpoint Efficiency | >90% | >80% | ≤80% | ✅/⚠️/❌ |
| Safety Alert Resolution | >95% | >85% | ≤85% | ✅/⚠️/❌ |
| Environmental Compliance | >95% | >85% | ≤85% | ✅/⚠️/❌ |

## Purpose & Inference

| Metric | Purpose | What to Infer |
|--------|---------|---------------|
| Quality Gauges | Per-stream data health | A single red stream with others green points to stream-specific issue (sensor, schema) |
| Validation Rate | Schema conformance tracking | Low rate means incoming data structure has changed — possible schema drift |
| Quarantine Count | Data loss quantification | High quarantine = data consumers are missing records; check failure reasons |
| Failure Reasons | Root cause identification | "range_violation" on runway wind_speed = schema drift scenario; "not_null" on passengers = sensor outage |
| Table Freshness | Pipeline recency | Outdated tables mean pipeline hasn't run; stale means it ran but not recently |
| Environmental Compliance | Regulatory adherence | <95% means sensor readings outside regulatory bounds — may trigger regulatory action |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/gold/quality_kpis.parquet` | Gold | `get_data_quality_scores()` | Per-stream: quality_score, validation_rate_pct, compliance_pct |
| `data/gold/flight_kpis.parquet` | Gold | KPI summary table | OTP%, delay for summary row |
| `data/gold/passenger_kpis.parquet` | Gold | KPI summary table | Checkpoint efficiency for summary row |
| `data/gold/safety_kpis.parquet` | Gold | KPI summary table | Alert resolution rate for summary row |
| `data/gold/*.parquet` | Gold | Freshness monitor | File modification timestamps (all Gold tables) |
| `data/quarantine/{stream}_quarantine.parquet` | Quarantine | Quarantine analysis | Invalid records with `_quarantine_reasons` JSON column |
| `data/silver/environmental.parquet` | Silver | Compliance checker | temperature_c, humidity, co2, aqi readings |

**Write operations:** None (read-only page)

## Interview Pitch

*"This page is our data governance layer. The 6 quality gauges give instant per-stream health. What's unique is the quarantine analysis — we don't just drop bad records, we quarantine them with tagged failure reasons. So when the runway quality gauge drops to 60%, I can see it's all 'range_violation' on wind_speed, immediately pointing to the schema drift injection. The freshness monitor ensures downstream consumers know if they're looking at current data."*

## Interview Questions

1. **Q: Why quarantine instead of dropping invalid records?**
   A: Quarantined records preserve evidence for root cause analysis. If 500 runway records fail range validation, we can inspect them, find that wind_speed was multiplied by 4×, and trace it to the schema drift injection. Dropped records would leave us guessing.

2. **Q: How do you define "data quality" — what's in that score?**
   A: Quality score = (passed_records / total_records) × 100 for each stream. "Passed" means a record satisfies all quality rules — regex patterns, range bounds, enum values, and not-null constraints defined in `quality_rules.py`.

3. **Q: What's the significance of environmental compliance in an airport?**
   A: Airports must meet regulatory standards for air quality, temperature, and CO2 levels. Our compliance metric checks sensor readings against regulatory bounds. Below 95% means we're out of compliance — in production this would trigger HVAC adjustments or regulatory notifications.

4. **Q: How would you handle evolving quality rules?**
   A: Quality rules are defined in a central `QUALITY_RULES` dictionary. Adding a new rule means adding an entry and re-processing Silver. Since Bronze preserves raw data, we can re-validate historical data against updated rules without re-ingesting.
