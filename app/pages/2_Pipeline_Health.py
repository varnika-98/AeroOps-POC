"""Pipeline Health & Logs dashboard page for AeroOps AI."""

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.theme import COLORS, SVG_ICONS, apply_theme, metric_card, page_header, page_loader, section_header
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
st.markdown(page_loader(duration=0.5), unsafe_allow_html=True)
st.markdown(page_header("Pipeline Health & Logs", SVG_ICONS["wrench"]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top metrics row
# ---------------------------------------------------------------------------

logs_df = load_pipeline_logs()
pipeline_kpis_df = load_pipeline_kpis()

# Filter out aggregate "all" rows — they double-count records and have broken quality_score=0.0
if logs_df is not None:
    logs_df = logs_df[logs_df["stream"] != "all"].reset_index(drop=True)

if logs_df is not None:
    # Derive run_id from timestamp (each unique timestamp = one pipeline run)
    logs_df["run_timestamp"] = pd.to_datetime(logs_df["run_timestamp"])
    logs_df["run_id"] = logs_df["run_timestamp"].dt.strftime("%Y%m%d_%H%M%S")
    # Derive status: quality_score == 1.0 → success, else partial
    logs_df["status"] = logs_df["quality_score"].apply(lambda q: "success" if q >= 1.0 else "partial")

    total_runs = logs_df["run_id"].nunique()
    success_runs = logs_df[
        (logs_df["stage"] == "gold") | (logs_df["status"] == "success")
    ]["run_id"].nunique() if "stage" in logs_df.columns else total_runs
    success_rate = round(success_runs / total_runs * 100, 1) if total_runs > 0 else 0
    avg_duration = round(logs_df["duration_sec"].mean(), 1) if "duration_sec" in logs_df.columns else 0
    total_records = int(logs_df["total_records"].sum()) if "total_records" in logs_df.columns else 0
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
st.markdown(section_header("Pipeline Run Timeline", "calendar"), unsafe_allow_html=True)

if logs_df is not None and all(c in logs_df.columns for c in ["run_timestamp", "duration_sec", "stream"]):
    heat_df = logs_df.copy()
    heat_df["Run #"] = heat_df.groupby("stream").cumcount() + 1
    heat_df["Stream"] = heat_df["stream"].str.title()
    pivot = heat_df.pivot_table(index="Stream", columns="Run #", values="duration_sec", aggfunc="mean")
    fig_timeline = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"Run {c}" for c in pivot.columns],
        y=pivot.index,
        colorscale=[[0, "#E8F0FE"], [0.5, "#4682B4"], [1, "#1B2A4A"]],
        text=[[f"{v * 1000:.0f}ms" if pd.notna(v) else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        hovertemplate="Stream: %{y}<br>%{x}<br>Duration: %{text}<extra></extra>",
        colorbar=dict(title="Duration (sec)"),
    ))
    fig_timeline.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif", color=COLORS["navy"]),
        title=dict(text="Pipeline Duration Heatmap", font=dict(size=16, color=COLORS["navy"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
        margin=dict(l=40, r=20, t=50, b=40),
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
    st.markdown(section_header("Success / Failure Trend", "chart_up"), unsafe_allow_html=True)
    if logs_df is not None and "run_timestamp" in logs_df.columns and "status" in logs_df.columns:
        trend_df = logs_df.copy()
        trend_df["run_timestamp"] = pd.to_datetime(trend_df["run_timestamp"])
        trend_df["hour"] = trend_df["run_timestamp"].dt.floor("h")
        pivot = trend_df.groupby(["hour", "status"]).size().unstack(fill_value=0).reset_index()
        pivot["hour"] = pivot["hour"].dt.strftime("%b %d, %H:%M")

        _STATUS_COLORS = {"success": "#1B2A4A", "partial": "#4682B4", "failed": "#e74c3c"}
        _STATUS_LABELS = {"success": "Success", "partial": "Partial", "failed": "Failed"}
        status_cols = [c for c in pivot.columns if c != "hour"]
        if status_cols:
            fig_trend = go.Figure()
            for col in status_cols:
                fig_trend.add_trace(go.Bar(
                    x=pivot["hour"], y=pivot[col],
                    name=_STATUS_LABELS.get(col, col.title()),
                    marker_color=_STATUS_COLORS.get(col, "#4682B4"),
                    width=0.22,
                ))
            fig_trend.update_layout(
                barmode="group", bargap=0.35, bargroupgap=0.05,
                height=380,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=20, t=40, b=40),
                font=dict(family="system-ui", size=12, color=COLORS["navy"]),
                title=dict(text="Runs by Status Over Time", font=dict(size=14, color=COLORS["navy"])),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", title="Runs"),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No status data to plot.")
    else:
        st.info("Pipeline log data not available.")

with col_right:
    st.markdown(section_header("Duration by Stage", "clock"), unsafe_allow_html=True)
    if logs_df is not None and all(c in logs_df.columns for c in ["stage", "stream", "duration_sec"]):
        dur_df = logs_df[logs_df["stage"] == "silver"].groupby("stream")["duration_sec"].mean().reset_index()
        dur_df["stream"] = dur_df["stream"].str.title()
        dur_df.columns = ["Stream", "Avg Duration (sec)"]

        fig_dur = go.Figure()
        fig_dur.add_trace(go.Bar(
            x=dur_df["Stream"], y=dur_df["Avg Duration (sec)"],
            marker_color="#4682B4", width=0.22,
            text=[f"{v:.3f}s" for v in dur_df["Avg Duration (sec)"]],
            textposition="outside", textfont=dict(size=11, color=COLORS["navy"]),
        ))
        fig_dur.update_layout(
            barmode="group", bargap=0.35,
            height=380,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=20, t=40, b=40),
            font=dict(family="system-ui", size=12, color=COLORS["navy"]),
            title=dict(text="Avg Silver Stage Duration per Stream", font=dict(size=14, color=COLORS["navy"])),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", title="Duration (sec)"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_dur, use_container_width=True)
    else:
        st.info("Duration data not available.")

# ---------------------------------------------------------------------------
# Throughput per Stream (multi-line)
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(section_header("Throughput per Stream", "rocket"), unsafe_allow_html=True)

if logs_df is not None and all(c in logs_df.columns for c in ["run_timestamp", "stream", "total_records"]):
    tp_df = logs_df.copy()
    tp_df["run_timestamp"] = pd.to_datetime(tp_df["run_timestamp"])
    tp_df["Stream"] = tp_df["stream"].str.title()
    fig_tp = px.line(
        tp_df, x="run_timestamp", y="total_records", color="Stream",
        title="Records per Stream Over Time",
        markers=True,
    )
    fig_tp.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(family="system-ui", size=12, color=COLORS["navy"]),
        title=dict(font=dict(size=14, color=COLORS["navy"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", title="Records Processed"),
        xaxis=dict(showgrid=False, title="Run Timestamp", tickformat="%b %d, %H:%M", nticks=8),
    )
    st.plotly_chart(fig_tp, use_container_width=True)
else:
    st.info("Throughput data not available.")

# ---------------------------------------------------------------------------
# Log Viewer
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(section_header("Pipeline Log Viewer", "clipboard"), unsafe_allow_html=True)

if logs_df is not None:
    display_cols = [
        "run_id", "run_timestamp", "stage", "stream", "status",
        "total_records", "passed", "failed", "quality_score", "duration_sec",
    ]
    display_cols = [c for c in display_cols if c in logs_df.columns]
    viewer_df = logs_df[display_cols].copy()

    # Capitalize values
    for col in ["stream", "stage", "status"]:
        if col in viewer_df.columns:
            viewer_df[col] = viewer_df[col].str.title()

    # Rename columns to readable labels
    _COL_LABELS = {
        "run_id": "Run ID",
        "run_timestamp": "Timestamp",
        "stage": "Stage",
        "stream": "Stream",
        "status": "Status",
        "total_records": "Total Records",
        "passed": "Passed",
        "failed": "Failed",
        "quality_score": "Quality Score",
        "duration_sec": "Duration (sec)",
    }
    viewer_df = viewer_df.rename(columns=_COL_LABELS)

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        streams = ["All"] + sorted(viewer_df["Stream"].dropna().unique().tolist()) if "Stream" in viewer_df.columns else ["All"]
        selected_stream = st.selectbox("Stream", streams, key="log_stream")

    with fcol2:
        statuses = ["All"] + sorted(viewer_df["Status"].dropna().unique().tolist()) if "Status" in viewer_df.columns else ["All"]
        selected_status = st.selectbox("Status", statuses, key="log_status")

    with fcol3:
        stages = ["All"] + sorted(viewer_df["Stage"].dropna().unique().tolist()) if "Stage" in viewer_df.columns else ["All"]
        selected_stage = st.selectbox("Stage", stages, key="log_stage")

    if selected_stream != "All":
        viewer_df = viewer_df[viewer_df["Stream"] == selected_stream]
    if selected_status != "All":
        viewer_df = viewer_df[viewer_df["Status"] == selected_status]
    if selected_stage != "All":
        viewer_df = viewer_df[viewer_df["Stage"] == selected_stage]

    st.dataframe(viewer_df.reset_index(drop=True), use_container_width=True, height=400)
else:
    st.info("No pipeline logs found.")
