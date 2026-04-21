# Miracles — Things To Do & Next Steps

---

## 🔧 POC: Streamlit IoT/Pipeline Analytics Dashboard

### Concept
Build a **Streamlit application** that visualizes real-time IoT data, stream analytics, and pipeline logs — with an **AI model integrated** to recommend improvements to throughput, framework, and pipeline performance.

### Features
- **Stream Analytics Visualization** — real-time event flow, latency trends, error rates
- **IoT Data Dashboard** — biometric streams, device health, anomaly detection
- **Pipeline Logs Viewer** — ETL run history, success/failure, duration trends
- **AI Recommendations Engine** — model analyzes metrics and suggests:
  - How to improve throughput
  - Pipeline bottleneck identification
  - Framework optimization suggestions

### KPIs & Metrics to Identify
- **Uptime ratio** — % of time services are healthy
- **P95/P99 latency** — tail latency trends
- **Throughput** — events/sec, records processed/hour
- **Error rate** — % of failed requests/pipeline runs
- **Pipeline duration** — ETL run time trends, regression detection
- **Resource utilization** — CPU/memory efficiency
- **Deflection rate** — (for RAG) queries answered vs. escalated
- **Data quality score** — % records passing validation
- **Cost per query/pipeline run** — cloud spend efficiency

### Tech Stack
- **Frontend**: Streamlit
- **Data**: Simulated IoT/telemetry events (or connect to real Event Hub/Kusto)
- **AI Model**: LLM-powered recommendations (Azure OpenAI or Claude API)
- **Visualizations**: Plotly, Altair

### 💡 Tip
- Use **claude.ai** for building this — better visuals and UI/UX generation
- Claude can help with Streamlit layout, Plotly chart configs, and AI prompt engineering for the recommendation engine

---

## 📋 Other Next Steps

- [ ] Continue adding Q&As to `FinalDayJobRevision/01_QA_Revision.md` as interview prep progresses
- [ ] Refine interview pitch if role-specific adjustments needed
- [ ] Mock interview practice sessions
- [ ] Build the Streamlit POC (use claude.ai)

---
