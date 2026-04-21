# AeroOps POC — Future Scope

> Items identified for future development beyond the current POC scope.
> Each item includes context, implementation approach, and acceptance criteria so it can be picked up independently.

---

## 1. P95/P99 Latency Metrics

**Current State:** The dashboard displays average pipeline stage durations and average processing latency. Percentile-based latency metrics (P95, P99) are not computed or visualized.

**Why It Matters:** Average latency hides tail-end performance issues. A pipeline that averages 2 seconds but has a P99 of 30 seconds is unreliable for time-sensitive airport operations (e.g., security screening throughput, flight boarding gates). P95/P99 metrics are the industry standard for SLA compliance reporting.

**Implementation Approach:**
- Add `numpy.percentile()` calculations to `utils/kpi_calculator.py` for each pipeline stage duration.
- Compute P50 (median), P95, and P99 from `duration_seconds` in `pipeline_logs.parquet`, grouped by stage and stream.
- Add a latency distribution chart (histogram or box plot) to the Pipeline Health page showing the spread.
- Add P95/P99 KPI cards to the KPI Metrics page alongside existing averages.
- Store percentile values in a new gold table (`data/gold/latency_percentiles.parquet`).

**Acceptance Criteria:**
- P50, P95, P99 latency values displayed per pipeline stage (bronze, silver, gold).
- Latency distribution visualization available on Pipeline Health page.
- Gold layer stores pre-computed percentile aggregates.

---

## 2. Resource Utilization Monitoring

**Current State:** No CPU, memory, disk, or network metrics are captured or displayed. The dashboard focuses on data pipeline metrics only.

**Why It Matters:** In a production airport environment, resource exhaustion (CPU spikes during peak hours, disk full from bronze append-only writes, memory pressure from large parquet reads) can silently degrade pipeline performance before any data quality issue appears. Proactive resource monitoring prevents outages.

**Implementation Approach:**
- Integrate the `psutil` Python library to capture system-level metrics: CPU %, memory %, disk usage, and network I/O.
- Capture metrics at each pipeline run (start and end) and log to `data/logs/resource_metrics.parquet`.
- Add a "System Resources" section to the Pipeline Health or Command Center page with:
  - Real-time CPU and memory gauges.
  - Disk usage trend (important for bronze append-only growth).
  - Historical resource usage correlated with pipeline run times.
- Optionally simulate resource metrics in the simulator for demo purposes (since the POC runs locally, real metrics may be minimal).

**Acceptance Criteria:**
- CPU, memory, and disk metrics captured per pipeline run.
- Resource metrics visualized on the dashboard with trend lines.
- Alerts surfaced when resource usage exceeds configurable thresholds (e.g., disk > 80%).

---

## 3. Deflection Rate Tracking (RAG Chatbot)

**Current State:** The AI Ops Center provides a Claude-powered chatbot that answers questions grounded in live pipeline data. However, there is no concept of escalation to a human operator — the chatbot always responds, and there is no tracking of whether the response was sufficient or if the user needed human intervention.

**Why It Matters:** Deflection rate (percentage of queries resolved by AI without human escalation) is a key KPI for any AI assistant deployment. Without it, there is no way to measure the chatbot's effectiveness or identify topics where it consistently fails, which is critical for continuous improvement and ROI justification.

**Implementation Approach:**
- Add a feedback mechanism to the chat UI: after each AI response, present a "Was this helpful?" prompt (thumbs up/down or a small rating widget).
- Add an "Escalate to Human" button that logs the query, AI response, and escalation reason to `data/logs/escalation_log.parquet`.
- Compute deflection rate as: `(total_queries - escalated_queries) / total_queries * 100`.
- Track metrics over time: deflection rate trend, most-escalated topics, average confidence score of deflected vs. escalated queries.
- Add a "Chatbot Effectiveness" section to the AI Performance Monitor page showing deflection rate, escalation reasons breakdown, and improvement trends.

**Acceptance Criteria:**
- User feedback captured after each AI response (helpful yes/no).
- Escalation path exists with reason logging.
- Deflection rate KPI displayed on AI Performance Monitor page.
- Escalation topic analysis available for identifying improvement areas.

---

## 4. SLA Definitions and Data Contracts

**Current State:** The pipeline has quality rules (42 validation rules in `quality_rules.py`) and logs pipeline durations, but there are no formal Service Level Agreements (SLAs) or data contracts defining expected data freshness, quality thresholds, or delivery guarantees between pipeline stages.

