"""AeroOps AI — Command Center (main Streamlit entry point)."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so local packages resolve correctly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
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
    page_loader,
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
st.markdown(page_loader(duration=1.5), unsafe_allow_html=True)

DATA_ROOT = _PROJECT_ROOT / "data"

# ── Section header SVG icons (navy, inline) ────────────────────────────────
_NAVY = "#1a1a2e"

SVG_SYSTEM_HEALTH = (
    f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{_NAVY}" stroke-width="2" style="vertical-align:middle">'
    '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>'
)

SVG_LIVE_AIRPORT = (
    f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{_NAVY}" stroke-width="2" style="vertical-align:middle">'
    '<rect x="2" y="3" width="20" height="14" rx="2"/>'
    '<circle cx="12" cy="10" r="4"/>'
    '<ellipse cx="12" cy="10" rx="1.8" ry="4"/>'
    '<line x1="8" y1="10" x2="16" y2="10"/>'
    '<line x1="8" y1="21" x2="16" y2="21"/>'
    '<line x1="12" y1="17" x2="12" y2="21"/></svg>'
)

SVG_MEDALLION = (
    f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{_NAVY}" stroke-width="2" style="vertical-align:middle">'
    '<path d="M12 2L2 7l10 5 10-5-10-5z"/>'
    '<path d="M2 17l10 5 10-5"/>'
    '<path d="M2 12l10 5 10-5"/></svg>'
)

SVG_RECENT_ALERTS = (
    f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{_NAVY}" stroke-width="2" style="vertical-align:middle">'
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
    '<line x1="12" y1="8" x2="12" y2="12"/>'
    '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
)

SVG_EVENTS_PROCESSED = (
    f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="{_NAVY}" stroke-width="2" style="vertical-align:middle">'
    '<path d="M4 6c4 0 4 6 8 6s4-6 8-6"/>'
    '<path d="M4 12c4 0 4 6 8 6s4-6 8-6"/>'
    '<path d="M4 18c4 0 4 6 8 6s4-6 8-6"/></svg>'
)


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
    """Return record counts per Bronze stream (reads JSON batch files)."""
    import json as _json
    counts: dict[str, int] = {}
    bronze_dir = DATA_ROOT / "bronze"
    if not bronze_dir.exists():
        return counts
    for stream in STREAM_ICONS:
        stream_dir = bronze_dir / stream
        if not stream_dir.exists():
            continue
        total = 0
        for jf in stream_dir.glob("*.json"):
            try:
                with open(jf, encoding="utf-8") as fh:
                    data = _json.load(fh)
                    total += len(data) if isinstance(data, list) else 1
            except Exception:
                pass
        if total:
            counts[stream] = total
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


# ── Sidebar SVG icons (white/yellow stroke for visibility on steel blue) ───
_W = COLORS["white"]
_WY = COLORS["warning_yellow"]
_accent = 'border-bottom:2px solid rgba(255,255,255,0.3);padding-bottom:6px;margin-bottom:8px;'

SVG_SIDEBAR_FAIL = (
    f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{_WY}" '
    f'stroke-width="2" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/>'
    f'<line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
)
SVG_SIDEBAR_PIPE = (
    f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{_W}" '
    f'stroke-width="2" style="vertical-align:middle"><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>'
    f'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 '
    f'11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 '
    f'0v-.09a1.65 1.65 0 00-1.08-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83'
    f'l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09a1.65 1.65 '
    f'0 001.51-1.08 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 '
    f'0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001.08 1.51 1.65 '
    f'1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9c.26'
    f'.604.852.997 1.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1.08z"/></svg>'
)
SVG_SIDEBAR_REFR = (
    f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{_W}" '
    f'stroke-width="2" style="vertical-align:middle"><path d="M21.5 2v6h-6"/>'
    f'<path d="M2.5 22v-6h6"/><path d="M2 11.5a10 10 0 0118.8-4.3L21.5 8"/>'
    f'<path d="M22 12.5a10 10 0 01-18.8 4.3L2.5 16"/></svg>'
)

_SIDEBAR_FAIL_HDR = (
    f'<div style="display:flex;align-items:center;gap:8px;{_accent}">'
    f'{SVG_SIDEBAR_FAIL}<span style="font-size:0.85rem;font-weight:700;color:{_WY};'
    f'text-transform:uppercase;letter-spacing:1.5px;">Failure Scenarios</span></div>'
)
_SIDEBAR_PIPE_HDR = (
    f'<div style="display:flex;align-items:center;gap:8px;{_accent}">'
    f'{SVG_SIDEBAR_PIPE}<span style="font-size:0.85rem;font-weight:700;color:{_W};'
    f'text-transform:uppercase;letter-spacing:1.5px;">Pipeline Controls</span></div>'
)
_SIDEBAR_REFR_HDR = (
    f'<div style="display:flex;align-items:center;gap:8px;{_accent}">'
    f'{SVG_SIDEBAR_REFR}<span style="font-size:0.85rem;font-weight:700;color:{_W};'
    f'text-transform:uppercase;letter-spacing:1.5px;">Auto Refresh</span></div>'
)

# ── Sidebar button CSS (Option C: outline style) ──────────────────────────
st.markdown(f"""
<style>
    [data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        color: {_W} !important;
        border: 1.5px solid rgba(255,255,255,0.4) !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 0.8rem !important;
        transition: all 0.2s ease !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(255,255,255,0.1) !important;
        border-color: rgba(255,255,255,0.7) !important;
    }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────
