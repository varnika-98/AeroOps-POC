"""AI Performance Monitor — LLM usage analytics, latency, tokens & cost tracking."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai.claude_client import load_ai_metrics
from utils.kpi_calculator import get_ai_kpis
from utils.theme import COLORS, SVG_ICONS, apply_theme, page_header, section_header, metric_card

# ---------------------------------------------------------------------------
# Page config & theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Performance Monitor | AeroOps AI", page_icon="📊", layout="wide")
apply_theme(st)
st.markdown(page_header("AI Performance Monitor", SVG_ICONS["pulse"]), unsafe_allow_html=True)
st.caption("LLM usage analytics — latency, token consumption & cost tracking")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
ai_kpis = get_ai_kpis()
ai_metrics_raw = load_ai_metrics()
success_metrics = [m for m in ai_metrics_raw if m.get("status") == "success"]
error_metrics = [m for m in ai_metrics_raw if m.get("status") == "error"]

if ai_kpis.get("status") == "no_data":
    st.info("📭 No AI metrics recorded yet. Use the **AI Ops Center** page to run a diagnosis, get recommendations, or chat — metrics will appear here automatically.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. KPI Cards
# ---------------------------------------------------------------------------
st.markdown(section_header("Overview", "robot"), unsafe_allow_html=True)

kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)
with kpi_c1:
    st.markdown(metric_card("Total Requests", str(ai_kpis["total_requests"])), unsafe_allow_html=True)
with kpi_c2:
    latency_status = "healthy" if ai_kpis["avg_latency_sec"] < 5 else ("warning" if ai_kpis["avg_latency_sec"] < 10 else "critical")
    st.markdown(metric_card("Avg Latency", f"{ai_kpis['avg_latency_sec']:.2f}s", status=latency_status), unsafe_allow_html=True)
with kpi_c3:
    st.markdown(metric_card("Total Tokens", f"{ai_kpis['total_tokens']:,}"), unsafe_allow_html=True)
with kpi_c4:
    st.markdown(metric_card("Total Cost", f"${ai_kpis['total_cost_usd']:.4f}"), unsafe_allow_html=True)
with kpi_c5:
    err_status = "healthy" if ai_kpis["error_rate_pct"] < 5 else ("warning" if ai_kpis["error_rate_pct"] < 20 else "critical")
    st.markdown(metric_card("Error Rate", f"{ai_kpis['error_rate_pct']:.1f}%", status=err_status), unsafe_allow_html=True)

# Model & backend info
st.caption(f"🤖 Model: **{ai_kpis['model']}** · Backend: **{ai_kpis['backend']}** · Avg tokens/request: **{ai_kpis['avg_tokens_per_request']:,}**")

# ---------------------------------------------------------------------------
# 2. Charts Row 1 — Latency Trend + Token Usage by Type
# ---------------------------------------------------------------------------
st.markdown("---")
chart_c1, chart_c2 = st.columns(2)

with chart_c1:
    st.markdown(section_header("Response Latency Trend", "stethoscope"), unsafe_allow_html=True)
    if success_metrics:
        latency_df = pd.DataFrame(success_metrics)
        latency_df["timestamp"] = pd.to_datetime(latency_df["timestamp"])
        latency_df = latency_df.sort_values("timestamp")
        fig_lat = go.Figure()
        fig_lat.add_trace(go.Scatter(
            x=latency_df["timestamp"], y=latency_df["latency_sec"],
            mode="lines+markers", name="Latency",
            line=dict(color="#4682B4", width=2),
            marker=dict(size=6, color=[
                COLORS["success_green"] if l < 3 else (COLORS["warning_yellow"] if l < 6 else COLORS["danger_red"])
                for l in latency_df["latency_sec"]
            ]),
        ))
        fig_lat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=320, margin=dict(l=40, r=20, t=20, b=40),
            yaxis=dict(title="Seconds", showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
            xaxis=dict(showgrid=False),
            font=dict(family="system-ui", color=COLORS["navy"]),
        )
        st.plotly_chart(fig_lat, use_container_width=True)
    else:
        st.info("No successful calls to chart yet.")

with chart_c2:
    st.markdown(section_header("Token Usage by Prompt Type", "robot"), unsafe_allow_html=True)
    by_type = ai_kpis.get("by_prompt_type", {})
    if by_type:
        types = list(by_type.keys())
        input_tok = [by_type[t].get("input_tokens", 0) for t in types]
        output_tok = [by_type[t].get("output_tokens", 0) for t in types]

        fig_usage = go.Figure()
        fig_usage.add_trace(go.Bar(
            x=types, y=input_tok, name="Input Tokens",
            marker_color="#0D3B66",
            text=[f"{t:,}" for t in input_tok], textposition="outside",
            textfont=dict(size=10),
        ))
        fig_usage.add_trace(go.Bar(
            x=types, y=output_tok, name="Output Tokens",
            marker_color="#1A8FA8",
            text=[f"{t:,}" for t in output_tok], textposition="outside",
            textfont=dict(size=10),
        ))
        max_val = max(max(input_tok, default=0), max(output_tok, default=0))
        fig_usage.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=320, margin=dict(l=40, r=20, t=20, b=40),
            yaxis=dict(title="Tokens", showgrid=True, gridcolor="rgba(0,0,0,0.06)",
                       range=[0, max_val * 1.4] if max_val else None),
            xaxis=dict(showgrid=False),
            font=dict(family="system-ui", color=COLORS["navy"]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_usage, use_container_width=True)
    else:
        st.info("No prompt type breakdown available yet.")

# ---------------------------------------------------------------------------
# 3. Charts Row 2 — Cost Breakdown + Request Count by Type
# ---------------------------------------------------------------------------
st.markdown("---")
chart_c3, chart_c4 = st.columns(2)

with chart_c3:
    st.markdown(section_header("Cost by Prompt Type", "robot"), unsafe_allow_html=True)
    if by_type:
        types = list(by_type.keys())
        costs = [round(by_type[t]["cost"], 4) for t in types]
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Pie(
            labels=types, values=costs,
            marker=dict(colors=["#0D3B66", "#14668A", "#1A8FA8", "#28B5C4"][:len(types)]),
            textinfo="label+percent", textfont=dict(size=12, color="white"),
            hole=0.4,
        ))
        fig_cost.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=320, margin=dict(l=20, r=20, t=20, b=20),
            font=dict(family="system-ui", color=COLORS["navy"]),
            showlegend=False,
            annotations=[dict(text=f"${sum(costs):.4f}", x=0.5, y=0.5,
                              font_size=16, font_color=COLORS["navy"], showarrow=False)],
        )
        st.plotly_chart(fig_cost, use_container_width=True)

with chart_c4:
    st.markdown(section_header("Requests by Prompt Type", "robot"), unsafe_allow_html=True)
    if by_type:
        types = list(by_type.keys())
        counts = [by_type[t]["count"] for t in types]
        fig_counts = go.Figure()
        fig_counts.add_trace(go.Bar(
            x=types, y=counts, name="Requests",
            marker_color=["#0D3B66", "#14668A", "#1A8FA8", "#28B5C4"][:len(types)],
            text=counts, textposition="outside",
            textfont=dict(size=12, color=COLORS["navy"]),
            width=0.5,
        ))
        fig_counts.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=320, margin=dict(l=40, r=20, t=20, b=40),
            yaxis=dict(title="Count", showgrid=True, gridcolor="rgba(0,0,0,0.06)",
                       range=[0, max(counts) * 1.4] if counts else None),
            xaxis=dict(showgrid=False),
            font=dict(family="system-ui", color=COLORS["navy"]),
            showlegend=False, bargap=0.35,
        )
        st.plotly_chart(fig_counts, use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Detailed Metrics Table
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(section_header("Call Log", "robot"), unsafe_allow_html=True)

if ai_metrics_raw:
    log_df = pd.DataFrame(ai_metrics_raw)
    log_df["timestamp"] = pd.to_datetime(log_df["timestamp"])
    log_df = log_df.sort_values("timestamp", ascending=False)

    display_cols = ["timestamp", "prompt_type", "status", "latency_sec",
                    "input_tokens", "output_tokens", "total_tokens", "cost_usd", "model"]
    display_cols = [c for c in display_cols if c in log_df.columns]

    st.dataframe(
        log_df[display_cols].style.format({
            "latency_sec": "{:.2f}",
            "cost_usd": "${:.6f}",
        }),
        use_container_width=True,
        height=300,
    )
