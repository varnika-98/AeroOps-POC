# AeroOps Application Workflow

> How services, pages, and modules interact to deliver the user experience

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Streamlit Application                                │
│                                                                                  │
│  ┌──────────────────┐   ┌────────────────────────────────────────────────────┐  │
│  │   Command Center │   │                    Pages                            │  │
│  │  (Main Entry)    │   │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │                  │   │  │Passenger │ │Pipeline  │ │   KPI    │          │  │
│  │  • System Status │   │  │Analytics │ │ Health   │ │ Metrics  │          │  │
│  │  • Run Pipeline  │   │  └──────────┘ └──────────┘ └──────────┘          │  │
│  │  • Generate Data │   │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  • Inject Faults │   │  │  Data    │ │  AI Ops  │ │   AI     │          │  │
│  │                  │   │  │ Lineage  │ │  Center  │ │ Perf Mon │          │  │
│  └──────────────────┘   │  └──────────┘ └──────────┘ └──────────┘          │  │
│                          └────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          Shared Services                                  │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │   │
│  │  │ theme   │ │ charts  │ │kpi_calc │ │lineage  │ │ claude_client   │  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          Pipeline Engine                                  │   │
│  │  ┌───────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐  │   │
│  │  │  bronze   │ │    silver      │ │     gold       │ │ orchestrator │  │   │
│  │  │ ingestion │ │ transformation │ │  aggregation   │ │              │  │   │
│  │  └───────────┘ └────────────────┘ └────────────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          Simulator                                        │   │
│  │  ┌────────────────┐  ┌──────────────────┐                               │   │
│  │  │ data_generator │  │ failure_injector  │                               │   │
│  │  └────────────────┘  └──────────────────┘                               │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  External Services   │
                              │  • Claude API        │
                              │  • Ollama (local)    │
                              └─────────────────────┘
```

## Application Startup Flow

```
User runs: streamlit run app/Command_Center.py
         │
         ▼
Streamlit discovers pages in app/pages/ (sorted by filename prefix)
         │
         ├── 1_Passenger_Analytics.py
         ├── 2_Pipeline_Health.py
         ├── 3_KPI_Metrics.py
         ├── 4_Data_Lineage.py
         ├── 5_AI_Ops_Center.py
         └── 6_AI_Performance_Monitor.py
         │
         ▼
Command_Center.py executes:
  1. apply_theme(st)           ← Injects CSS, sets page config
  2. Initialize session_state  ← Pipeline status, chat history
  3. Render sidebar            ← Navigation, controls, failure toggles
  4. Load KPIs via kpi_calculator ← Read Gold parquet files
  5. Render main content       ← Status cards, metrics, action buttons
```

## User Workflows

### Workflow 1: Full Pipeline Execution

```
User clicks "Generate Data" (Command Center sidebar)
    │
    ▼
data_generator.generate_all_events(hours=24)
    │  Produces ~60,000 events across 6 streams
    ▼
bronze_ingestion.ingest_to_bronze(stream, events)  ×6 streams
    │  Writes JSON to data/bronze/{stream}/
    ▼
User clicks "Run Pipeline"
    │
    ▼
