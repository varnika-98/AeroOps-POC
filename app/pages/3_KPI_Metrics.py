"""KPI Metrics & Data Quality dashboard page."""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.theme import COLORS, STATUS_COLORS, STREAM_ICONS, SVG_ICONS, apply_theme, metric_card, status_indicator, page_header, page_loader, section_header
from utils.charts import gauge_chart, bar_chart
from utils.kpi_calculator import get_data_quality_scores, get_environmental_compliance, get_overall_system_health

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
apply_theme(st)
st.markdown(page_loader(duration=0.5), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STREAMS = ["flights", "passengers", "cargo", "environmental", "runway", "security"]

DATA_DIR = PROJECT_ROOT / "data"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
QUARANTINE_DIR = DATA_DIR / "quarantine"

# Environmental compliance bounds
ENV_BOUNDS = {
    "temperature_c": (-10, 50),
    "humidity": (0, 100),
    "co2": (200, 5000),
    "aqi": (0, 500),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_parquet(path: str) -> pd.DataFrame | None:
    """Safely load a parquet file, returning None on failure."""
    try:
        p = Path(path)
        if p.exists():
            return pd.read_parquet(p)
    except Exception:
        pass
    return None


def _quality_color(score: float) -> str:
    if score > 95:
        return COLORS.get("success_green", "#2ecc71")
    elif score > 85:
        return COLORS.get("warning_yellow", "#f39c12")
    return COLORS.get("danger_red", "#e74c3c")


def _freshness_status(minutes: float) -> tuple[str, str]:
    """Return (status_label, emoji) for freshness."""
    if minutes < 5:
        return "Fresh", "🟢"
    elif minutes < 15:
        return "Stale", "🟡"
    return "Outdated", "🔴"


# =========================================================================
# Page content
# =========================================================================

st.markdown(page_header("KPI Metrics & Data Quality", SVG_ICONS["chart_up"]), unsafe_allow_html=True)

# ---------- 1. Data Quality Gauges ----------
st.markdown(section_header("Data Quality Scores by Stream", "gauge"), unsafe_allow_html=True)

quality_scores = get_data_quality_scores()  # dict: stream -> score

cols = st.columns(len(STREAMS))
for i, stream in enumerate(STREAMS):
    with cols[i]:
        score_data = quality_scores.get(stream, 0) if isinstance(quality_scores, dict) else 0
        score = score_data.get("quality_score", 0) if isinstance(score_data, dict) else score_data
        fig = gauge_chart(
            value=score,
            title=f"{stream.title()}",
            max_val=100,
            thresholds={
                "warning": 95,
                "critical": 85,
            },
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------- 2. Schema Validation Rate ----------
st.markdown(section_header("Schema Validation Rate", "validate"), unsafe_allow_html=True)

quality_df = load_parquet(str(GOLD_DIR / "quality_kpis.parquet"))
if quality_df is not None and not quality_df.empty:
    # Build validation pass-rate per stream
    if "stream" in quality_df.columns and "quality_score" in quality_df.columns:
        val_df = quality_df.groupby("stream")["quality_score"].mean().reset_index()
        val_df.columns = ["Stream", "Validation Rate (%)"]
        val_df["color"] = val_df["Validation Rate (%)"].apply(_quality_color)

        fig = bar_chart(
            val_df,
            x_col="Stream",
            y_col="Validation Rate (%)",
            title="Schema Validation Pass Rate per Stream",
            color=None,
        )
        # Color individual bars
        if fig.data:
            fig.data[0].marker.color = val_df["color"].tolist()
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Quality KPI data does not contain expected columns.")
else:
    st.info("No quality_kpis.parquet found — run the pipeline to generate KPIs.")

# ---------- 3. Quarantine: Trend & Breakdown ----------
st.markdown(section_header("Quarantine Analysis", "quarantine"), unsafe_allow_html=True)

left_col, right_col = st.columns(2)

quarantine_counts: dict[str, int] = {}
quarantine_reasons: dict[str, pd.Series] = {}

for stream in STREAMS:
    qf = load_parquet(str(QUARANTINE_DIR / f"{stream}_quarantine.parquet"))
    if qf is not None:
        quarantine_counts[stream] = len(qf)
        reason_col = "_quarantine_reasons"
        if reason_col in qf.columns:
            # Reasons may be lists or strings — explode for counting
            reasons = qf[reason_col].dropna()
            if not reasons.empty:
                exploded = reasons.explode() if reasons.apply(lambda x: isinstance(x, list)).any() else reasons
                quarantine_reasons[stream] = exploded.value_counts()

with left_col:
    st.markdown("**Quarantined Records per Stream**")
    if quarantine_counts:
        qc_df = pd.DataFrame(
            {"Stream": list(quarantine_counts.keys()), "Quarantined Records": list(quarantine_counts.values())}
        )
        fig = bar_chart(qc_df, x_col="Stream", y_col="Quarantined Records", title="Quarantined Records by Stream")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No quarantine files found — all records passed validation! ✅")

with right_col:
    st.markdown("**Quarantine Failure Reasons**")
    if quarantine_reasons:
        all_reasons: list[dict] = []
        for stream, counts in quarantine_reasons.items():
            for reason, cnt in counts.items():
                all_reasons.append({"Stream": stream, "Reason": str(reason), "Count": int(cnt)})
        if all_reasons:
            reasons_df = pd.DataFrame(all_reasons)
            fig = bar_chart(reasons_df, x_col="Reason", y_col="Count", title="Failure Reasons Breakdown")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No failure reasons recorded.")
    else:
        st.info("No quarantine reason data available.")

# ---------- 4. Gold Table Freshness ----------
st.markdown(section_header("Gold Table Freshness", "freshness"), unsafe_allow_html=True)

freshness_rows: list[dict] = []
if GOLD_DIR.exists():
    for f in sorted(GOLD_DIR.glob("*.parquet")):
        try:
            mtime = os.path.getmtime(f)
            age_min = (time.time() - mtime) / 60.0
            status_label, emoji = _freshness_status(age_min)
            freshness_rows.append({
                "Table": f.stem,
                "Last Modified": datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "Age (min)": round(age_min, 1),
                "Status": f"{emoji} {status_label}",
            })
        except OSError:
            freshness_rows.append({"Table": f.stem, "Last Modified": "N/A", "Age (min)": None, "Status": "🔴 Error"})

if freshness_rows:
    st.dataframe(pd.DataFrame(freshness_rows), use_container_width=True, hide_index=True)
else:
    st.info("No gold parquet files found.")

# ---------- 5. Environmental Compliance ----------
st.markdown(section_header("Environmental Compliance", "leaf"), unsafe_allow_html=True)

env_data = get_environmental_compliance()
env_df = load_parquet(str(SILVER_DIR / "environmental.parquet"))

env_left, env_right = st.columns(2)

with env_left:
    compliance_pct = env_data.get("compliance_pct", env_data.get("in_bounds_pct", 0))
    fig = gauge_chart(
        value=compliance_pct,
        title="Environmental Compliance %",
        max_val=100,
        thresholds={"warning": 95, "critical": 85},
    )
    st.plotly_chart(fig, use_container_width=True)

with env_right:
    if env_df is not None and not env_df.empty:
        bounds_info: list[dict] = []
        for col, (lo, hi) in ENV_BOUNDS.items():
            if col in env_df.columns:
                total = env_df[col].dropna().shape[0]
                in_bounds = ((env_df[col] >= lo) & (env_df[col] <= hi)).sum()
                pct = round(in_bounds / total * 100, 1) if total else 0
                bounds_info.append({"Parameter": col, "In Bounds": int(in_bounds), "Total": total, "Compliance %": pct})
        if bounds_info:
            st.dataframe(pd.DataFrame(bounds_info), use_container_width=True, hide_index=True)
        else:
            st.info("Environmental columns not found in data.")
    else:
        st.info("No environmental data available.")

# ---------- 6. KPI Summary Table ----------
st.markdown(section_header("KPI Summary Table", "table"), unsafe_allow_html=True)

system = get_overall_system_health()

kpi_rows: list[dict] = []


def _status_icon(val: float, green_thresh: float, yellow_thresh: float) -> str:
    if val >= green_thresh:
        return "✅"
    elif val >= yellow_thresh:
        return "⚠️"
    return "❌"


# Pipeline KPIs
pipeline = system.get("pipeline", {})
if pipeline:
    kpi_rows.append({
        "KPI Name": "Pipeline Success Rate",
        "Current Value": f"{pipeline.get('success_rate', 0):.1f}%",
        "Threshold": ">95% green, >85% yellow",
        "Status": _status_icon(pipeline.get("success_rate", 0), 95, 85),
    })

# Quality KPIs per stream
quality = system.get("quality", {})
if isinstance(quality, dict):
    for stream, score in quality.items():
        if isinstance(score, (int, float)):
            kpi_rows.append({
                "KPI Name": f"Data Quality — {stream.title()}",
                "Current Value": f"{score:.1f}%",
                "Threshold": ">95% green, >85% yellow",
                "Status": _status_icon(score, 95, 85),
            })

# Flight KPIs
flights = system.get("flights", {})
if flights:
    otp = flights.get("otp_pct", 0)
    kpi_rows.append({
        "KPI Name": "On-Time Performance",
        "Current Value": f"{otp:.1f}%",
        "Threshold": ">90% green, >80% yellow",
        "Status": _status_icon(otp, 90, 80),
    })

# Passenger KPIs
passengers = system.get("passengers", {})
if passengers:
    eff = passengers.get("checkpoint_efficiency_pct", 0)
    kpi_rows.append({
        "KPI Name": "Checkpoint Efficiency",
        "Current Value": f"{eff:.1f}%",
        "Threshold": ">90% green, >80% yellow",
        "Status": _status_icon(eff, 90, 80),
    })

# Safety KPIs
safety = system.get("safety", {})
if safety:
    res = safety.get("resolution_rate_pct", 0)
    kpi_rows.append({
        "KPI Name": "Safety Alert Resolution",
        "Current Value": f"{res:.1f}%",
        "Threshold": ">95% green, >85% yellow",
        "Status": _status_icon(res, 95, 85),
    })

# Environmental compliance
kpi_rows.append({
    "KPI Name": "Environmental Compliance",
    "Current Value": f"{compliance_pct:.1f}%",
    "Threshold": ">95% green, >85% yellow",
    "Status": _status_icon(compliance_pct, 95, 85),
})

if kpi_rows:
    st.dataframe(pd.DataFrame(kpi_rows), use_container_width=True, hide_index=True)
else:
    st.info("No KPI data available — run the pipeline first.")
