"""AeroOps AI — Command Center (main Streamlit entry point)."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so local packages resolve correctly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import streamlit as st

# ── Page config (MUST be the first Streamlit command) ──────────────────────
st.set_page_config(page_title="AeroOps AI", page_icon="✈️", layout="wide")

from utils.theme import (
    COLORS,
    STATUS_COLORS,
    STREAM_ICONS,
    apply_theme,
    metric_card,
    page_header,
    status_indicator,
)
from utils.charts import bar_chart, stacked_bar_chart
from utils.kpi_calculator import (
    get_data_quality_scores,
    get_flight_kpis,
    get_passenger_kpis,
    get_pipeline_health,
    get_safety_kpis,
)
from pipeline.orchestrator import run_pipeline

# ── Apply custom CSS theme ─────────────────────────────────────────────────
apply_theme(st)

DATA_ROOT = _PROJECT_ROOT / "data"


# ── Cached data loaders ───────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_flight_kpis() -> dict:
    return get_flight_kpis()


@st.cache_data(ttl=60)
def load_passenger_kpis() -> dict:
    return get_passenger_kpis()


@st.cache_data(ttl=60)
def load_pipeline_health() -> dict:
    return get_pipeline_health()


@st.cache_data(ttl=60)
def load_quality_scores() -> dict:
    return get_data_quality_scores()


@st.cache_data(ttl=60)
def load_safety_kpis() -> dict:
    return get_safety_kpis()


@st.cache_data(ttl=60)
def load_silver_counts() -> dict[str, int]:
    """Return record counts per Silver stream."""
    counts: dict[str, int] = {}
    silver_dir = DATA_ROOT / "silver"
    if not silver_dir.exists():
        return counts
    for stream in STREAM_ICONS:
        path = silver_dir / f"{stream}.parquet"
        if path.exists():
            try:
                counts[stream] = len(pd.read_parquet(path))
            except Exception:
                counts[stream] = 0
    return counts


@st.cache_data(ttl=60)
def load_bronze_counts() -> dict[str, int]:
    """Return record counts per Bronze stream."""
    counts: dict[str, int] = {}
    bronze_dir = DATA_ROOT / "bronze"
    if not bronze_dir.exists():
        return counts
    for stream in STREAM_ICONS:
        path = bronze_dir / f"{stream}.parquet"
        if path.exists():
            try:
                counts[stream] = len(pd.read_parquet(path))
            except Exception:
                counts[stream] = 0
    return counts


@st.cache_data(ttl=60)
def load_gold_counts() -> dict[str, int]:
    """Return record counts per Gold KPI table."""
    counts: dict[str, int] = {}
    gold_dir = DATA_ROOT / "gold"
    if not gold_dir.exists():
        return counts
    for f in gold_dir.glob("*.parquet"):
        try:
            counts[f.stem] = len(pd.read_parquet(f))
        except Exception:
            counts[f.stem] = 0
    return counts


@st.cache_data(ttl=60)
def load_security_events() -> pd.DataFrame | None:
    """Load security silver data for the alerts feed."""
    path = DATA_ROOT / "silver" / "security.parquet"
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


# ── Color shortcuts for f-string usage ─────────────────────────────────────
_C_WHITE = COLORS["white"]
_C_LIGHT_GRAY = COLORS["light_gray"]
_C_SKY_BLUE = COLORS["sky_blue"]
_C_NAVY = COLORS["navy"]
_C_DARK_GRAY = COLORS["dark_gray"]
_C_WARN_YELLOW = COLORS["warning_yellow"]

# ── Sidebar ────────────────────────────────────────────────────────────────
st.logo(str(_PROJECT_ROOT / "resources" / "logo.svg"), size="large")

with st.sidebar:
    # -- Failure Scenarios --
    st.markdown(
        f"<h4 style='color:{_C_WARN_YELLOW}'>⚠️ Failure Scenarios</h4>",
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("failure_schema_drift", False)
    st.session_state.setdefault("failure_sensor_outage", False)
    st.session_state.setdefault("failure_traffic_spike", False)

    st.session_state["failure_schema_drift"] = st.checkbox(
        "Runway Schema Drift", value=st.session_state["failure_schema_drift"]
    )
    st.session_state["failure_sensor_outage"] = st.checkbox(
        "Passenger Sensor Outage", value=st.session_state["failure_sensor_outage"]
    )
    st.session_state["failure_traffic_spike"] = st.checkbox(
        "Holiday Traffic Spike", value=st.session_state["failure_traffic_spike"]
    )

    st.divider()

    # -- Pipeline Controls --
    st.markdown(
        f"<h4 style='color:{_C_SKY_BLUE}'>🔧 Pipeline Controls</h4>",
        unsafe_allow_html=True,
    )
    if st.button("▶️ Run Pipeline", use_container_width=True):
        with st.spinner("Running Bronze → Silver → Gold pipeline…"):
            try:
                result = run_pipeline()
                st.success(
                    f"Pipeline complete — {result.get('total_records_processed', 'N/A')} records processed"
                )
                st.cache_data.clear()
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")

    if st.button("🔄 Generate New Data", use_container_width=True):
        with st.spinner("Generating synthetic airport data…"):
            try:
                from simulator.airport_generator import generate_all_events, write_events_to_json
                from simulator.failure_injector import (
                    inject_schema_drift,
                    inject_sensor_outage,
                    inject_traffic_spike,
                )
                multiplier = 1.0
                if st.session_state.get("failure_traffic_spike"):
                    multiplier = inject_traffic_spike()

                events = generate_all_events(rate_multiplier=multiplier)

                if st.session_state.get("failure_schema_drift"):
                    events = inject_schema_drift(events)
                if st.session_state.get("failure_sensor_outage"):
                    events = inject_sensor_outage(events)

                write_events_to_json(events)
                result = run_pipeline()
                st.success("Data generated & pipeline executed ✅")
                st.cache_data.clear()
            except Exception as exc:
                st.error(f"Data generation failed: {exc}")



# ── Helper: determine status from quality score ──────────────────────────
def _quality_status(score: float) -> str:
    if score >= 90:
        return "healthy"
    if score >= 70:
        return "warning"
    return "critical"


# ── Main Content ───────────────────────────────────────────────────────────
st.markdown(page_header("Command Center", ""), unsafe_allow_html=True)

# Load all KPI data
flight_kpis = load_flight_kpis()
passenger_kpis = load_passenger_kpis()
pipeline_health = load_pipeline_health()
quality_scores = load_quality_scores()
safety_kpis = load_safety_kpis()

has_data = "status" not in flight_kpis or flight_kpis.get("status") != "no_data"

if not has_data:
    st.info(
        "👋 **Welcome to AeroOps AI!** No data found yet. "
        "Click **Generate New Data** in the sidebar to create synthetic airport data "
        "and run the pipeline.",
        icon="✈️",
    )

# ── 1. Live Airport Stats ─────────────────────────────────────────────────
st.markdown("### 📊 Live Airport Stats")
col1, col2, col3, col4 = st.columns(4)

total_flights = flight_kpis.get("total_flights", 0) if has_data else 0
total_passengers = passenger_kpis.get("total_passengers", 0) if has_data else 0
success_rate = pipeline_health.get("success_rate", 0) if "status" not in pipeline_health else 0

# Average quality score across streams
avg_quality = 0.0
if isinstance(quality_scores, dict) and "status" not in quality_scores:
    scores = [v["quality_score"] for v in quality_scores.values() if isinstance(v, dict) and "quality_score" in v]
    avg_quality = round(sum(scores) / len(scores), 1) if scores else 0.0

with col1:
    st.markdown(
        metric_card("Total Flights Today", f"{total_flights:,}", status="healthy"),
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        metric_card("Passengers Processed", f"{total_passengers:,}", status="healthy"),
        unsafe_allow_html=True,
    )
with col3:
    rate_status = "healthy" if success_rate >= 95 else ("warning" if success_rate >= 80 else "critical")
    st.markdown(
        metric_card("Pipeline Success Rate", f"{success_rate}%", status=rate_status),
        unsafe_allow_html=True,
    )
with col4:
    q_status = _quality_status(avg_quality)
    st.markdown(
        metric_card("Data Quality Score", f"{avg_quality}%", status=q_status),
        unsafe_allow_html=True,
    )

st.markdown("")

# ── 2. System Health per Stream ────────────────────────────────────────────
st.markdown("### 🚦 System Health per Stream")
stream_cols = st.columns(6)

streams_ordered = list(STREAM_ICONS.keys())
for idx, stream in enumerate(streams_ordered):
    icon = STREAM_ICONS[stream]
    with stream_cols[idx]:
        if isinstance(quality_scores, dict) and stream in quality_scores:
            info = quality_scores[stream]
            score = info.get("quality_score", 0) if isinstance(info, dict) else 0
            status = _quality_status(score)
            indicator = status_indicator(status)
            st.markdown(
                f"""
                <div style="background:{COLORS['white']};border-radius:10px;padding:1rem;
                text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                    <div style="font-size:2rem;">{icon}</div>
                    <div style="font-weight:600;color:{COLORS['navy']};text-transform:capitalize;">
                        {stream}
                    </div>
                    <div style="font-size:1.5rem;">{indicator}</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{STATUS_COLORS.get(status, COLORS['sky_blue'])};">
                        {score}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background:{COLORS['white']};border-radius:10px;padding:1rem;
                text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                    <div style="font-size:2rem;">{icon}</div>
                    <div style="font-weight:600;color:{COLORS['navy']};text-transform:capitalize;">
                        {stream}
                    </div>
                    <div style="font-size:1.5rem;">⚪</div>
                    <div style="font-size:0.85rem;color:{COLORS['dark_gray']};">No data</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("")

