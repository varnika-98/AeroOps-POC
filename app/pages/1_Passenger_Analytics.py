"""Flight & Passenger Analytics dashboard page for AeroOps AI."""

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.theme import COLORS, SVG_ICONS, apply_theme, metric_card, page_header, page_loader, section_header
from utils.charts import gauge_chart, time_series_chart, bar_chart, funnel_chart
from utils.kpi_calculator import get_flight_kpis, get_passenger_kpis

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_flight_kpis():
    path = os.path.join(DATA_ROOT, "gold", "flight_kpis.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


@st.cache_data(ttl=60)
def load_flights():
    path = os.path.join(DATA_ROOT, "silver", "flights.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


@st.cache_data(ttl=60)
def load_passengers():
    path = os.path.join(DATA_ROOT, "silver", "passengers.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


@st.cache_data(ttl=60)
def load_cargo():
    path = os.path.join(DATA_ROOT, "silver", "cargo.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Passenger Analytics", page_icon="✈️", layout="wide")
apply_theme(st)
st.markdown(page_loader(duration=0.5), unsafe_allow_html=True)
st.markdown(page_header("Passenger Analytics", SVG_ICONS["flights"]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top metrics row
# ---------------------------------------------------------------------------

flight_kpi = get_flight_kpis()
passenger_kpi = get_passenger_kpis()

otp_pct = flight_kpi.get("otp_pct", 0)
total_flights = flight_kpi.get("total_flights", 0)
avg_delay = flight_kpi.get("avg_delay_min", 0)
throughput = passenger_kpi.get("throughput_per_hour", 0)

otp_status = "healthy" if otp_pct >= 80 else ("warning" if otp_pct >= 60 else "critical")
delay_status = "healthy" if avg_delay <= 10 else ("warning" if avg_delay <= 20 else "critical")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.plotly_chart(
        gauge_chart(otp_pct, "Flight OTP %", max_val=100, thresholds={"warning": 80, "critical": 60}),
        use_container_width=True,
    )

with col2:
    st.markdown(metric_card("Total Flights", f"{total_flights:,}"), unsafe_allow_html=True)

with col3:
    st.markdown(
        metric_card("Avg Delay (min)", f"{avg_delay:.1f}", status=delay_status),
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        metric_card("Passenger Throughput", f"{throughput:,.0f} pax/hr"),
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Flight OTP Trend
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(section_header("Flight OTP Trend", "chart_up"), unsafe_allow_html=True)

flight_kpis_df = load_flight_kpis()
if flight_kpis_df is not None and "hour" in flight_kpis_df.columns and "otp_pct" in flight_kpis_df.columns:
    fig_otp = time_series_chart(flight_kpis_df, "hour", "otp_pct", "On-Time Performance % by Hour")
    fig_otp.add_hline(y=80, line_dash="dash", line_color=COLORS["danger_red"], annotation_text="80% Target")
    fig_otp.update_layout(height=350)
    st.plotly_chart(fig_otp, use_container_width=True)
else:
    st.info("Flight KPI data not available.")

# ---------------------------------------------------------------------------
# Delay Distribution & Flight Status Breakdown
# ---------------------------------------------------------------------------

st.markdown("---")
col_left, col_right = st.columns(2)

flights_df = load_flights()

with col_left:
    st.markdown(section_header("Delay Distribution", "bar_chart"), unsafe_allow_html=True)
    if flights_df is not None and "delay_minutes" in flights_df.columns:
        fig_hist = px.histogram(
            flights_df, x="delay_minutes", nbins=40,
            title="Distribution of Flight Delays",
            color_discrete_sequence=[COLORS["sky_blue"]],
        )
        fig_hist.update_layout(
            xaxis_title="Delay (minutes)", yaxis_title="Count",
            plot_bgcolor=COLORS["white"], paper_bgcolor=COLORS["white"],
            height=350,
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("Flight delay data not available.")

with col_right:
    st.markdown(section_header("Flight Status Breakdown", "target"), unsafe_allow_html=True)
    if flights_df is not None and "status" in flights_df.columns:
        status_counts = flights_df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig_pie = px.pie(
            status_counts, names="status", values="count",
            title="Flight Status Distribution",
            color_discrete_sequence=[
                COLORS["sky_blue"], COLORS["success_green"], COLORS["safety_orange"],
                COLORS["warning_yellow"], COLORS["danger_red"], COLORS["navy"],
            ],
        )
        fig_pie.update_layout(
            plot_bgcolor=COLORS["white"], paper_bgcolor=COLORS["white"],
            height=350,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Flight status data not available.")

# ---------------------------------------------------------------------------
# Passenger Flow Section
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(section_header("Passenger Flow", "passengers"), unsafe_allow_html=True)

passengers_df = load_passengers()

col_cp, col_tp = st.columns(2)

with col_cp:
    st.markdown("**Checkpoint Wait Times**")
    if passengers_df is not None and "checkpoint" in passengers_df.columns and "wait_time_minutes" in passengers_df.columns:
        avg_wait = (
            passengers_df.groupby("checkpoint")["wait_time_minutes"]
            .mean()
            .reset_index()
            .rename(columns={"wait_time_minutes": "avg_wait_min"})
            .sort_values("avg_wait_min", ascending=False)
        )
        fig_wait = bar_chart(avg_wait, "checkpoint", "avg_wait_min", "Avg Wait Time per Checkpoint", color=COLORS["safety_orange"])
        fig_wait.update_layout(height=350)
        st.plotly_chart(fig_wait, use_container_width=True)
    else:
        st.info("Passenger checkpoint data not available.")

with col_tp:
    st.markdown("**Throughput vs Capacity**")
    if passengers_df is not None and "throughput_per_hour" in passengers_df.columns and "timestamp" in passengers_df.columns:
        tp_df = passengers_df.copy()
        tp_df["timestamp"] = pd.to_datetime(tp_df["timestamp"])
        tp_hourly = tp_df.set_index("timestamp").resample("h")["throughput_per_hour"].mean().reset_index()
        fig_tp = time_series_chart(tp_hourly, "timestamp", "throughput_per_hour", "Throughput per Hour", color=COLORS["success_green"])
        fig_tp.add_hline(y=2000, line_dash="dash", line_color=COLORS["danger_red"], annotation_text="Capacity: 2000")
        fig_tp.update_layout(height=350)
        st.plotly_chart(fig_tp, use_container_width=True)
    else:
        st.info("Passenger throughput data not available.")

# ---------------------------------------------------------------------------
# Baggage Processing Funnel
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(section_header("Baggage Processing Funnel", "cargo"), unsafe_allow_html=True)

cargo_df = load_cargo()
if cargo_df is not None and "status" in cargo_df.columns:
    stage_order = ["checked_in", "in_transit", "loaded", "delivered"]
    status_counts_cargo = cargo_df["status"].value_counts()
    labels = [s for s in stage_order if s in status_counts_cargo.index]
    values = [int(status_counts_cargo[s]) for s in labels]
    if labels:
        fig_funnel = funnel_chart(labels, values, "Baggage Processing Pipeline")
        fig_funnel.update_layout(height=350)
        st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.info("No matching baggage status stages found.")
else:
    st.info("Cargo data not available.")
