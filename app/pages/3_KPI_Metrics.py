"""KPI Metrics & Data Quality dashboard page."""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.theme import COLORS, STATUS_COLORS, STREAM_ICONS, SVG_ICONS, apply_theme, metric_card, status_indicator, page_header, page_loader, section_header
from utils.charts import bar_chart
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

# Environmental compliance bounds (must match silver/environmental.parquet columns)
ENV_BOUNDS = {
    "temperature_c": (-10, 50),
    "humidity_pct": (0, 100),
    "co2_ppm": (200, 5000),
    "air_quality_index": (0, 500),
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

_GAUGE_LEGEND = """
<div style="
    display: flex; justify-content: center; gap: 2rem;
    margin: 0.5rem 0 1.5rem 0; padding: 0.6rem 1.2rem;
    background: rgba(0,0,0,0.02); border-radius: 8px;
    font-family: system-ui; font-size: 0.85rem; color: #1B2A4A;
">
    <span>
        <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#2ECC71;margin-right:6px;vertical-align:middle;"></span>
        Healthy (≥ 95%)
    </span>
    <span>
        <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#f39c12;margin-right:6px;vertical-align:middle;"></span>
        Warning (85–95%)
    </span>
    <span>
        <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
            background:#e74c3c;margin-right:6px;vertical-align:middle;"></span>
        Critical (&lt; 85%)
    </span>
</div>
"""

st.markdown(_GAUGE_LEGEND, unsafe_allow_html=True)

cols = st.columns(len(STREAMS))
for i, stream in enumerate(STREAMS):
    with cols[i]:
        score_data = quality_scores.get(stream, 0) if isinstance(quality_scores, dict) else 0
        score = score_data.get("quality_score", 0) if isinstance(score_data, dict) else score_data
        bar_color = COLORS["success_green"] if score >= 95 else (COLORS["warning_yellow"] if score >= 85 else COLORS["danger_red"])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": stream.title(), "font": {"size": 14, "color": COLORS["navy"]}},
            number={"font": {"size": 32, "color": COLORS["navy"]}, "suffix": "%"},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#4682B4", "dtick": 20},
                "bar": {"color": bar_color},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 2,
                "bordercolor": "#4682B4",
                "threshold": {
                    "line": {"color": COLORS["dark_gray"], "width": 2},
                    "thickness": 0.8,
                    "value": 95,
                },
            },
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
            margin=dict(l=20, r=20, t=50, b=20),
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------- 2. Schema Validation Rate ----------
st.markdown(section_header("Schema Validation Rate", "validate"), unsafe_allow_html=True)

quality_df = load_parquet(str(GOLD_DIR / "quality_kpis.parquet"))
if quality_df is not None and not quality_df.empty:
    # Build validation pass-rate per stream
    if "stream" in quality_df.columns and "validation_rate_pct" in quality_df.columns:
        val_df = quality_df.groupby("stream")["validation_rate_pct"].mean().reset_index()
        val_df.columns = ["Stream", "Validation Rate (%)"]
        val_df["color"] = val_df["Validation Rate (%)"].apply(_quality_color)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=val_df["Stream"], y=val_df["Validation Rate (%)"],
            marker_color=val_df["color"].tolist(), width=0.25,
            text=[f"{r:.1f}%" for r in val_df["Validation Rate (%)"]],
            textposition="outside", textfont=dict(size=11, color=COLORS["navy"]),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=40, r=20, t=50, b=40),
            font=dict(family="system-ui", size=12, color=COLORS["navy"]),
            title=dict(text="Schema Validation Pass Rate per Stream", font=dict(size=16, color=COLORS["navy"])),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", title="Validation Rate (%)",
                       range=[0, val_df["Validation Rate (%)"].max() * 1.15]),
            xaxis=dict(showgrid=False),
            bargap=0.45,
        )
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
            reasons = qf[reason_col].dropna()
            if not reasons.empty:
                # Reasons may be JSON strings, actual lists, or plain strings
                import json as _json
                def _parse_reasons(val):
                    if isinstance(val, list):
                        return val
                    if isinstance(val, str) and val.startswith("["):
                        try:
                            return _json.loads(val)
                        except (ValueError, TypeError):
                            pass
                    return [val]
                parsed = reasons.apply(_parse_reasons).explode()
                quarantine_reasons[stream] = parsed.value_counts()

