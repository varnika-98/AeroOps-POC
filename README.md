# ✈️ AeroOps AI — Smart Airport IoT DataOps Dashboard

A Streamlit dashboard that monitors a smart airport's IoT sensor network through a **Bronze → Silver → Gold medallion pipeline** — visualizing flight operations, passenger flow, cargo processing, and environmental systems — with **Claude AI** providing grounded incident diagnosis and pipeline optimization recommendations.

> IoT/Sensors data lake for a major international airport with 200+ destinations.

---

## 🏗️ Architecture

```
IoT Sensor Network (6 Streams)
  ├── ✈️ Flight Operations
  ├── 👥 Passenger Flow
  ├── 📦 Cargo & Baggage
  ├── 🌡️ Environmental
  ├── 🛬 Runway & Ground
  └── 🔒 Security Systems
         │
    ┌────┴────┐
    ▼         ▼
 BRONZE    Pipeline
 (Raw)     Logs
    │
    ▼
 SILVER
 (Validated)
    │
    ▼
  GOLD ──► Streamlit Dashboard (6 pages) ──► Claude AI
 (KPIs)
```

### Medallion Layers
- **Bronze**: Raw JSON events, append-only, no transformations
- **Silver**: Schema-enforced, quality-validated, bad records quarantined
- **Gold**: Aggregated KPIs, business metrics, SLA tracking

---

## 📊 Dashboard Pages

| Page | Description |
|------|-------------|
| 🏠 **Command Center** | System health with SVG icon cards, grouped medallion layer bars, recent alerts |
| 👥 **Passenger Analytics** | Passenger flow, checkpoint wait times, baggage funnel |
| 🔧 **Pipeline Health** | ETL run history, success/failure trends, log viewer |
| 📈 **KPI Metrics** | Data quality scores, schema validation, SLA compliance |
| 🔗 **Data Lineage** | Bronze→Silver→Gold flow, impact analysis, governance |
| 🤖 **AI Ops Center** | Claude Haiku 4.5 diagnosis with Ollama fallback, recommendations, chat |
| 📊 **AI Performance Monitor** | LLM usage analytics: latency, token cost, error rates, prompt-type breakdown |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Claude API key ([console.anthropic.com](https://console.anthropic.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/varnika-98/AeroOps-POC.git
cd AeroOps-POC

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Generate sample data
python -m simulator.airport_generator

# Run the dashboard
streamlit run app/Command_Center.py
```

---

## 🧪 Failure Scenarios

Injectable scenarios to demonstrate observability:

1. **Runway Sensor Schema Drift** — Unit change (kph → mph) causes validation failures
2. **Passenger Sensor Outage** — 3 checkpoints go offline, KPIs underreport
3. **Holiday Traffic Spike** — 3x volume overwhelms pipeline, SLA breach

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Visualizations | Plotly |
| Data Processing | Pandas + DuckDB |
| Storage | Parquet (Bronze/Silver/Gold) |
| AI | Claude Haiku 4.5 (Anthropic SDK) + Ollama fallback |
| Deployment | Streamlit Community Cloud |

---

## 📁 Project Structure

```
AeroOps-POC/
├── app/                    # Streamlit dashboard
│   ├── Command_Center.py   # Main entry point
│   └── pages/
│       ├── 1_Passenger_Analytics.py
│       ├── 2_Pipeline_Health.py
│       ├── 3_KPI_Metrics.py
│       ├── 4_Data_Lineage.py
│       ├── 5_AI_Ops_Center.py
│       └── 6_AI_Performance_Monitor.py
├── simulator/              # IoT data & log generators
├── pipeline/               # Bronze → Silver → Gold ETL
├── ai/                     # Claude AI integration
├── utils/                  # Charts, KPI calc, lineage, theme
├── data/                   # Generated data (gitignored)
└── resources/              # Reference documents & architecture docs
```

---

## 👩‍💻 Author

**Varnika Prasad** — Data Engineer / AI Engineer

---

## 📄 License

This project is for demonstration purposes only.