st.logo(str(_PROJECT_ROOT / "resources" / "logo.svg"), size="large")

with st.sidebar:
    # -- Failure Scenarios --
    st.markdown(_SIDEBAR_FAIL_HDR, unsafe_allow_html=True)
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
    st.markdown(_SIDEBAR_PIPE_HDR, unsafe_allow_html=True)
    if st.button("Run Pipeline", icon="⚡", use_container_width=True):
        with st.spinner("Running Bronze → Silver → Gold pipeline…"):
            try:
                result = run_pipeline()
                total = sum(r["total_records"] for r in result.get("silver_results", {}).values())
                st.cache_data.clear()
                st.session_state["_pipeline_msg"] = f"Pipeline complete — {total:,} records processed"
                st.rerun()
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")

    if st.button("Generate New Data", icon="➕", use_container_width=True):
        with st.spinner("Generating synthetic airport data & running pipeline…"):
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
                total = sum(r["total_records"] for r in result.get("silver_results", {}).values())
                quarantined = sum(r["quarantined"] for r in result.get("silver_results", {}).values())
                st.cache_data.clear()
                st.session_state["_generate_msg"] = f"Generated & processed {total:,} records ({quarantined:,} quarantined) ✅"
                st.rerun()
            except Exception as exc:
                st.error(f"Data generation failed: {exc}")

    # Show success messages persisted through rerun
    if "_pipeline_msg" in st.session_state:
        st.success(st.session_state.pop("_pipeline_msg"))
    if "_generate_msg" in st.session_state:
        st.success(st.session_state.pop("_generate_msg"))

    st.divider()

    # -- Auto Refresh --
    st.markdown(_SIDEBAR_REFR_HDR, unsafe_allow_html=True)
    refresh_interval = st.slider(
        "Refresh interval (sec)", min_value=10, max_value=300, value=60, step=10
    )
    if st.button("Start Auto Refresh", icon="⏱️", use_container_width=True):
        import time
        time.sleep(refresh_interval)
        st.cache_data.clear()
        st.rerun()

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
st.markdown(f'{SVG_LIVE_AIRPORT} &nbsp; <span style="font-size:1.3rem;font-weight:700;color:{_NAVY}">Live Airport Stats</span>', unsafe_allow_html=True)
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
st.markdown(f'{SVG_SYSTEM_HEALTH} &nbsp; <span style="font-size:1.3rem;font-weight:700;color:{_NAVY}">System Health per Stream</span>', unsafe_allow_html=True)
stream_cols = st.columns(6)

