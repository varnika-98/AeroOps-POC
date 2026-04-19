"""Pipeline Health & Logs dashboard page for AeroOps AI."""

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.theme import COLORS, apply_theme, metric_card, page_header
from utils.charts import stacked_bar_chart, time_series_chart
from utils.kpi_calculator import get_pipeline_health

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_pipeline_logs():
    path = os.path.join(DATA_ROOT, "logs", "pipeline_logs.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


@st.cache_data(ttl=60)
def load_pipeline_kpis():
    path = os.path.join(DATA_ROOT, "gold", "pipeline_kpis.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Pipeline Health & Logs", page_icon="🔧", layout="wide")
apply_theme(st)
st.markdown(page_header("Pipeline Health & Logs", "🔧"), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top metrics row
# ---------------------------------------------------------------------------

logs_df = load_pipeline_logs()
pipeline_kpis_df = load_pipeline_kpis()

if logs_df is not None:
    total_runs = logs_df["run_id"].nunique()
    success_runs = logs_df[logs_df["status"] == "success"]["run_id"].nunique()
    success_rate = round(success_runs / total_runs * 100, 1) if total_runs > 0 else 0
    avg_duration = round(logs_df["duration_sec"].mean(), 1) if "duration_sec" in logs_df.columns else 0
    total_records = int(logs_df["records_in"].sum()) if "records_in" in logs_df.columns else 0
else:
    total_runs = success_rate = avg_duration = total_records = 0

rate_status = "healthy" if success_rate >= 95 else ("warning" if success_rate >= 80 else "critical")
dur_status = "healthy" if avg_duration <= 20 else ("warning" if avg_duration <= 40 else "critical")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        metric_card("Pipeline Success Rate", f"{success_rate}%", status=rate_status),
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(metric_card("Total Runs", f"{total_runs:,}"), unsafe_allow_html=True)

with col3:
    st.markdown(
        metric_card("Avg Duration (sec)", f"{avg_duration:.1f}", status=dur_status),
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(metric_card("Records Processed", f"{total_records:,}"), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pipeline Run Timeline (Gantt-style)
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("🗓️ Pipeline Run Timeline")

if logs_df is not None and all(c in logs_df.columns for c in ["timestamp", "duration_sec", "stream", "status"]):
    timeline_df = logs_df.copy()
    timeline_df["Start"] = pd.to_datetime(timeline_df["timestamp"])
    timeline_df["Finish"] = timeline_df["Start"] + pd.to_timedelta(timeline_df["duration_sec"], unit="s")
    timeline_df["Stream"] = timeline_df["stream"]
    timeline_df["Status"] = timeline_df["status"]

    color_map = {"success": COLORS["success_green"], "failed": COLORS["danger_red"], "partial": COLORS["warning_yellow"]}
    fig_timeline = px.timeline(
        timeline_df, x_start="Start", x_end="Finish", y="Stream", color="Status",
        color_discrete_map=color_map,
        title="Pipeline Runs by Stream",
    )
    fig_timeline.update_yaxes(autorange="reversed")
    fig_timeline.update_layout(
        plot_bgcolor=COLORS["white"], paper_bgcolor=COLORS["white"],
        height=400,
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    st.info("Pipeline log data not available for timeline.")

# ---------------------------------------------------------------------------
# Success/Failure Trend & Duration by Stage
# ---------------------------------------------------------------------------

st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 Success / Failure Trend")
    if logs_df is not None and "timestamp" in logs_df.columns and "status" in logs_df.columns:
        trend_df = logs_df.copy()
        trend_df["timestamp"] = pd.to_datetime(trend_df["timestamp"])
        trend_df["hour"] = trend_df["timestamp"].dt.floor("h")
        pivot = trend_df.groupby(["hour", "status"]).size().unstack(fill_value=0).reset_index()
        status_cols = [c for c in pivot.columns if c != "hour"]
        if status_cols:
            fig_trend = stacked_bar_chart(
                pivot, "hour", status_cols, "Runs by Status Over Time",
                colors=[
                    COLORS["success_green"], COLORS["danger_red"],
                    COLORS["warning_yellow"], COLORS["sky_blue"],
                ],
            )
            fig_trend.update_layout(height=380)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No status data to plot.")
    else:
        st.info("Pipeline log data not available.")

with col_right:
    st.subheader("⏱️ Duration by Stage")
    if logs_df is not None and all(c in logs_df.columns for c in ["stage", "stream", "duration_sec"]):
        dur_df = logs_df.groupby(["stream", "stage"])["duration_sec"].mean().reset_index()
        fig_dur = px.bar(
            dur_df, x="stream", y="duration_sec", color="stage", barmode="group",
            title="Avg Duration per Stage by Stream",
            color_discrete_sequence=[
                COLORS["sky_blue"], COLORS["success_green"], COLORS["safety_orange"],
                COLORS["navy"], COLORS["warning_yellow"],
            ],
        )
        fig_dur.update_layout(
            plot_bgcolor=COLORS["white"], paper_bgcolor=COLORS["white"],
            height=380,
        )
        st.plotly_chart(fig_dur, use_container_width=True)
    else:
        st.info("Duration data not available.")

# ---------------------------------------------------------------------------
# Throughput per Stream (multi-line)
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("🚀 Throughput per Stream")

if logs_df is not None and all(c in logs_df.columns for c in ["timestamp", "stream", "records_in"]):
    tp_df = logs_df.copy()
    tp_df["timestamp"] = pd.to_datetime(tp_df["timestamp"])
    fig_tp = px.line(
        tp_df, x="timestamp", y="records_in", color="stream",
        title="Records In per Stream Over Time",
        markers=True,
    )
    fig_tp.update_layout(
        plot_bgcolor=COLORS["white"], paper_bgcolor=COLORS["white"],
        height=380,
    )
    st.plotly_chart(fig_tp, use_container_width=True)
else:
    st.info("Throughput data not available.")

# ---------------------------------------------------------------------------
# Log Viewer
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("📋 Pipeline Log Viewer")

if logs_df is not None:
    display_cols = [
        "run_id", "timestamp", "stage", "stream", "status",
        "records_in", "records_out", "duration_sec", "error_message",
    ]
    display_cols = [c for c in display_cols if c in logs_df.columns]
    viewer_df = logs_df[display_cols].copy()

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        streams = ["All"] + sorted(viewer_df["stream"].dropna().unique().tolist()) if "stream" in viewer_df.columns else ["All"]
        selected_stream = st.selectbox("Stream", streams, key="log_stream")

    with fcol2:
        statuses = ["All"] + sorted(viewer_df["status"].dropna().unique().tolist()) if "status" in viewer_df.columns else ["All"]
        selected_status = st.selectbox("Status", statuses, key="log_status")

    with fcol3:
        stages = ["All"] + sorted(viewer_df["stage"].dropna().unique().tolist()) if "stage" in viewer_df.columns else ["All"]
        selected_stage = st.selectbox("Stage", stages, key="log_stage")

    if selected_stream != "All":
        viewer_df = viewer_df[viewer_df["stream"] == selected_stream]
    if selected_status != "All":
        viewer_df = viewer_df[viewer_df["status"] == selected_status]
    if selected_stage != "All":
        viewer_df = viewer_df[viewer_df["stage"] == selected_stage]

    st.dataframe(viewer_df.reset_index(drop=True), use_container_width=True, height=400)
else:
    st.info("No pipeline logs found.")
