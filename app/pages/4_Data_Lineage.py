"""Data Lineage & Governance dashboard page."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.theme import COLORS, STREAM_ICONS, apply_theme, page_header, page_loader
from utils.charts import sankey_chart
from utils.lineage import LINEAGE_MODEL, get_lineage_for_stream, get_impact_analysis, get_reverse_lineage, get_sankey_data
from pipeline.quality_rules import QUALITY_RULES

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
apply_theme(st)
st.markdown(page_loader(duration=0.5), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STREAMS = list(LINEAGE_MODEL.keys())
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"

DATA_CLASSIFICATION = {
    "flights": ["Operational", "PII (passenger_count)"],
    "passengers": ["Operational", "PII"],
    "cargo": ["Operational", "Commercial"],
    "environmental": ["Operational", "Regulatory"],
    "runway": ["Operational", "Safety"],
    "security": ["Security", "PII", "Regulatory"],
}

TAG_COLORS = {
    "Operational": "#3498db",
    "PII": "#e74c3c",
    "PII (passenger_count)": "#e74c3c",
    "Commercial": "#2ecc71",
    "Regulatory": "#9b59b6",
    "Safety": "#f39c12",
    "Security": "#e67e22",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_parquet(path: str) -> pd.DataFrame | None:
    try:
        p = Path(path)
        if p.exists():
            return pd.read_parquet(p)
    except Exception:
        pass
    return None


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:12px;margin-right:4px;font-size:0.85em;">{text}</span>'
    )


# =========================================================================
# Page content
# =========================================================================

page_header("Data Lineage & Governance", "🔗")

# ---------- 1. Lineage Flow Diagram (Sankey) ----------
st.subheader("Data Lineage Flow — Bronze → Silver → Gold")

sankey_data = get_sankey_data()
if sankey_data and sankey_data.get("labels"):
    fig = sankey_chart(
        sources=sankey_data["sources"],
        targets=sankey_data["targets"],
        values=sankey_data["values"],
        labels=sankey_data["labels"],
        title="End-to-End Data Lineage (all streams)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sankey data unavailable — ensure data files exist.")

# ---------- 2. Impact Analysis ----------
st.subheader("Impact Analysis")

selected_stream = st.selectbox(
    "Select a stream to analyse impact",
    STREAMS,
    format_func=lambda s: f"{STREAM_ICONS.get(s, '📊')} {s.title()}",
    key="impact_stream",
)

impact = get_impact_analysis(selected_stream)
if impact:
    severity = impact.get("severity", "unknown")
    sev_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
    st.markdown(f"**Severity if `{selected_stream}` fails:** {sev_color} {severity.upper()}")

    st.markdown("**Affected Gold Tables:**")
    for t in impact.get("affected_gold_tables", []):
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📦 `{t}`")

    st.markdown("**Affected KPIs:**")
    for k in impact.get("affected_kpis", []):
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📈 {k}")

    shared = impact.get("shared_gold_with", [])
    if shared:
        st.markdown("**Shares Gold tables with streams:**")
        for s in shared:
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔗 {s}")

    # Visual tree
    with st.expander("Lineage tree", expanded=False):
        lineage = get_lineage_for_stream(selected_stream)
        if lineage:
            st.markdown(f"```\n{STREAM_ICONS.get(selected_stream, '')} {selected_stream}")
            st.markdown(f"  ├── Bronze: {lineage.get('bronze', 'N/A')}")
            st.markdown(f"  ├── Silver: {lineage.get('silver', 'N/A')}")
            gold = lineage.get("gold", [])
            gold_list = gold if isinstance(gold, list) else [gold]
            for g in gold_list:
                st.markdown(f"  ├── Gold: {g}")
            for k in lineage.get("kpis", []):
                st.markdown(f"  └── KPI: {k}")
            st.markdown("```")
else:
    st.warning("No impact data for this stream.")

# ---------- 3. Quality Rules Table ----------
st.subheader("Quality Rules Catalogue")

rules_rows: list[dict] = []
quarantine_failed_rules: set[str] = set()

# Collect failing rules from quarantine data
for stream in STREAMS:
    qf = load_parquet(str(QUARANTINE_DIR / f"{stream}_quarantine.parquet"))
    if qf is not None and "_quarantine_reasons" in qf.columns:
        reasons = qf["_quarantine_reasons"].dropna()
        if not reasons.empty:
            for r in reasons:
                if isinstance(r, list):
                    quarantine_failed_rules.update(r)
                else:
                    quarantine_failed_rules.add(str(r))

for stream, rules in QUALITY_RULES.items():
    for rule in rules:
        rule_name = rule.get("rule", "")
        rule_type = rule.get("type", "")

        # Build human-readable criteria
        if rule_type == "range":
            criteria = f"{rule.get('min', '?')} – {rule.get('max', '?')}"
        elif rule_type == "enum":
            criteria = ", ".join(str(v) for v in rule.get("values", []))
        elif rule_type == "regex":
            criteria = f"pattern: {rule.get('pattern', '')}"
        elif rule_type == "not_null":
            criteria = "must not be null"
        else:
            criteria = str(rule_type)

        status = "❌ Failing" if rule_name in quarantine_failed_rules else "✅ Passing"

        rules_rows.append({
            "Stream": stream.title(),
            "Rule Name": rule_name,
            "Field": rule.get("field", ""),
            "Type": rule_type,
            "Criteria": criteria,
            "Status": status,
        })

if rules_rows:
    st.dataframe(pd.DataFrame(rules_rows), use_container_width=True, hide_index=True)
else:
    st.info("No quality rules defined.")

# ---------- 4. Quarantine Inspector ----------
st.subheader("Quarantine Inspector")

inspect_stream = st.selectbox(
    "Select stream to inspect quarantine",
    STREAMS,
    format_func=lambda s: f"{STREAM_ICONS.get(s, '📊')} {s.title()}",
    key="quarantine_stream",
)

qfile = QUARANTINE_DIR / f"{inspect_stream}_quarantine.parquet"
qdf = load_parquet(str(qfile))

if qdf is not None and not qdf.empty:
    st.metric("Quarantined Records", len(qdf))

    reason_col = "_quarantine_reasons"
    if reason_col in qdf.columns:
        reasons = qdf[reason_col].dropna()
        if not reasons.empty:
            exploded = reasons.explode() if reasons.apply(lambda x: isinstance(x, list)).any() else reasons
            st.markdown("**Failure reason summary:**")
            st.dataframe(
                exploded.value_counts().reset_index().rename(columns={"index": "Reason", reason_col: "Reason", "count": "Count", 0: "Count"}),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander(f"View quarantined records for {inspect_stream}", expanded=False):
        st.dataframe(qdf, use_container_width=True, hide_index=True)
else:
    st.success(f"No quarantine records for **{inspect_stream}** — all records passed! ✅")

# ---------- 5. Reverse Lineage ----------
st.subheader("Reverse Lineage — Trace KPI to Source")

# Collect all KPI names from the lineage model
all_kpis: list[str] = []
for stream_info in LINEAGE_MODEL.values():
    kpis = stream_info.get("kpis", [])
    if isinstance(kpis, list):
        all_kpis.extend(kpis)
    else:
        all_kpis.append(str(kpis))
all_kpis = sorted(set(all_kpis))

if all_kpis:
    selected_kpi = st.selectbox("Select a Gold KPI", all_kpis, key="reverse_kpi")

    reverse = get_reverse_lineage(selected_kpi)
    if reverse:
        for entry in reverse:
            stream_name = entry.get("stream", "?")
            icon = STREAM_ICONS.get(stream_name, "📊")
            st.markdown(
                f"**{selected_kpi}** &larr; Gold `{entry.get('gold', '?')}` "
                f"&larr; Silver `{entry.get('silver', '?')}` "
                f"&larr; Bronze `{entry.get('bronze', '?')}` "
                f"({icon} {stream_name})"
            )
    else:
        st.info("No lineage trace found for this KPI.")
else:
    st.info("No KPIs found in the lineage model.")

# ---------- 6. Data Classification Tags ----------
st.subheader("Data Classification Tags")

classification_rows: list[dict] = []
for stream, tags in DATA_CLASSIFICATION.items():
    badges_html = " ".join(_badge(tag, TAG_COLORS.get(tag, "#888")) for tag in tags)
    classification_rows.append({
        "Stream": f"{STREAM_ICONS.get(stream, '📊')} {stream.title()}",
        "Classifications": badges_html,
    })

if classification_rows:
    html_table = "<table style='width:100%;border-collapse:collapse;'>"
    html_table += "<tr><th style='text-align:left;padding:8px;border-bottom:1px solid #ddd;'>Stream</th>"
    html_table += "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd;'>Classifications</th></tr>"
    for row in classification_rows:
        html_table += (
            f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{row['Stream']}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee;'>{row['Classifications']}</td></tr>"
        )
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)