with left_col:
    st.markdown("**Quarantined Records per Stream**")
    if quarantine_counts:
        qc_df = pd.DataFrame(
            {"Stream": list(quarantine_counts.keys()), "Quarantined Records": list(quarantine_counts.values())}
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=qc_df["Stream"], y=qc_df["Quarantined Records"],
            marker_color=["#4682B4"] * len(qc_df), width=0.2,
            text=[f"{v:,}" for v in qc_df["Quarantined Records"]],
            textposition="outside", textfont=dict(size=11, color=COLORS["navy"]),
        ))
        fig.update_layout(
            height=350,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=20, t=40, b=40),
            font=dict(family="system-ui", size=12, color=COLORS["navy"]),
            title=dict(text="Records Failed Validation", font=dict(size=14, color=COLORS["navy"])),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", title="Records", range=[0, max(qc_df["Quarantined Records"]) * 1.5]),
            xaxis=dict(showgrid=False),
            bargap=0.35,
        )
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
            # Convert variable names to readable labels
            _REASON_LABELS = {
                "wait_time_range": "Wait Time Out of Range",
                "checkpoint_not_null": "Checkpoint Not Null",
                "wind_speed_range": "Wind Speed Out of Range",
                "flight_id_format": "Invalid Flight ID",
                "status_enum": "Invalid Status Value",
                "delay_non_negative": "Negative Delay",
                "temperature_range": "Temperature Out of Range",
                "humidity_range": "Humidity Out of Range",
                "co2_range": "CO₂ Out of Range",
                "aqi_range": "AQI Out of Range",
                "visibility_range": "Visibility Out of Range",
                "friction_range": "Friction Out of Range",
                "severity_enum": "Invalid Severity",
                "response_time_range": "Response Time Out of Range",
            }
            reasons_df["Reason"] = reasons_df["Reason"].map(
                lambda r: _REASON_LABELS.get(r, r.replace("_", " ").title())
            )
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=reasons_df["Reason"], y=reasons_df["Count"],
                marker_color=["#4682B4"] * len(reasons_df), width=0.2,
                text=[f"{v:,}" for v in reasons_df["Count"]],
                textposition="outside", textfont=dict(size=11, color=COLORS["navy"]),
            ))
            fig.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=20, t=40, b=40),
                font=dict(family="system-ui", size=12, color=COLORS["navy"]),
                title=dict(text="Failure Reasons Breakdown", font=dict(size=14, color=COLORS["navy"])),
                yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", title="Count", range=[0, max(reasons_df["Count"]) * 1.5]),
                xaxis=dict(showgrid=False),
                bargap=0.35,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No failure reasons recorded.")
    else:
        st.info("No quarantine reason data available.")

# ---------- 4. Gold Table Freshness ----------
st.markdown(section_header("Gold Table Freshness", "freshness"), unsafe_allow_html=True)

freshness_rows: list[dict] = []
_TABLE_LABELS = {
    "flight_kpis": "Flight KPIs",
    "passenger_kpis": "Passenger KPIs",
    "pipeline_kpis": "Pipeline KPIs",
    "quality_kpis": "Quality KPIs",
    "safety_kpis": "Safety KPIs",
}
if GOLD_DIR.exists():
    for f in sorted(GOLD_DIR.glob("*.parquet")):
        try:
            mtime = os.path.getmtime(f)
            age_min = (time.time() - mtime) / 60.0
            status_label, emoji = _freshness_status(age_min)
            freshness_rows.append({
                "Table": _TABLE_LABELS.get(f.stem, f.stem.replace("_", " ").title()),
                "Last Modified": datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "Age (min)": round(age_min, 1),
                "Status": f"{emoji} {status_label}",
            })
        except OSError:
            freshness_rows.append({"Table": f.stem, "Last Modified": "N/A", "Age (min)": None, "Status": "🔴 Error"})

if freshness_rows:
    st.markdown("""
    <style>
        [data-testid="stDataFrame"] {
            background-color: transparent !important;
        }
        [data-testid="stDataFrame"] iframe {
            background-color: transparent !important;
        }
    </style>
    """, unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(freshness_rows), use_container_width=True, hide_index=True)
else:
    st.info("No gold parquet files found.")