orchestrator.run_pipeline()
    │
    ├── transform_to_silver("flights")     → silver/flights.parquet
    ├── transform_to_silver("passengers")  → silver/passengers.parquet
    ├── transform_to_silver("cargo")       → silver/cargo.parquet
    ├── transform_to_silver("environmental") → silver/environmental.parquet
    ├── transform_to_silver("runway")      → silver/runway.parquet
    ├── transform_to_silver("security")    → silver/security.parquet
    │
    ├── aggregate_to_gold()                → gold/*.parquet (5 tables)
    │
    └── _append_pipeline_log()             → logs/pipeline_logs.parquet
    │
    ▼
st.rerun() → Dashboard refreshes with new data
```

### Workflow 2: Failure Injection + Diagnosis

```
User toggles "Runway Schema Drift" (Command Center sidebar)
    │
    ▼
data_generator.generate_all_events()
    │
    ▼
failure_injector.inject_schema_drift(runway_events)
    │  wind_speed_kph × 4.0 → exceeds max 200
    ▼
bronze_ingestion → Run Pipeline → Silver/Quarantine split
    │
    ▼
User navigates to "AI Ops Center"
    │
    ▼
User clicks "Generate System Diagnosis"
    │
    ▼
context_builder.build_ai_context()
    │  Reads: Gold KPIs, pipeline logs, quarantine, alerts
    │  Detects: runway quality_score dropped, high quarantine count
    ▼
claude_client.diagnose(context)
    │  Sends context + system prompt to LLM
    │  Logs: latency, tokens, cost → ai_metrics.json
    ▼
LLM Response: "Runway stream experiencing schema drift on wind_speed_kph.
               320 records quarantined with range_violation.
               Recommend: Check sensor firmware update, validate unit conversion."
    │
    ▼
User navigates to "AI Performance Monitor"
    │  Views: cost of that LLM call, latency, token breakdown
```

### Workflow 3: Interactive AI Chat

```
User opens "AI Ops Center" page
    │
    ▼
Page renders: suggested queries → chat input → context panel (hidden until history)
    │
    ▼
User clicks starter: "What is the current pipeline health status?"
    │
    ▼
st.session_state["ai_messages"].append({"role": "user", "content": query})
st.rerun()  ← Triggers full page re-render
    │
    ▼
Page detects new user message without assistant reply
    │
    ▼
context_builder.build_ai_context()  ← Assembles current system state
    │
    ▼
claude_client.chat(messages=history, context=context)
    │
    ├── Backend selection: Claude API (if key set) → Ollama (if running) → None
    ├── Send: system prompt + context + full message history
    ├── Receive: streaming response
    └── Log: ai_metrics.json (latency, tokens, cost, prompt_type="chat")
    │
    ▼
st.session_state["ai_messages"].append({"role": "assistant", "content": response})
    │
    ▼
Chat history renders with user message + AI response
Context expander + "New Conversation" button appear
```

### Workflow 4: Data Quality Investigation

```
User sees red quality gauge on Command Center
    │
    ▼
Navigates to "KPI Metrics" page
    │  Sees: per-stream quality scores, quarantine counts
    │  Identifies: runway at 70% (normally 99%)
    ▼
Navigates to "Data Lineage" page
    │  Sees: runway lineage B→S→G with quarantine spike
    │  Impact analysis: "Affects: Runway Availability, Weather Hold Rate KPIs"
    ▼
Navigates to "AI Ops Center"
    │  Asks: "Why is runway quality low?"
    │  AI: "320 records failed wind_speed_range validation.
    │       Values 4× expected range indicate unit conversion issue."
    ▼
User goes back to Command Center
    │  Disables "Schema Drift" toggle
    │  Re-generates data + Re-runs pipeline
    │  Quality restores to 99%
```

### Workflow 5: Performance Monitoring

```
User makes several AI queries (chat, diagnose, recommend)
    │
    │  Each call appends to data/logs/ai_metrics.json:
    │  {timestamp, backend, model, prompt_type, latency_sec,
    │   input_tokens, output_tokens, cost_usd, status}
    │
    ▼
User navigates to "AI Performance Monitor"
    │
    ▼
kpi_calculator.get_ai_kpis()
    │  Reads ai_metrics.json
    │  Computes: total_requests, avg_latency, total_cost,
    │            error_rate, by_prompt_type breakdown
    ▼
Page renders:
    ├── KPI cards: Total Requests, Avg Latency, Total Cost, Error Rate
    ├── Latency by Prompt Type (grouped bar)
    ├── Token Usage by Prompt Type (grouped bar: input vs output)
    ├── Cost Breakdown (pie chart)
    └── Request Timeline (time series)
```

## Module Dependency Graph

```
app/Command_Center.py
    ├── utils/theme.py
    ├── utils/kpi_calculator.py
    ├── utils/charts.py
    ├── simulator/data_generator.py
    ├── simulator/failure_injector.py
    └── pipeline/orchestrator.py
            ├── pipeline/bronze_ingestion.py
            ├── pipeline/silver_transformation.py
            │       └── pipeline/quality_rules.py
            └── pipeline/gold_aggregation.py

app/pages/5_AI_Ops_Center.py
    ├── utils/theme.py
    ├── ai/context_builder.py
    │       └── utils/kpi_calculator.py (partial)
    └── ai/claude_client.py

app/pages/6_AI_Performance_Monitor.py
    ├── utils/theme.py
    ├── utils/kpi_calculator.py (get_ai_kpis)
    └── ai/claude_client.py (load_ai_metrics)
```

## Session State Management

| Key | Type | Used By | Purpose |
|-----|------|---------|---------|
| `pipeline_status` | dict | Command Center | Last run results |
| `data_generated` | bool | Command Center | Whether data exists |
| `failure_scenarios` | dict | Command Center | Active failure toggles |
| `ai_messages` | list[dict] | AI Ops Center | Chat history |
| `ai_context` | dict | AI Ops Center | Last context sent to LLM |

## Error Handling Strategy

| Layer | Error Type | Handling |
|-------|-----------|----------|
| Simulator | Generation failure | Catch + show st.error |
| Bronze | Empty events | Raise ValueError (caller handles) |
| Silver | Per-record validation | Quarantine (never crashes) |
| Gold | Missing Silver file | Skip with 0 rows (graceful) |
| Orchestrator | Per-stream failure | Catch + log + continue others |
| AI Client | API rate limit | Retry with backoff |
| AI Client | No backend available | Show warning, disable AI features |
| KPI Calculator | Missing parquet | Return None (pages show "No data") |

## External Service Integration

### Claude API (Production)
```
Request: POST https://api.anthropic.com/v1/messages
Headers: x-api-key: $ANTHROPIC_API_KEY
Body: {model, max_tokens, system, messages}
Response: {content[0].text, usage.input_tokens, usage.output_tokens}
```

### Ollama (Local Development)
```
Request: POST http://localhost:11434/api/chat
Body: {model, messages, stream: false}
Response: {message.content}
```

## Deployment Configuration

| Setting | Value |
|---------|-------|
| Platform | Streamlit Cloud |
| Entry point | `app/Command_Center.py` |
| Python version | 3.12 |
| Branch | master |
| Dependencies | requirements.txt (streamlit, pandas, plotly, duckdb, anthropic) |

## Interview Pitch

"The application follows a layered architecture with clear separation: Simulator generates realistic IoT data, Pipeline Engine processes it through the medallion pattern, Shared Services provide reusable analytics and styling, and the Streamlit UI renders interactive dashboards. The AI layer demonstrates RAG — the context builder reads live operational data and injects it into LLM prompts so responses are grounded in actual system metrics, not hallucinated. The whole system is self-contained — one `streamlit run` command starts everything, no external databases or message queues required."

## Interview Q&A

1. **Q: How do the pages communicate with each other?**
   A: They don't communicate directly — they share state via `st.session_state` (in-memory) and data via the file system (parquet/JSON). When Command Center runs the pipeline, it writes to data/gold/. When Passenger Analytics loads, it reads from data/gold/. This is loose coupling via shared data stores.

2. **Q: Why Streamlit instead of Flask/React?**
   A: Streamlit is purpose-built for data applications — interactive charts, session state, and auto-refresh come free. A Flask+React app would require: API endpoints, frontend build pipeline, state management library, WebSocket for live updates. Streamlit delivers the same UX in 1/10th the code for a POC. In production, you'd move to a proper frontend for customization and performance.

3. **Q: How does the AI integration work end-to-end?**
   A: Three steps: (1) `context_builder` reads all Gold tables, pipeline logs, and quarantine data to assemble current system state. (2) This context is injected as a system prompt alongside the user's question. (3) `claude_client` routes to the available backend (Claude API or Ollama), sends the request, logs metrics, and returns the response. The LLM never sees raw data — only pre-digested KPIs and anomaly summaries.

4. **Q: What happens on first load with no data?**
   A: Every data reader (`_safe_read`, `_has_silver`, `load_ai_metrics`) handles missing files gracefully — returning None, empty DataFrames, or empty lists. Pages show "No data available" messages. The user generates data via the Command Center sidebar, then runs the pipeline.

5. **Q: How would you add a new dashboard page?**
   A: Create `app/pages/7_New_Page.py` (number prefix controls sidebar order). Import `apply_theme`, call it first. Read from existing Gold tables or add a new Gold computation in `gold_aggregation.py`. Use `charts.py` helpers for visualization. The page automatically appears in the sidebar.

6. **Q: How do you handle concurrent users?**
   A: Streamlit gives each user their own session_state (isolated in-memory). However, the data layer (file system) is shared — if two users run the pipeline simultaneously, they'd overwrite each other's files. For the POC this is acceptable. In production, you'd use user-scoped data directories or a proper database.

7. **Q: What's the cold start experience?**
   A: User opens app → sees empty dashboard with "No data" messages → clicks "Generate Data" (creates Bronze) → clicks "Run Pipeline" (creates Silver + Gold) → dashboard populates. Total time: ~10 seconds. No pre-configuration needed.
