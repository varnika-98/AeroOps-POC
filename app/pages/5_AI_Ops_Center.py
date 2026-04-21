"""AI Ops Center — AeroOps AI real-time diagnostics and chat interface."""

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from ai.claude_client import ClaudeClient
from ai.context_builder import build_ai_context, format_context_for_prompt
from utils.theme import COLORS, STREAM_ICONS, SVG_ICONS, apply_theme, page_header, page_loader, section_header, inline_svg, stream_svg, status_svg

# ---------------------------------------------------------------------------
# Page config & theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Ops Center | AeroOps AI", page_icon="🤖", layout="wide")
apply_theme(st)
st.markdown(page_loader(duration=0.5), unsafe_allow_html=True)
st.markdown(page_header("AI Ops Center", SVG_ICONS["robot"]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "ai_context" not in st.session_state:
    st.session_state.ai_context = None
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_api_key() -> bool:
    """Return True when any LLM backend (Ollama or Claude) is available."""
    try:
        client = ClaudeClient()
        return client._has_client()
    except Exception:
        return False


def _determine_severity(context: dict) -> str:
    """Classify overall system health from context data.

    Returns 'critical', 'warning', or 'healthy'.
    """
    if context is None:
        return "healthy"

    # Check for pipeline failures
    anomalies = context.get("anomalies", {})
    failure_count = anomalies.get("count", 0) if isinstance(anomalies, dict) else 0

    # Check KPI breaches
    kpis = context.get("kpi_summary", {})
    warning_kpis = sum(
        1
        for info in kpis.values()
        if isinstance(info, dict) and info.get("status") == "warning"
    )

    pipeline = context.get("pipeline_health", {})
    success_rate = pipeline.get("success_rate", 100) if isinstance(pipeline, dict) else 100

    if failure_count >= 3 or success_rate < 90 or warning_kpis >= 4:
        return "critical"
    if failure_count >= 1 or success_rate < 99 or warning_kpis >= 1:
        return "warning"
    return "healthy"


_SEVERITY_CONFIG = {
    "healthy": {
        "color": COLORS["success_green"],
        "svg": status_svg("healthy"),
        "label": "All systems operational",
    },
    "warning": {
        "color": COLORS["warning_yellow"],
        "svg": status_svg("warning"),
        "label": "Warnings detected",
    },
    "critical": {
        "color": COLORS["danger_red"],
        "svg": status_svg("critical"),
        "label": "Critical issues detected",
    },
}

# ---------------------------------------------------------------------------
# 1. Build context (always — it's cheap and powers everything)
# ---------------------------------------------------------------------------
try:
    context = build_ai_context()
    st.session_state.ai_context = context
except Exception as exc:
    context = None
    st.warning(f"Could not build system context: {exc}")

severity = _determine_severity(context)
cfg = _SEVERITY_CONFIG[severity]

# ---------------------------------------------------------------------------
# 2. Status Banner
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="
        background-color: {cfg['color']};
        color: {'#000' if severity == 'warning' else '#fff'};
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 1rem;
    ">
        {cfg['svg']}  {cfg['label']}
    </div>
    """,
    unsafe_allow_html=True,
)

# API/LLM guard
api_available = _has_api_key()
if api_available:
    _client_info = ClaudeClient()
    st.caption(f"🤖 AI Backend: **{_client_info._get_backend_label()}**")
else:
    st.warning("⚠️ No LLM backend available. Start **Ollama** locally or set **ANTHROPIC_API_KEY** in `.env`.")

# ---------------------------------------------------------------------------
# 3. System Status Summary — Generate Diagnosis
# ---------------------------------------------------------------------------
st.markdown(section_header("System Diagnosis", "stethoscope"), unsafe_allow_html=True)

if st.button("Generate System Diagnosis", disabled=not api_available):
    with st.spinner("Analyzing system state…"):
        try:
            client = ClaudeClient()
            result = client.diagnose(context)
            st.session_state.diagnosis_result = result
        except Exception as exc:
            st.error(f"Diagnosis failed: {exc}")

if st.session_state.diagnosis_result:
    st.markdown(
        f"""<div style="
            background: {COLORS['white']};
            border-left: 5px solid {COLORS['sky_blue']};
            border-radius: 8px;
            padding: 1.2rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        ">{st.session_state.diagnosis_result}</div>""",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# 4. Incident Analysis — Four Expandable Sections
# ---------------------------------------------------------------------------
st.markdown(section_header("Incident Analysis", "search"), unsafe_allow_html=True)

with st.expander("What Changed?", expanded=False):
    anomalies = context.get("anomalies", {}) if context else {}
    if anomalies.get("status") == "no_data":
        st.info("No anomaly data available.")
    elif anomalies.get("count", 0) == 0:
        st.success("No anomalies detected.")
    else:
        st.warning(f"**{anomalies['count']}** anomalies detected")
        for f in anomalies.get("recent_failures", []):
            icon = stream_svg(f.get("stream", ""), 16)
            quality = f.get("quality_score", "N/A")
            failed = f.get("failed_records", 0)
            total = f.get("total_records", 0)
            stage = f.get("stage", "unknown")
            ts = str(f.get("timestamp", ""))[:19]
            st.markdown(
                f"- {icon} **{f.get('stream', 'unknown')}** / {stage} — "
                f"quality: `{quality}`, failed: `{failed}/{total}`  "
                f"<small>({ts})</small>",
                unsafe_allow_html=True,
            )

with st.expander("What Broke?", expanded=False):
    quality = context.get("quality_issues", {}) if context else {}
    pipeline = context.get("pipeline_health", {}) if context else {}

    if quality.get("status") == "no_quarantine_data" and pipeline.get("status") == "no_data":
        st.info("No failure or quality data available.")
    else:
        # Pipeline failures
        if isinstance(pipeline, dict) and pipeline.get("success_rate") is not None:
            rate = pipeline["success_rate"]
            if rate < 100:
                st.warning(f"Pipeline success rate: **{rate}%**")
            else:
                st.success("Pipeline success rate: **100%**")

        # Quality / quarantine issues
        for stream, info in quality.items():
            if isinstance(info, dict):
                icon = stream_svg(stream, 16)
                st.markdown(
                    f"- {icon} **{stream}**: {info.get('quarantined_records', 0)} quarantined records",
                    unsafe_allow_html=True,
                )
                for reason, count in info.get("top_failure_reasons", {}).items():
                    st.markdown(f"  - _{reason}_: **{count}**")

with st.expander("What's Impacted?", expanded=False):
    impact = context.get("lineage_impact", {}) if context else {}
    kpis = context.get("kpi_summary", {}) if context else {}

    if not impact and not any(
        isinstance(v, dict) and v.get("status") == "warning" for v in kpis.values()
    ):
        st.success("No downstream KPIs impacted.")
    else:
        # Lineage-based impact
        for stream, info in impact.items():
            if isinstance(info, dict):
                st.markdown(f"**Stream `{stream}`** failure impacts:")
                for kpi in info.get("affected_kpis", []):
                    st.markdown(f"  - KPI: `{kpi}`")
                for gold in info.get("affected_gold_tables", []):
                    st.markdown(f"  - Gold table: `{gold}`")

        # KPIs in warning state
        warned = {
            k: v
            for k, v in kpis.items()
            if isinstance(v, dict) and v.get("status") == "warning"
        }
        if warned:
            st.markdown("**KPIs breaching thresholds:**")
            _w_svg = status_svg("warning")
            for name, info in warned.items():
                st.markdown(
                    f"- {_w_svg} **{name}**: {info.get('value')} {info.get('unit', '')} "
                    f"(target: {info.get('target')} {info.get('unit', '')})",
                    unsafe_allow_html=True,
                )
with st.expander("Recommended Actions", expanded=False):
    if not api_available:
        st.info("Enable an LLM backend (Ollama or Claude) to get AI-powered recommendations.")
    elif st.button("Get Recommendations", key="btn_recommend"):
        with st.spinner("Generating recommendations…"):
            try:
                client = ClaudeClient()
                recs = client.recommend(context)
                st.markdown(recs)
            except Exception as exc:
                st.error(f"Failed to fetch recommendations: {exc}")

st.divider()

# ---------------------------------------------------------------------------
# 5. Chat Interface
# ---------------------------------------------------------------------------
st.markdown(section_header("Ask the AI Ops Assistant", "chat"), unsafe_allow_html=True)

# Render chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Starter question buttons — right above chat input
starter_cols = st.columns(6)
starters = [
    "What is the current system health?",
    "Which streams have quality issues?",
    "What KPIs are at risk?",
    "Show recent pipeline failures",
    "Any anomalies detected?",
    "Summarize sensor status",
]
for col, question in zip(starter_cols, starters):
    if col.button(question, key=f"starter_{question}"):
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.rerun()

# Chat input
if user_input := st.chat_input("Ask about system health, KPIs, incidents…"):
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

# Generate assistant reply for the latest unanswered user message
if (
    st.session_state.chat_messages
    and st.session_state.chat_messages[-1]["role"] == "user"
):
    if not api_available:
        assistant_reply = (
            "⚠️ No LLM backend available. Start **Ollama** locally or set "
            "**ANTHROPIC_API_KEY** in `.env` to enable AI-powered responses."
        )
    else:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing…"):
                try:
                    client = ClaudeClient()
                    assistant_reply = client.chat(
                        st.session_state.chat_messages, context
                    )
                except Exception as exc:
                    assistant_reply = f"❌ Error: {exc}"
            st.markdown(assistant_reply)

    st.session_state.chat_messages.append(
        {"role": "assistant", "content": assistant_reply}
    )

# Context panel & New Conversation — only visible when chat has history
if st.session_state.chat_messages:
    ctx_col, clear_col = st.columns([6, 1])
    with ctx_col:
        with st.expander("Show Context Sent to AI", expanded=False):
            if context:
                tab_text, tab_json = st.tabs(["Formatted Text", "Raw JSON"])
                with tab_text:
                    st.code(format_context_for_prompt(context), language="text")
                with tab_json:
                    st.json(context)
            else:
                st.info("No context available — data may not have been generated yet.")
    with clear_col:
        if st.button("➕ New Conversation", key="clear_chat"):
            st.session_state.chat_messages = []
            st.rerun()

    # Vertical alignment fix + custom button styling
    st.markdown("""
    <style>
        /* Align the New Conversation button with the expander */
        [data-testid="stColumns"] > div:last-child .stButton {
            margin-top: 0px;
        }
        [data-testid="stColumns"] > div:last-child .stButton button {
            height: 44px;
            white-space: nowrap;
            border-radius: 8px;
            border: 1px solid rgba(70,130,180,0.3);
            font-size: 0.8rem;
        }
    </style>
    """, unsafe_allow_html=True)
