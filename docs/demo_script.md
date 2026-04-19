# AeroOps AI — Demo Script for Sanjeev

## Quick Setup (< 2 minutes)

```bash
cd MiraclesPOC
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # Add your ANTHROPIC_API_KEY
python -m simulator.airport_generator
python -m simulator.pipeline_log_generator
python -m pipeline.orchestrator
streamlit run app/🏠_Command_Center.py
```

---

## Demo Flow: Detect → Diagnose → Assess → Recommend

### Act 1: Normal State (2 min)

**Command Center** — "This is our airport operations dashboard monitoring 6 IoT sensor streams through a Bronze/Silver/Gold medallion pipeline."

- Point out: all 6 streams showing green health indicators
- Show: 66K+ events processed, 100% pipeline success rate, high data quality
- Show: medallion layer chart — Bronze raw events flowing to Silver validated to Gold KPIs

**Flight & Passenger** — "Here's our operational analytics."

- Show: Flight OTP gauge (should be ~80%+), delay distribution histogram
- Show: Passenger throughput by checkpoint, baggage processing funnel

### Act 2: Inject Failure (2 min)

**Command Center sidebar** — Check "Runway Schema Drift" toggle.

- Click "Generate New Data" — this regenerates data with the failure injected
- Click "Run Pipeline" — pipeline processes the corrupted data

**Watch the dashboard react:**
- Runway stream health indicator turns yellow/red
- Data quality score drops
- Quarantine count increases for runway stream

### Act 3: Diagnose with Pipeline Health (1 min)

**Pipeline Health page** — "Let's see what the pipeline detected."

- Show: runway stream showing increased quarantine
- Show: log viewer filtered to runway — validation failures visible
- Point out: other streams unaffected — isolation works

### Act 4: Assess Impact with Lineage (1 min)

**Data Lineage page** — "Now let's trace the impact."

- Show: Sankey diagram — runway flow has reduced throughput at Silver
- Select "runway" in impact analysis — shows which Gold KPIs are affected
- Show: reverse lineage from "Runway Utilization" KPI back to Bronze source

### Act 5: AI Diagnosis (2 min)

**AI Ops Center** — "Let's ask Claude what happened."

- Click "Generate System Diagnosis"
- Claude explains: wind speed values changed from kph to mph, likely firmware update
- Show the grounding context panel — "This is the exact data Claude saw — no hallucination"
- Ask in chat: "What should we do to fix the runway sensor issue?"

### Act 6: KPI Deep Dive (1 min)

**KPI Metrics** — "Here's the governance view."

- Show: quality gauges per stream — runway degraded
- Show: quarantine breakdown — wind_speed_range failures
- Show: Gold table freshness — still within SLA

---

## Key Talking Points

1. **Medallion Architecture** — "Bronze preserves raw data, Silver enforces quality, Gold computes business KPIs. Same pattern as Microsoft Fabric Lakehouse."

2. **Grounded AI** — "Claude only references actual pipeline data. Show the context panel — this is what makes AI enterprise-ready, not the model, but the data architecture around it."

3. **Observable by Design** — "The failure propagated through 3 layers and the dashboard surfaced it at every level. In production, this is how you catch issues before business users notice stale KPIs."

4. **Data Governance** — "Quality rules per stream, quarantine tracking, lineage from any Gold KPI back to its Bronze source. This matches what your team built for the airport case study."

5. **This mirrors real problems** — "Schema drift from firmware updates, sensor outages, traffic spikes — these are the exact issues that break data pipelines in production."

---

## Other Scenarios to Demo

- **Passenger Sensor Outage** — 3 checkpoints go offline, throughput KPIs underreport
- **Holiday Traffic Spike** — 3x volume overwhelms pipeline, freshness SLA breached

---

## Technical Q&A Prep

See `docs/architecture.md` section 11 for 8 prepared Q&A responses covering architecture, KPI identification, AI integration, failure scenarios, and improvement roadmap.