_STREAM_SVGS = {
    "flights": f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="{COLORS["navy"]}" stroke-width="1.8"><path d="M17.8 19.2L16 11l3.5-3.5C20.3 6.7 21 5.4 21 4.5c0-.6-.2-.9-.3-1-.1-.1-.4-.3-1-.3-.9 0-2.2.7-3 1.5L13 8.2 5 6.4a.5.5 0 0 0-.5.2l-1 1.3a.5.5 0 0 0 .1.6L9 12l-2 2.5H4.5a.5.5 0 0 0-.4.2l-1 1.3a.5.5 0 0 0 .1.6l3 1.5 1.5 3a.5.5 0 0 0 .6.1l1.3-1a.5.5 0 0 0 .2-.4V17.5l2.5-2 3.5 5.4a.5.5 0 0 0 .6.1l1.3-1a.5.5 0 0 0 .2-.5z"/></svg>',
    "passengers": f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="{COLORS["navy"]}" stroke-width="1.8"><circle cx="12" cy="7" r="4"/><path d="M5.5 21a6.5 6.5 0 0 1 13 0"/></svg>',
    "cargo": f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="{COLORS["navy"]}" stroke-width="1.8"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M12 12v4"/><path d="M3 12h18"/></svg>',
    "environmental": f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="{COLORS["navy"]}" stroke-width="1.8"><path d="M12 9a4 4 0 0 0-2 7.5"/><path d="M12 3v2"/><path d="M6.6 18.4l-1.4 1.4"/><path d="M20 12h-2"/><path d="M6 12H4"/><path d="M12 5a7 7 0 0 1 7 7c0 3-2 5.4-4 6.5"/><line x1="12" y1="12" x2="12" y2="21"/></svg>',
    "runway": f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="{COLORS["navy"]}" stroke-width="1.8"><rect x="4" y="3" width="16" height="18" rx="1"/><line x1="12" y1="6" x2="12" y2="8"/><line x1="12" y1="10" x2="12" y2="12"/><line x1="12" y1="14" x2="12" y2="16"/><line x1="12" y1="18" x2="12" y2="20"/></svg>',
    "security": f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="{COLORS["navy"]}" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
}