# ---------- 5. Environmental Compliance ----------
st.markdown(section_header("Environmental Compliance", "leaf"), unsafe_allow_html=True)

env_df = load_parquet(str(SILVER_DIR / "environmental.parquet"))

# Compute overall compliance from silver data
compliance_pct = 0.0
if env_df is not None and not env_df.empty:
    _total_checks = 0
    _total_in_bounds = 0
    for _col, (_lo, _hi) in ENV_BOUNDS.items():
        if _col in env_df.columns:
            _vals = env_df[_col].dropna()
            _total_checks += len(_vals)
            _total_in_bounds += int(((_vals >= _lo) & (_vals <= _hi)).sum())
    compliance_pct = round(_total_in_bounds / _total_checks * 100, 1) if _total_checks else 0.0

st.markdown("**Parameter Compliance Breakdown**")
if env_df is not None and not env_df.empty:
    bounds_info: list[dict] = []
    for col, (lo, hi) in ENV_BOUNDS.items():
        if col in env_df.columns:
            total = env_df[col].dropna().shape[0]
            in_bounds = ((env_df[col] >= lo) & (env_df[col] <= hi)).sum()
            pct = round(in_bounds / total * 100, 1) if total else 0
            bounds_info.append({"Parameter": col, "In Bounds": int(in_bounds), "Total": total, "Compliance %": pct})
    _PARAM_LABELS = {
        "temperature_c": "Temperature (°C)",
        "humidity_pct": "Humidity (%)",
        "co2_ppm": "CO₂ (ppm)",
        "air_quality_index": "Air Quality Index",
    }
    if bounds_info:
        bounds_df = pd.DataFrame(bounds_info)
        bounds_df["Parameter"] = bounds_df["Parameter"].map(
            lambda p: _PARAM_LABELS.get(p, p.replace("_", " ").title())
        )
        st.dataframe(bounds_df, use_container_width=True, hide_index=True)
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
        return "🟢 Good"
    elif val >= yellow_thresh:
        return "🟡 Warning"
    return "🔴 Critical"


# Pipeline KPIs
pipeline = system.get("pipeline", {})
if pipeline:
    kpi_rows.append({
        "KPI Name": "Pipeline Success Rate",
        "Current Value": f"{pipeline.get('success_rate', 0):.1f}%",
        "Threshold": ">95% Green, >85% Yellow",
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
                "Threshold": ">95% Green, >85% Yellow",
                "Status": _status_icon(score, 95, 85),
            })

# Flight KPIs
flights = system.get("flights", {})
if flights:
    otp = flights.get("otp_pct", 0)
    kpi_rows.append({
        "KPI Name": "On-Time Performance",
        "Current Value": f"{otp:.1f}%",
        "Threshold": ">90% Green, >80% Yellow",
        "Status": _status_icon(otp, 90, 80),
    })

# Passenger KPIs
passengers = system.get("passengers", {})
if passengers:
    avg_wait = passengers.get("avg_wait_min", 0)
    # Lower is better: ≤15 min green, ≤25 min yellow, >25 min red
    wait_status = "🟢 Good" if avg_wait <= 15 else ("🟡 Warning" if avg_wait <= 25 else "🔴 Critical")
    kpi_rows.append({
        "KPI Name": "Average Wait Time",
        "Current Value": f"{avg_wait:.1f} min",
        "Threshold": "≤15 min Green, ≤25 min Yellow",
        "Status": wait_status,
    })

# Safety KPIs
safety = system.get("safety", {})
if safety:
    res = safety.get("resolution_rate_pct", 0)
    kpi_rows.append({
        "KPI Name": "Safety Alert Resolution",
        "Current Value": f"{res:.1f}%",
        "Threshold": ">95% Green, >85% Yellow",
        "Status": _status_icon(res, 95, 85),
    })

# Environmental compliance
kpi_rows.append({
    "KPI Name": "Environmental Compliance",
    "Current Value": f"{compliance_pct:.1f}%",
    "Threshold": ">95% Green, >85% Yellow",
    "Status": _status_icon(compliance_pct, 95, 85),
})

if kpi_rows:
    st.dataframe(pd.DataFrame(kpi_rows), use_container_width=True, hide_index=True)
else:
    st.info("No KPI data available — run the pipeline first.")