**Why It Matters:** In a production airport DataOps environment, data consumers (dashboards, AI models, operational systems) depend on data being delivered within specific time windows and quality levels. Without formal SLAs and data contracts:
- There is no agreed definition of "on time" for data delivery.
- Quality degradation has no threshold that triggers action.
- Upstream schema changes can break downstream consumers silently.

**Implementation Approach:**
- **SLA Configuration:** Create a `pipeline/sla_config.py` defining SLAs per stage and stream:
  - Freshness SLA: e.g., "Bronze data must be ingested within 5 minutes of event generation."
  - Quality SLA: e.g., "Silver validation pass rate must be ≥ 95% per stream."
  - Duration SLA: e.g., "Full Bronze→Gold pipeline must complete within 60 seconds."
- **Data Contracts:** Define schema contracts per stream as versioned JSON schemas in `pipeline/contracts/`:
  - Expected columns, data types, nullable constraints, and valid value ranges.
  - Contract versioning to track schema evolution over time.
  - Contract validation at each pipeline stage boundary (Bronze→Silver, Silver→Gold).
- **SLA Monitoring Dashboard:** Add an SLA Compliance section to Pipeline Health or a dedicated page:
  - SLA breach count and trend over time.
  - Current compliance percentage per SLA.
  - Breach alerts with root cause (which stream, which rule, how far out of SLA).
- **Contract Violation Tracking:** Log contract violations separately from quality rule failures, with breaking vs. non-breaking classification.

**Acceptance Criteria:**
- SLA definitions codified in configuration (not hardcoded).
- SLA compliance tracked and displayed on the dashboard.
- Data contracts defined per stream with version history.
- Contract violations logged and surfaced with severity classification.

---

## 5. Multi-Environment Setup (Dev / Integration / Production)

**Current State:** The POC runs as a single local environment. There is no separation between development, integration testing, and production configurations. All data paths, API keys, and pipeline parameters are shared.

**Why It Matters:** A production airport system requires environment isolation to:
- Safely develop and test new features without affecting live operations.
- Run integration tests with realistic data volumes before promoting changes.
- Maintain separate credentials, data stores, and configurations per environment.
- Support CI/CD promotion workflows (Dev → Int → Prod) with approval gates.

**Implementation Approach:**
- **Environment Configuration:**
  - Create environment-specific config files: `.env.dev`, `.env.int`, `.env.prod`.
  - Add an `APP_ENV` variable that controls which configuration is loaded.
  - Parameterize all paths, API endpoints, model selections, and thresholds per environment.
- **Data Isolation:**
  - Separate data directories per environment: `data/dev/`, `data/int/`, `data/prod/`.
  - Dev uses simulated data (current behavior), Int uses a subset of production-like data, Prod uses live feeds.
- **CI/CD Pipeline Enhancement:**
  - Extend `.github/workflows/ci.yml` with environment-specific stages:
    - Dev: Lint + unit tests + smoke test (current).
    - Int: Full pipeline run with validation against SLA thresholds.
    - Prod: Canary deployment with rollback capability.
  - Add manual approval gates for Int → Prod promotion.
- **Infrastructure as Code:**
  - Dockerize the application for consistent environment parity.
  - Add `docker-compose.yml` with profiles for each environment.
  - Consider Terraform/Bicep templates for cloud resource provisioning.

**Acceptance Criteria:**
- Three distinct environments with isolated configuration and data.
- CI/CD pipeline supports promotion workflow with approval gates.
- Environment parity ensured via containerization.
- No production credentials accessible from dev/int environments.

---

## 6. Data Warehouse Integration with Microsoft Fabric

**Current State:** The POC stores all data as local Parquet files in a medallion architecture (`data/bronze/`, `data/silver/`, `data/gold/`). This works for demonstration but does not scale for production airport data volumes or multi-user concurrent access.

**Why It Matters:** Microsoft Fabric provides a unified analytics platform that combines data engineering, data warehousing, real-time analytics, and Power BI reporting — all on a single SaaS platform with OneLake as the storage layer. For an airport IoT system, this means:
- Scalable storage for high-volume IoT streams (thousands of events/second).
- Lakehouse architecture that natively supports the medallion pattern already in the POC.
- Built-in real-time analytics for streaming airport data.
- Enterprise security, governance, and compliance features.
- Power BI integration for executive dashboards beyond the Streamlit POC.

**Implementation Approach:**
- **OneLake Integration:**
  - Replace local Parquet file writes with OneLake-backed storage using the Azure SDK or Fabric REST APIs.
  - Map existing data layout to Fabric Lakehouse: `bronze/`, `silver/`, `gold/` folders in OneLake.
  - Use Delta Lake format (instead of plain Parquet) for ACID transactions and time travel.
