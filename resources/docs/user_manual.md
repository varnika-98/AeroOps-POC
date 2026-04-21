# AeroOps AI — Dashboard User Manual

> A complete guide to every element in the AeroOps AI Smart Airport IoT DataOps dashboard.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Top Bar (Streamlit Controls)](#top-bar-streamlit-controls)
3. [Sidebar Controls](#sidebar-controls)
4. [Command Center (Home Page)](#command-center-home-page)
5. [Passenger Analytics](#passenger-analytics)
6. [Pipeline Health & Logs](#pipeline-health--logs)
7. [KPI Metrics & Data Quality](#kpi-metrics--data-quality)
8. [Data Lineage & Governance](#data-lineage--governance)
9. [AI Ops Center](#ai-ops-center)

---

## Getting Started

### Launching the App

```bash
streamlit run app/Command_Center.py
```

The app opens in your browser (default: `http://localhost:8501`). The **top bar** has Streamlit controls, the **sidebar** on the left contains app controls, and the **main area** shows dashboard content. Use the **navigation menu** on the left to switch between pages.

### First-Time Setup

When you open the app for the first time, there is no data. You will see a blue info box:

> "👋 **Welcome to AeroOps AI!** No data found yet. Click **Generate New Data** in the sidebar to create synthetic airport data and run the full pipeline."

Click **Generate New Data** in the sidebar to populate the dashboard.

---

## Top Bar (Streamlit Controls)

The top-right corner of the app has three built-in Streamlit controls. These are **not part of AeroOps AI** — they are standard Streamlit features present on every Streamlit app.

| Button | What It Does | When to Use |
|--------|-------------|-------------|
| **Deploy** | Opens Streamlit's deployment dialog to publish your app to Streamlit Community Cloud (share.streamlit.io) or other hosting platforms. | Only when you want to deploy the app online for others to access. Not needed for local development or demos. |
| **⟳ Re-run** (Always rerun / Rerun) | Re-executes the entire app script from top to bottom. When you edit source code while the app is running, Streamlit detects the change and shows "Source file changed" — click **Rerun** to apply changes. You can also toggle **"Always rerun"** to auto-refresh on every code change. | After editing any `.py` file while the app is running. Also useful if the dashboard seems stuck or shows stale data. |
| **Clear cache** | Purges all `@st.cache_data` and `@st.cache_resource` cached values. AeroOps AI caches KPI data, quality scores, pipeline health, and parquet reads for performance. Clearing cache forces the app to re-read all data files from disk. | After generating new data or running the pipeline, if the dashboard still shows old numbers. Normally the app clears cache automatically after data generation, but this is a manual fallback. |

### Resetting the Dashboard

To start completely fresh:

1. **Delete the data folder** — run `Remove-Item -Recurse -Force data` (PowerShell) or `rm -rf data` (Mac/Linux) from the project root
2. **Click Clear cache** in the top bar
3. **Click 🔄 Generate New Data** in the sidebar to regenerate everything

---

## Sidebar Controls

The sidebar is visible on every page and contains three sections:

### ⚠️ Failure Scenarios

Three checkboxes that inject real-world data problems into the generated data. Use these **before** clicking "Generate New Data" to test how the pipeline handles failures.

| Checkbox | What It Does | Where You'll See the Impact |
|----------|-------------|----------------------------|
| **Runway Schema Drift** | Multiplies runway wind speed values by 1.6×, pushing them beyond the valid 0–200 kph range | KPI Metrics → quarantined runway records; Data Lineage → failing quality rules |
| **Passenger Sensor Outage** | Drops all passenger events from 3 random checkpoints, simulating sensors going offline | Passenger Analytics → gaps in checkpoint data; KPI Metrics → lower passenger quality score |
| **Holiday Traffic Spike** | Generates 3× the normal event volume (~200K events instead of ~66K) | Pipeline Health → longer durations; Command Center → higher record counts |

**Tip:** Toggle one or more, click Generate New Data, then explore the dashboard to see how the system reacts.

---

### 🔧 Pipeline Controls

Two action buttons:

| Button | What It Does |
|--------|-------------|
| **▶️ Run Pipeline** | Executes the Bronze → Silver → Gold pipeline on existing data. Use this to re-process data without regenerating it. Shows a spinner while running, then a success/error message. |
| **🔄 Generate New Data** | Generates fresh synthetic airport data (all 6 IoT streams), applies any selected failure scenarios, ingests to Bronze, and runs the full pipeline. This is the main "refresh everything" button. |

---

### 🔄 Auto Refresh

| Element | What It Does |
|---------|-------------|
| **Refresh interval slider** | Sets how often (10–300 seconds) the dashboard auto-refreshes. Default is 60 seconds. Useful for demo/monitoring mode. |

---

## Command Center (Home Page)

The main landing page providing an at-a-glance overview of the entire airport system.

### 📊 Live Airport Stats (Top Row)

Four metric cards showing key numbers:

| Card | What It Shows | Color Logic |
|------|--------------|-------------|
| **Total Flights Today** | Total number of flight events processed | Always green |
| **Passengers Processed** | Total passenger count from all checkpoints | Always green |
| **Pipeline Success Rate** | Percentage of pipeline runs that succeeded | 🟢 ≥95% · 🟡 ≥80% · 🔴 <80% |
| **Data Quality Score** | Average quality score across all 6 streams | 🟢 ≥90% · 🟡 ≥70% · 🔴 <70% |

---

### 🚦 System Health per Stream

Six cards in a row — one for each IoT stream:

| Stream | Icon | What It Monitors |
|--------|------|-----------------|
| **flights** | ✈️ | Flight schedule, delays, gate assignments |
| **passengers** | 👥 | Checkpoint throughput, wait times |
| **cargo** | 📦 | Baggage/cargo tracking, processing |
| **environmental** | 🌡️ | Temperature, humidity, CO2, air quality |
| **runway** | 🛬 | Runway conditions, wind speed, visibility |
| **security** | 🔒 | Security alerts, severity, response times |

Each card shows:
- **Stream icon** — identifies the data stream
- **Stream name** — e.g., "flights", "passengers"
- **Status indicator** — colored circle: 🟢 Healthy (≥90%) · 🟡 Warning (70–90%) · 🔴 Critical (<70%)
- **Quality percentage** — the validation pass rate for that stream
- **"No data"** — shown with ⚪ if no data exists for that stream yet

---

### 🏅 Medallion Layer Health

A **stacked bar chart** showing record counts at each pipeline layer (Bronze and Silver) per stream.

- **Bronze bars** — raw ingested records (before validation)
- **Silver bars** — validated records that passed quality rules
- The difference between Bronze and Silver = quarantined records

If no data exists, shows: "No medallion data available yet."

---

### 🚨 Recent Alerts (Left Column)

A scrollable feed of the latest 20 security alerts, sorted newest-first.

Each alert shows:
- **Severity badge** — colored label:
  - 🔴 `critical` (red)
  - 🟠 `high` (orange)
  - 🟡 `medium` (yellow)
  - 🔵 `low` (blue)
- **Description** — the alert event type or message
- **Timestamp** — when the alert occurred

---

### 📈 Events Processed per Stream (Right Column)

A **bar chart** showing the number of validated (Silver layer) records per stream. Gives you a quick sense of data volume distribution across streams.

---

## Passenger Analytics

Detailed view of flight operations and passenger flow.

### Top Metrics Row

| Element | Type | What It Shows |
|---------|------|--------------|
| **Flight OTP % (Gauge)** | Circular gauge | On-Time Performance percentage. 🟢 ≥80% · 🟡 ≥60% · 🔴 <60%. The needle shows the current value. |
| **Total Flights** | Metric card | Count of all flight events |
| **Avg Delay (min)** | Metric card | Average delay in minutes. 🟢 ≤10 · 🟡 ≤20 · 🔴 >20 |
| **Passenger Throughput** | Metric card | Average passengers per hour across checkpoints |

---

### 📈 Flight OTP Trend

A **line chart** showing On-Time Performance percentage by hour throughout the day.

- **Red dashed line at 80%** — the OTP target. Hours below this line indicate performance issues.
- **X-axis** — hour of day
- **Y-axis** — OTP percentage

---

### 📊 Delay Distribution (Left)

A **histogram** showing the distribution of flight delay minutes.

- **X-axis** — delay in minutes (0 = on time, negative = early)
- **Y-axis** — number of flights
- 40 bins for granularity
- Helps identify: are most flights on time? Is there a long tail of severe delays?

---

### 🎯 Flight Status Breakdown (Right)

A **pie chart** showing the proportion of flights in each status:

| Status | Meaning |
|--------|---------|
| `scheduled` | Not yet departed |
| `boarding` | Currently boarding passengers |
| `departed` | Left the gate |
| `arrived` | Landed and at gate |
| `delayed` | Behind schedule |
| `cancelled` | Flight cancelled |

---

### 👥 Passenger Flow — Checkpoint Wait Times (Left)

A **horizontal bar chart** showing average wait time per security checkpoint, sorted longest-first.

- **Y-axis** — checkpoint name
- **X-axis** — average wait time in minutes
- Long bars indicate bottlenecks that need attention

---

### Throughput vs Capacity (Right)

A **line chart** showing passenger throughput over time.

- **Green line** — actual throughput per hour
- **Red dashed line at 2,000** — capacity limit
- Points above the red line indicate capacity overload

---

### 📦 Baggage Processing Funnel

A **funnel chart** showing how baggage moves through processing stages:

```
checked_in → in_transit → loaded → delivered
```

- Each stage shows the count of items
- Narrowing between stages = items lost/stuck in process
- A healthy funnel narrows gradually; a steep drop indicates a problem

---

## Pipeline Health & Logs

Monitoring the ETL (Extract-Transform-Load) pipeline performance.

### Top Metrics Row

| Card | What It Shows | Color Logic |
|------|--------------|-------------|
| **Pipeline Success Rate** | % of pipeline runs that completed successfully | 🟢 ≥95% · 🟡 ≥80% · 🔴 <80% |
| **Total Runs** | Number of pipeline executions recorded | Neutral |
| **Avg Duration (sec)** | Average time to process a pipeline run | 🟢 ≤20s · 🟡 ≤40s · 🔴 >40s |
| **Records Processed** | Total records ingested across all runs | Neutral |

---

### 🗓️ Pipeline Run Timeline

A **Gantt-style timeline chart** showing when each pipeline stage ran and how long it took.

- **Y-axis** — stream name (flights, passengers, etc.)
- **X-axis** — time
- **Bar color** — 🟢 success · 🔴 failed · 🟡 partial
- Helps visualize: which streams take longest? Did any fail?

---

### 📈 Success / Failure Trend (Left)

A **stacked bar chart** showing hourly counts of successful, failed, and partial pipeline runs.

- **X-axis** — hour
- **Y-axis** — count of runs
- **Colors** — green (success), red (failed), yellow (partial)
- Spot patterns: do failures cluster at certain times?

---

### ⏱️ Duration by Stage (Right)

A **grouped bar chart** showing average pipeline duration per stream, grouped by stage (silver/gold).

- **X-axis** — stream name
- **Y-axis** — duration in seconds
- **Grouped bars** — one bar per stage
- Identify which stream/stage combination is slowest

---

### 🚀 Throughput per Stream

A **multi-line chart** showing records processed over time per stream.

- Each line = one stream
- **X-axis** — time
- **Y-axis** — record count
- Markers on each data point for clarity
- Spot throughput drops that may indicate issues

---

### 📋 Pipeline Log Viewer

An **interactive data table** with filters for exploring raw pipeline logs.

**Filter dropdowns (top row):**

| Filter | Options | What It Filters |
|--------|---------|----------------|
| **Stream** | "All" + each stream name | Show logs for a specific stream only |
| **Status** | "All" + success/failed/partial | Show only runs with a specific outcome |
| **Stage** | "All" + silver/gold | Show only a specific pipeline stage |

**Table columns:**

| Column | Description |
|--------|------------|
| `run_id` | Unique identifier for the pipeline run |
| `timestamp` | When the run occurred |
| `stage` | Pipeline stage (silver or gold) |
| `stream` | Which data stream was processed |
| `status` | Run outcome (success/failed/partial) |
| `records_in` | Number of records read |
| `records_out` | Number of records written |
| `duration_sec` | How long processing took |
| `error_message` | Error details (if failed) |

---

## KPI Metrics & Data Quality

Deep dive into data quality scores and key performance indicators.

### Data Quality Scores by Stream

Six **circular gauge charts** — one per stream — showing the validation pass rate.

- **Needle position** — current quality score (0–100%)
- **Color zones:**
  - 🔴 Red: 0–85% (critical — many records failing validation)
  - 🟡 Yellow: 85–95% (warning — some quality issues)
  - 🟢 Green: 95–100% (healthy — most records pass)

---

### Schema Validation Rate

A **horizontal bar chart** showing the validation pass rate per stream.

- **Y-axis** — stream name
- **X-axis** — validation rate (0–100%)
- **Bar color** — dynamic: 🟢 >95% · 🟡 >85% · 🔴 ≤85%
- Quick comparison: which streams have the lowest quality?

---

### Quarantine Analysis

#### Quarantined Records per Stream (Left)

A **bar chart** showing how many records were quarantined (failed validation) per stream.

- High bars = more records failing = possible data source issues
- If all records passed: shows "✅ No quarantine files found — all records passed validation!"

#### Quarantine Failure Reasons (Right)

A **bar chart** showing the count of each type of validation failure across all streams.

- **Y-axis** — failure rule name (e.g., `delay_non_negative`, `temperature_range`)
- **X-axis** — count of failures
- Identifies which specific quality rules are being violated most

---

### Gold Table Freshness

An **interactive table** showing how up-to-date each Gold layer KPI table is.

| Column | Description |
|--------|------------|
| `Table` | Gold parquet file name (e.g., `flight_kpis`, `quality_kpis`) |
| `Last Modified` | Timestamp of when the file was last written |
| `Age (min)` | Minutes since last update |
| `Status` | 🟢 Fresh (<5 min) · 🟡 Stale (5–15 min) · 🔴 Outdated (>15 min) |

---

### Environmental Compliance

#### Compliance Gauge (Left)

A **circular gauge** showing overall environmental compliance percentage.

- Measures what percentage of environmental readings (temperature, humidity, CO2, air quality) fall within regulatory bounds
- **Thresholds:** 🟢 ≥95% · 🟡 ≥85% · 🔴 <85%

#### Compliance Bounds Table (Right)

An **interactive table** breaking down compliance per parameter:

| Column | Description |
|--------|------------|
| `Parameter` | Environmental metric (temperature_c, humidity_pct, co2_ppm, air_quality_index) |
| `In Bounds` | Number of readings within acceptable limits |
| `Total` | Total readings for that parameter |
| `Compliance %` | Percentage within bounds |

**Regulatory bounds:**
- Temperature: -10°C to 50°C
- Humidity: 0% to 100%
- CO2: 200 to 5,000 ppm
- Air Quality Index: 0 to 500

---

### KPI Summary Table

A consolidated **data table** of all key performance indicators with status:

| Column | Description |
|--------|------------|
| `KPI Name` | Name of the metric |
| `Current Value` | Latest computed value |
| `Threshold` | Target or acceptable range |
| `Status` | ✅ Passing · ⚠️ Warning · ❌ Failing |

Includes: pipeline success rate, quality scores per stream, flight OTP, checkpoint efficiency, safety alert resolution rate, and environmental compliance.

---

## Data Lineage & Governance

Track data flow, understand dependencies, and inspect data quality governance.

### Data Lineage Flow — Sankey Diagram

A **Sankey (flow) diagram** showing how data moves through the pipeline:

```
Bronze (raw JSON) → Silver (validated Parquet) → Gold (KPI aggregations)
```

- **Left nodes** — Bronze layer sources (one per stream)
- **Middle nodes** — Silver layer validated data
- **Right nodes** — Gold layer KPI tables
- **Flow width** — proportional to record count
- Thicker flows = more data moving through that path

---

### Impact Analysis

**What happens if a stream fails?** Select a stream from the dropdown to see:

| Element | What It Shows |
|---------|-------------|
| **Severity indicator** | 🔴 High / 🟡 Medium / 🟢 Low — how critical this stream is |
| **Affected Gold Tables** | Which KPI tables depend on this stream's data |
| **Affected KPIs** | Which specific KPIs would be wrong or missing |
| **Shared Gold Tables** | Other streams that feed the same Gold tables — useful for understanding blast radius |
| **Lineage tree** (expandable) | Full hierarchy: Bronze → Silver → Gold → KPI for the selected stream |

**Use case:** Before making changes to a data source, check which downstream analytics would break.

---

### Quality Rules Catalogue

An **interactive table** listing every validation rule in the system:

| Column | Description |
|--------|------------|
| `Stream` | Which stream the rule applies to |
| `Rule Name` | Unique rule identifier (e.g., `flight_id_format`, `temperature_range`) |
| `Field` | Which data field is checked |
| `Type` | Validation type: `regex`, `enum`, `range`, `not_null` |
| `Criteria` | The specific check (e.g., pattern `^[A-Z0-9]{2}\d{3,4}$`, range `0–500`) |
| `Status` | ✅ Passing — no quarantined records from this rule · ❌ Failing — some records violated this rule |

---

### Quarantine Inspector

Drill into quarantined (failed validation) records for a specific stream.

1. **Select a stream** from the dropdown
2. **Quarantine count** — metric showing how many records were quarantined
3. **Failure reasons table** — which rules were violated and how many times
4. **View quarantined records** (expandable) — full data table of all quarantined records with their failure reasons

If no records were quarantined: "✅ No quarantine records for **{stream}** — all records passed!"

---

### Reverse Lineage — Trace KPI to Source

**Work backwards from a KPI to find its data source.**

1. Select a KPI from the dropdown (e.g., `otp_pct`, `avg_wait_min`)
2. See the full trace: **KPI** ← Gold table ← Silver layer ← Bronze layer (stream)

**Use case:** "This KPI looks wrong — where does its data come from?"

---

### Data Classification Tags

A reference table showing data sensitivity classifications per stream:

| Tag | Color | Meaning |
|-----|-------|---------|
| **Operational** | 🔵 Blue | Day-to-day operational data |
| **PII** | 🔴 Red | Personally Identifiable Information (passengers) |
| **Commercial** | 🟢 Green | Business/commercial data (cargo, flights) |
| **Regulatory** | 🟣 Purple | Subject to regulatory compliance (environmental) |
| **Safety** | 🟠 Orange | Safety-critical data (runway, security) |
| **Security** | 🟤 Dark orange | Security-sensitive data |

---

## AI Ops Center

AI-powered diagnostics and recommendations using Claude.

> **Requires:** `ANTHROPIC_API_KEY` set in a `.env` file at the project root. Without it, AI features show a warning and are disabled, but the rest of the page still works.

---

### Status Banner (Top)

A colored banner showing overall system health:

| Banner | Meaning |
|--------|---------|
| 🟢 Green: **"All systems operational"** | No anomalies, all KPIs within targets |
| 🟡 Yellow: **"Warnings detected"** | Some quality issues or KPI breaches, but no critical failures |
| 🔴 Red: **"Critical issues detected"** | Pipeline failures, critical quality drops, or major KPI breaches |

---

### 🩺 System Diagnosis

Click **"Generate System Diagnosis"** to have Claude AI analyze the current state of all pipeline data, KPIs, and quality scores.

- Claude receives the full pipeline context (quality scores, pipeline health, KPIs, anomalies)
- Returns a structured diagnosis explaining what's happening and why
- Displayed in a styled card with light background

---

### 🔍 Incident Analysis

Four expandable sections that break down current issues:

#### 💡 What Changed?

Lists recent anomalies detected in the data:
- Stream name + icon
- Status description
- Error details
- Timestamp
- Shows "No anomalies detected" if everything is healthy

#### 🔴 What Broke?

Shows pipeline and quality failures:
- Pipeline success rate (highlighted if <100%)
- Streams with quarantined records and counts
- Top failure reasons per stream

#### 📊 What's Impacted?

Downstream impact analysis:
- Which KPIs are affected by current issues
- Which Gold tables are impacted
- KPIs in warning state with current value vs target

#### ✅ Recommended Actions

Click **"Get AI Recommendations"** for Claude to generate specific action items:
- Prioritized list of fixes
- Root cause analysis
- Preventive measures

---

### 💬 Ask the AI Ops Assistant

An interactive **chat interface** for asking questions about the system.

**Quick-start buttons** (click any to ask a pre-built question):
- "What is the current system health?"
- "Which streams have quality issues?"
- "What KPIs are at risk?"

**Free-form chat input** at the bottom — type any question about:
- System health and status
- Data quality issues
- KPI performance
- Pipeline problems
- Specific stream analysis

The AI has full context of all pipeline data, quality scores, and KPIs when answering.

---

### 📄 Show Context Sent to AI

An expandable section (collapsed by default) showing exactly what data the AI receives.

| Tab | What It Shows |
|-----|-------------|
| **Formatted Text** | Human-readable summary of all context sent to Claude |
| **Raw JSON** | The exact JSON data structure passed to the AI |

**Use case:** Transparency — verify what data the AI is basing its analysis on.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Bronze layer** | Raw, unprocessed data stored as JSON files |
| **Silver layer** | Validated and cleaned data stored as Parquet files |
| **Gold layer** | Aggregated KPI tables computed from Silver data |
| **Quarantine** | Records that failed quality validation, stored separately for investigation |
| **OTP** | On-Time Performance — percentage of flights departing within 15 minutes of schedule |
| **Medallion architecture** | Bronze → Silver → Gold data pipeline pattern |
| **DuckDB** | In-process SQL engine used for Gold layer aggregations |
| **Sankey diagram** | Flow visualization showing data movement between pipeline layers |
| **Quality score** | Percentage of records passing all validation rules for a stream |

---

*AeroOps AI — Smart Airport IoT DataOps Platform*