# ── 3. Medallion Layer Health ──────────────────────────────────────────────
st.markdown("### 🏅 Medallion Layer Health")

bronze_counts = load_bronze_counts()
silver_counts = load_silver_counts()
gold_counts = load_gold_counts()

if bronze_counts or silver_counts or gold_counts:
    layer_data = {
        "Layer": ["Bronze", "Silver", "Gold"],
        "Records": [
            sum(bronze_counts.values()),
            sum(silver_counts.values()),
            sum(gold_counts.values()),
        ],
    }
    layer_df = pd.DataFrame(layer_data)

    # Build a stacked view: per-stream counts at each layer
    stacked_rows = []
    for stream in streams_ordered:
        stacked_rows.append(
            {
                "Stream": stream,
                "Bronze": bronze_counts.get(stream, 0),
                "Silver": silver_counts.get(stream, 0),
            }
        )
    stacked_df = pd.DataFrame(stacked_rows)
    fig = stacked_bar_chart(stacked_df, "Stream", ["Bronze", "Silver"], "Records per Stream by Layer")
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No medallion data available yet.")

# ── 4. Two-column layout: Alerts + Events per Stream ──────────────────────
left_col, right_col = st.columns(2)

# -- Left: Recent Alerts Feed --
with left_col:
    st.markdown("### 🚨 Recent Alerts")
    security_df = load_security_events()

    if security_df is not None and not security_df.empty:
        SEVERITY_BADGES = {
            "critical": f"background:{COLORS['danger_red']};color:#fff",
            "high": f"background:{COLORS['safety_orange']};color:#fff",
            "medium": f"background:{COLORS['warning_yellow']};color:#000",
            "low": f"background:{COLORS['sky_blue']};color:#fff",
        }

        severity_col = None
        for candidate in ("severity", "alert_level", "level", "priority"):
            if candidate in security_df.columns:
                severity_col = candidate
                break

        time_col = None
        for candidate in ("timestamp", "event_time", "created_at", "ts"):
            if candidate in security_df.columns:
                time_col = candidate
                break

        desc_col = None
        for candidate in ("event_type", "description", "alert_type", "message", "type"):
            if candidate in security_df.columns:
                desc_col = candidate
                break

        display_df = security_df.copy()
        if time_col:
            display_df = display_df.sort_values(time_col, ascending=False)
        display_df = display_df.head(20)

        alerts_html = '<div style="max-height:350px;overflow-y:auto;padding-right:0.5rem;">'
        for _, row in display_df.iterrows():
            sev = str(row[severity_col]).lower() if severity_col else "low"
            badge_style = SEVERITY_BADGES.get(sev, SEVERITY_BADGES["low"])
            ts_str = str(row[time_col])[:19] if time_col else ""
            desc = str(row[desc_col]) if desc_col else "Alert"
            alerts_html += f"""
            <div style="background:{COLORS['white']};border-radius:8px;padding:0.6rem 0.8rem;
            margin-bottom:0.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);display:flex;
            align-items:center;gap:0.6rem;">
                <span style="{badge_style};padding:2px 8px;border-radius:4px;
                font-size:0.7rem;font-weight:700;text-transform:uppercase;">{sev}</span>
                <span style="flex:1;color:{COLORS['navy']};font-size:0.85rem;">{desc}</span>
                <span style="color:{COLORS['dark_gray']};font-size:0.75rem;white-space:nowrap;">{ts_str}</span>
            </div>"""
        alerts_html += "</div>"
        st.markdown(alerts_html, unsafe_allow_html=True)
    else:
        st.caption("No security alerts available.")

# -- Right: Events Processed per Stream --
with right_col:
    st.markdown("### 📈 Events Processed per Stream")
    silver = load_silver_counts()
    if silver:
        stream_df = pd.DataFrame(
            {"Stream": list(silver.keys()), "Records": list(silver.values())}
        )
        fig = bar_chart(stream_df, "Stream", "Records", "Silver Layer Records by Stream")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No stream data available.")

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='text-align:center;color:{_C_DARK_GRAY};font-size:0.8rem;'>"
    f"AeroOps AI — Smart Airport IoT DataOps Platform</p>",
    unsafe_allow_html=True,
)
