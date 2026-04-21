# AI Ops Center

> File: `app/pages/5_AI_Ops_Center.py`

## Overview

The AI Ops Center is the intelligent diagnostics layer — it uses LLM integration (Claude API or Ollama) to analyze system health, diagnose issues, recommend actions, and answer questions grounded in live operational data. It bridges the gap between raw metrics and actionable insights.

**Supporting files:** `ai/claude_client.py` (LLM abstraction), `ai/context_builder.py` (grounding context assembly), `utils/kpi_calculator.py` (KPI data), `utils/lineage.py` (impact data)

## Metrics & Features

### System Status Banner

| Severity | Condition | Color |
|----------|-----------|-------|
| 🔴 Critical | anomaly_count ≥3 OR success_rate <90% OR warning_kpis ≥4 | Red (#E74C3C) |
| 🟡 Warning | anomaly_count ≥1 OR success_rate <99% OR warning_kpis ≥1 | Yellow (#F1C40F) |
| 🟢 Healthy | None of the above | Green (#2ECC71) |

Source: `ai/context_builder.py` → `build_ai_context()`

### System Diagnosis
- **Trigger:** "Generate System Diagnosis" button
- **Function:** `ClaudeClient.diagnose(context)` — prompt_type: "diagnose"
- **Input:** Full operational context (pipeline health, KPIs, anomalies, quality issues, lineage impact)
- **Output:** Markdown-formatted diagnosis covering all system areas

### Incident Analysis (4 Expandable Sections)

| Section | Content | Data Source |
|---------|---------|-------------|
| **What Changed?** | Anomaly count, recent failures (stream, stage, quality score, records) | `context["anomalies"]` |
| **What Broke?** | Pipeline success rate, quarantined records per stream, top failure reasons | `context["quality_issues"]` |
| **What's Impacted?** | Warning/critical KPIs, affected Gold tables, affected KPIs per stream | `context["lineage_impact"]`, `context["kpi_summary"]` |
| **Recommended Actions** | AI-generated remediation steps via `ClaudeClient.recommend(context)` | LLM output |

### Chat Interface
- **6 Suggested Queries:** System health, quality issues, KPIs at risk, pipeline failures, anomalies, sensor status
- **Free-form Input:** Bottom-docked chat input
- **Context Grounding:** All responses use `build_ai_context()` for factual grounding
- **Chat History:** Persisted in `st.session_state.chat_messages`
- **New Conversation:** Button appears after first exchange

### Context Panel
- **Expander:** "Show Context Sent to AI" (hidden until chat history exists)
- **Tabs:** Formatted Text (human-readable) | Raw JSON
- Source: `ai/context_builder.py` → `format_context_for_prompt(context)`

## Purpose & Inference

| Feature | Purpose | What to Infer |
|---------|---------|---------------|
| System Status | Instant health assessment | Red = immediate attention needed; check incident sections for details |
| Diagnosis | Comprehensive system analysis | LLM synthesizes across all data streams — catches correlations humans might miss |
| What Changed? | Recent anomaly detection | High anomaly count after failure injection validates the detection pipeline |
| What Broke? | Root cause identification | Links quarantine spikes to specific failure reasons and streams |
| What's Impacted? | Blast radius assessment | Shows downstream KPI impact — critical for prioritizing fixes |
| Recommendations | Actionable remediation | LLM suggests specific steps based on the actual system state |
| Chat | Interactive exploration | Ask follow-up questions; context-grounded so answers reference real data |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/gold/flight_kpis.parquet` | Gold | `build_ai_context()` → `_get_kpi_summary()` | Flight KPIs for context |
| `data/gold/passenger_kpis.parquet` | Gold | `build_ai_context()` → `_get_kpi_summary()` | Passenger KPIs for context |
| `data/gold/quality_kpis.parquet` | Gold | `build_ai_context()` → `_get_kpi_summary()` | Quality scores for context |
| `data/gold/safety_kpis.parquet` | Gold | `build_ai_context()` → `_get_kpi_summary()` | Safety KPIs for context |
| `data/logs/pipeline_logs.parquet` | Logs | `build_ai_context()` → `_get_pipeline_health()`, `_get_anomalies()` | Pipeline status, failures |
| `data/logs/alerts.parquet` | Logs | `build_ai_context()` → `_get_recent_alerts()` | Recent alert entries |
| `data/quarantine/*.parquet` | Quarantine | `build_ai_context()` → `_get_quality_issues()` | Quarantine counts and failure reasons |
| `data/logs/ai_metrics.json` | Logs | `_log_ai_metric()` (write) | AI call metrics (latency, tokens, cost) |

**Write operations:** Appends to `data/logs/ai_metrics.json` on every LLM call (diagnose, recommend, chat)

## Interview Pitch

*"The AI Ops Center demonstrates RAG (Retrieval-Augmented Generation) in an operational context. Instead of asking an LLM generic questions, we ground every response in live system data — pipeline health, quality scores, anomalies, and lineage impact. The context builder assembles this data, and the LLM interprets it. So when it says 'runway stream has a schema drift issue,' it's reading actual quarantine data showing range violations on wind_speed. The incident analysis follows the SRE framework: What Changed → What Broke → What's Impacted → Recommended Actions."*

## Interview Questions

1. **Q: How do you prevent LLM hallucination in operational diagnostics?**
   A: Context grounding — we assemble factual system data (pipeline status, quality scores, anomalies) and pass it with every prompt. The system prompt instructs the LLM to only reference provided data. The "Show Context Sent to AI" panel lets users verify what data the LLM received.

2. **Q: Why not just show dashboards instead of using an LLM?**
   A: Dashboards show individual metrics; the LLM correlates across them. A human might miss that a runway quality drop + environmental compliance warning + increased flight delays are all caused by the same weather event. The LLM connects these dots in natural language.

3. **Q: How does the backend fallback work?**
   A: `ClaudeClient.__init__()` checks for `ANTHROPIC_API_KEY` first (cloud Claude). If unavailable, checks if Ollama is running on localhost:11434. If neither is available, the page shows a graceful warning. This enables local development without API costs.

4. **Q: What's the cost model for LLM usage?**
   A: Haiku: $0.80/$4.00 per 1M input/output tokens. Sonnet: $3.00/$15.00. Ollama: $0.00 (local). The AI Performance Monitor tracks actual cost per call. For this POC, a typical diagnosis costs ~$0.005.

5. **Q: How would you scale this for a production SOC (Security Operations Center)?**
   A: Add streaming context updates (not just on-demand), alert-triggered automatic diagnosis, runbook integration for recommended actions, and role-based access to limit who can trigger LLM calls.
