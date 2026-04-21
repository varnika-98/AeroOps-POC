# context_builder.py

> File: `ai/context_builder.py`

## Overview

RAG (Retrieval-Augmented Generation) data layer — reads live operational data from Gold, Silver, Logs, and Quarantine layers to assemble structured context for LLM prompts. This ensures AI responses are grounded in actual system metrics rather than hallucinated.

## Purpose

- **Data grounding** — LLM responses reference real KPIs, not fabricated values
- **Threshold evaluation** — Compares current values against operational targets, labels healthy/warning
- **Anomaly detection** — Identifies pipeline failures and quality score drops
- **Impact tracing** — Connects failures to downstream KPI impact via lineage
- **Token efficiency** — Formats context as compact text, not raw data dumps

## Data Dependencies

| Data File | Function | What It Extracts |
|-----------|----------|-----------------|
| `data/logs/pipeline_logs.parquet` | `_get_pipeline_health()` | Total runs, success rate, per-stream breakdown, avg duration |
| `data/gold/flight_kpis.parquet` | `_get_kpi_summary()` | OTP%, avg delay → compare against 80% target |
| `data/gold/passenger_kpis.parquet` | `_get_kpi_summary()` | Throughput, wait time → compare against 2000 pax/hr, 15 min |
| `data/gold/quality_kpis.parquet` | `_get_kpi_summary()` | Validation rate → compare against 95% target |
| `data/gold/pipeline_kpis.parquet` | `_get_kpi_summary()` | Pipeline quality % → compare against 99% target |
| `data/gold/safety_kpis.parquet` | `_get_kpi_summary()` | Response time → compare against 120s target |
| `data/quarantine/*.parquet` | `_get_quality_issues()` | Quarantine counts, top failure reasons per stream |
| `data/logs/pipeline_logs.parquet` | `_get_anomalies()` | Records with quality_score < 1.0 (Silver stage only) |
| `data/logs/alerts.parquet` | `_get_recent_alerts()` | Last 20 alerts sorted by severity |

## KPI Threshold System

```python
KPI_THRESHOLDS = {
    "pipeline_success_rate":     {"target": 99.0,  "unit": "%",      "direction": "above"},
    "data_quality_score":        {"target": 95.0,  "unit": "%",      "direction": "above"},
    "flight_otp":                {"target": 80.0,  "unit": "%",      "direction": "above"},
    "passenger_throughput":      {"target": 2000,  "unit": "pax/hr", "direction": "above"},
    "avg_security_wait":         {"target": 15,    "unit": "min",    "direction": "below"},
    "safety_incident_response":  {"target": 120,   "unit": "sec",    "direction": "below"},
    "environmental_compliance":  {"target": 95.0,  "unit": "%",      "direction": "above"},
}
```

**Evaluation logic:**
- `direction: "above"` → healthy if value ≥ target
- `direction: "below"` → healthy if value ≤ target

## Key Functions

### `build_ai_context() → dict`
Main assembler — calls all internal functions and merges results:
```python
{
    "timestamp": "2026-04-20T16:30:00",
    "airport": "AeroOps International Airport (AOP)",
    "pipeline_health": {...},    # From _get_pipeline_health()
    "kpi_summary": {...},        # From _get_kpi_summary()
    "quality_issues": {...},     # From _get_quality_issues()
    "anomalies": {...},          # From _get_anomalies()
    "recent_alerts": [...],      # From _get_recent_alerts()
    "lineage_impact": {...}      # From utils/lineage.get_impact_analysis()
}
```

### `format_context_for_prompt(context: dict) → str`
Renders context into compact text with sections:
```
Timestamp: 2026-04-20T16:30:00

=== PIPELINE HEALTH ===
Runs: 12, Success: 85.71%, Avg duration: 2.3s
  flights: 100.0% (2 runs)
  runway: 50.0% (2 runs)

=== KPIs ===
  ✅ flight_otp: 87.5 % (target: 80.0 %)
  ⚠️ data_quality_score: 89.2 % (target: 95.0 %)

=== QUALITY ISSUES ===
  runway_quarantine: 320 quarantined

=== ANOMALIES (2) ===
  runway/silver: quality=0.7407, failed=320/1200

=== IMPACT ===
  runway → KPIs: Runway Availability, Weather Hold Rate
```

### `_safe_read_parquet(path: str) → pd.DataFrame | None`
Safe file reader — returns None if file missing or corrupt. Prevents crashes from missing data.

## How Context Flows to LLM

```
build_ai_context()
    │  Reads 8+ data files
    ▼
format_context_for_prompt(context)
    │  Renders ~500-1500 chars of structured text
    ▼
CHAT_PROMPT.format(context=text, question=user_query)
    │  Injects context into prompt template
    ▼
claude_client.messages.create(system=SYSTEM_PROMPT, messages=[...])
    │  LLM sees: system prompt + grounded context + user question
    ▼
Response references actual metrics from context
```

## Interview Q&A

1. **Q: What is context grounding and why is it critical for operational AI?**
   A: LLMs hallucinate — they generate plausible but incorrect information. In an airport operations context, hallucinated metrics could lead to wrong decisions. Context grounding provides the LLM with actual current data so when it says "runway quality is at 74%," that number comes from the context, not its training data.

2. **Q: How do you keep context size manageable?**
   A: Three strategies: (1) Read pre-aggregated Gold tables (50 rows), not raw Silver (60,000 rows). (2) `format_context_for_prompt` outputs summaries, not full DataFrames. (3) Alerts limited to 20, anomalies to 10. Typical context is 500-1500 chars (~300-800 tokens), well within Haiku's 200K context window.

3. **Q: Why evaluate KPIs against thresholds before sending to the LLM?**
   A: Pre-evaluation (healthy/warning labels) gives the LLM structured signals instead of asking it to interpret raw numbers. The LLM can immediately focus on warning KPIs rather than guessing what's "normal" for airport throughput. It also reduces prompt engineering complexity.

4. **Q: How does lineage impact get computed?**
   A: `build_ai_context` checks which streams have anomalies, then calls `get_impact_analysis(stream)` from `utils/lineage.py` for each affected stream. This tells the LLM which downstream KPIs are unreliable — e.g., "runway failure → Runway Availability and Weather Hold Rate KPIs affected."

5. **Q: What happens if all data files are missing (fresh deployment)?**
   A: Every reader function handles missing files gracefully — returns None, empty dict, or "no_data" status. `format_context_for_prompt` only includes sections with actual data. The LLM receives minimal context and responds appropriately: "No pipeline data available yet."