- **Fabric Data Pipeline:**
  - Migrate the Python ETL orchestrator (`pipeline/orchestrator.py`) to Fabric Data Pipelines or Notebooks.
  - Use Fabric Spark for Silver transformations at scale (current pandas logic translates to PySpark).
  - Schedule pipeline runs via Fabric triggers instead of manual invocation.
- **Real-Time Hub:**
  - Connect simulated IoT streams to Fabric Real-Time Hub using Event Streams.
  - Enable real-time KPI computation for latency-sensitive metrics (security queue times, runway status).
- **Power BI Layer:**
  - Create a Power BI semantic model on top of Gold tables for executive reporting.
  - Maintain Streamlit dashboard for operational use; Power BI for strategic/executive use.
- **Migration Path:**
  - Phase 1: Dual-write (local + OneLake) to validate parity.
  - Phase 2: Switch primary storage to OneLake, keep local as cache.
  - Phase 3: Migrate ETL to Fabric-native pipelines.

**Acceptance Criteria:**
- Gold layer data available in Microsoft Fabric Lakehouse.
- At least one pipeline stage running as a Fabric pipeline or notebook.
- Delta Lake format with time travel enabled for audit trails.
- Power BI report connected to Fabric semantic model.

---

## 7. Alerting and Notification System

**Current State:** The dashboard displays anomalies, quality failures, and pipeline issues visually, but there are no proactive alerts or notifications. Users must actively open the dashboard to discover problems — there is no push-based notification mechanism.

**Why It Matters:** In airport operations, delayed awareness of issues has direct safety and operational impact:
- A failed environmental sensor (CO₂ spike) requires immediate facilities response.
- A pipeline failure during peak hours means stale data for security screening decisions.
- Schema drift in a live feed can silently corrupt downstream KPIs if not caught in real time.
- Operations teams need to be notified immediately, not when they next check a dashboard.

**Implementation Approach:**
- **Alert Rule Engine:**
  - Create `pipeline/alert_rules.py` defining alert conditions:
    - Pipeline failure: any stage fails or exceeds duration SLA.
    - Quality breach: validation pass rate drops below threshold (e.g., < 90%).
    - Anomaly detection: environmental readings outside safe ranges.
    - Data freshness: no new data received for a stream within expected interval.
  - Support severity levels: INFO, WARNING, CRITICAL.
  - Make rules configurable via YAML or a config dict (similar to `QUALITY_RULES` pattern).
- **Notification Channels:**
  - **Email:** SMTP integration for critical alerts (e.g., pipeline down, safety threshold breach).
  - **Microsoft Teams / Slack:** Webhook integration for operational alerts with rich cards showing affected stream, metric values, and dashboard deep links.
  - **In-App:** Notification bell/badge on the Streamlit dashboard showing unacknowledged alerts.
  - **SMS (optional):** For CRITICAL safety alerts via Twilio or Azure Communication Services.
- **Alert Management:**
  - Log all alerts to `data/logs/alerts.parquet` with timestamp, rule, severity, message, and acknowledged status.
  - Add an "Alert History" section to the dashboard showing recent alerts with acknowledge/resolve workflow.
  - Implement alert deduplication (don't send the same alert repeatedly) and cooldown periods.
  - Support alert escalation: if a WARNING is not acknowledged within N minutes, escalate to CRITICAL.
- **Integration with AI:**
  - When an alert fires, automatically generate a Claude diagnosis and include it in the notification.
  - This turns alerts from "something is wrong" into "something is wrong and here's the likely cause."

**Acceptance Criteria:**
- At least two notification channels configured and working (e.g., in-app + Teams/email).
- Alert rules defined for pipeline failures, quality breaches, and anomaly detection.
- Alert history logged and viewable on the dashboard.
- Alert deduplication and cooldown logic prevents notification fatigue.
- AI-powered root cause included in critical alert notifications.

---

## Summary

| # | Item                           | Effort   | Priority   |
|---|--------------------------------|----------|------------|
| 1 | P95/P99 Latency Metrics        | Low      | High       |
| 2 | Resource Utilization           | Medium   | Medium     |
| 3 | Deflection Rate (RAG)          | Medium   | Medium     |
| 4 | SLA & Data Contracts           | High     | High       |
| 5 | Multi-Environment (Dev/Int/Prod)| High    | High       |
| 6 | Microsoft Fabric Data Warehouse| High     | High       |
| 7 | Alerting & Notifications       | Medium   | High       |

---

*Document created: April 2025*
*Last updated: April 2025*