streams_ordered = list(STREAM_ICONS.keys())
for idx, stream in enumerate(streams_ordered):
    svg_icon = _STREAM_SVGS.get(stream, "")
    with stream_cols[idx]:
        if isinstance(quality_scores, dict) and stream in quality_scores:
            info = quality_scores[stream]
            score = info.get("quality_score", 0) if isinstance(info, dict) else 0
            status = _quality_status(score)
            status_color = STATUS_COLORS.get(status, COLORS["sky_blue"])
            if status == "healthy":
                bg_tint, label = "#e8f8f0", "Healthy"
            elif status == "warning":
                bg_tint, label = "#fef9e7", "Warning"
            else:
                bg_tint, label = "#fdedec", "Critical"
            st.markdown(
                f"""
                <div style="background:{bg_tint};border-left:5px solid {status_color};
                border-radius:8px;padding:1rem;text-align:center;
                box-shadow:0 2px 8px rgba(0,0,0,0.06);min-height:160px;">
                    <div>{svg_icon}</div>
                    <div style="font-weight:700;color:{COLORS['navy']};text-transform:capitalize;
                        margin:0.3rem 0;">{stream}</div>
                    <div style="font-size:1.6rem;font-weight:800;color:{status_color};">
                        {score}%</div>
                    <div style="font-size:0.8rem;color:{status_color};font-weight:600;
                        margin-top:0.3rem;">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background:{COLORS['white']};border-left:5px solid {COLORS['dark_gray']};
                border-radius:8px;padding:1rem;text-align:center;
                box-shadow:0 2px 8px rgba(0,0,0,0.06);min-height:160px;">
                    <div>{svg_icon}</div>
                    <div style="font-weight:700;color:{COLORS['navy']};text-transform:capitalize;
                        margin:0.3rem 0;">{stream}</div>
                    <div style="font-size:1.6rem;font-weight:800;color:{COLORS['dark_gray']};">
                        —</div>
                    <div style="font-size:0.8rem;color:{COLORS['dark_gray']};font-weight:600;
                        margin-top:0.3rem;">No data</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("")

# ── 3. Medallion Layer Health + Recent Alerts (side by side) ──────────────
medal_col, alerts_col = st.columns(2)

# -- Left: Medallion Layer Health --
with medal_col:
    st.markdown(f'{SVG_MEDALLION} &nbsp; <span style="font-size:1.3rem;font-weight:700;color:{_NAVY}">Medallion Layer Health</span>', unsafe_allow_html=True)

    bronze_counts = load_bronze_counts()
    silver_counts = load_silver_counts()

    if bronze_counts or silver_counts:
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

        _BRONZE_COLOR = "#cd7f32"
        _SILVER_COLOR = "#8a9bae"
        fig = go.Figure()
        fig.add_trace(go.Bar(x=stacked_df["Stream"], y=stacked_df["Bronze"], name="Bronze",
                             marker_color=_BRONZE_COLOR, width=0.22))
        fig.add_trace(go.Bar(x=stacked_df["Stream"], y=stacked_df["Silver"], name="Silver",
                             marker_color=_SILVER_COLOR, width=0.22))
        fig.update_layout(
            barmode="group",
            bargap=0.35,
            bargroupgap=0.05,
            height=400,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=20, t=40, b=40),
            font=dict(family="system-ui", size=12, color=COLORS["navy"]),
            title=dict(text="Records per Stream by Layer", font=dict(size=14, color=COLORS["navy"])),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No medallion data available yet.")

# -- Right: Recent Alerts Feed --
with alerts_col:
    st.markdown(f'{SVG_RECENT_ALERTS} &nbsp; <span style="font-size:1.3rem;font-weight:700;color:{_NAVY}">Recent Alerts</span>', unsafe_allow_html=True)
    security_df = load_security_events()

    if security_df is not None and not security_df.empty:
        SEV_COLORS = {
            "critical": COLORS["danger_red"],
            "high": COLORS["safety_orange"],
            "medium": COLORS["warning_yellow"],
            "low": "#58d68d",
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

        alerts_html = '<div style="position:relative;"><div style="max-height:380px;overflow-y:auto;padding-bottom:24px;">'
        for _, row in display_df.iterrows():
            sev = str(row[severity_col]).lower() if severity_col else "low"
            sev_color = SEV_COLORS.get(sev, SEV_COLORS["low"])
            ts_str = str(row[time_col])[:19] if time_col else ""
            desc = str(row[desc_col]) if desc_col else "Alert"
            badge_fg = "#000" if sev in ("medium", "low") else "#fff"
            alerts_html += f"""
            <div style="border-left:4px solid {sev_color};background:#fff;border-radius:8px;
            padding:10px 14px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:600;color:{COLORS['navy']};font-size:0.85rem;">{desc}</span>
                <span style="font-size:0.7rem;color:#999;">{ts_str[11:] if len(ts_str) > 11 else ts_str}</span>
              </div>
              <span style="display:inline-block;margin-top:4px;background:{sev_color};color:{badge_fg};
              padding:1px 8px;border-radius:10px;font-size:0.65rem;font-weight:700;
              text-transform:uppercase;letter-spacing:0.5px;">{sev}</span>
            </div>"""
        alerts_html += '</div>'
        alerts_html += '<div style="position:absolute;bottom:0;left:0;right:0;height:32px;background:linear-gradient(transparent, #fff);pointer-events:none;border-radius:0 0 8px 8px;"></div>'
        alerts_html += f'<div style="text-align:center;font-size:0.7rem;color:#aaa;margin-top:2px;">Scroll for more &#x25BE;</div>'
        alerts_html += '</div>'
        st.markdown(alerts_html, unsafe_allow_html=True)
    else:
        st.caption("No security alerts available.")

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='text-align:center;color:{COLORS['dark_gray']};font-size:0.8rem;'>"
    f"AeroOps AI — Smart Airport IoT DataOps Platform</p>",
    unsafe_allow_html=True,
)
