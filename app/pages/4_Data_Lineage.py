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

from utils.theme import COLORS, STREAM_ICONS, SVG_ICONS, apply_theme, page_header, page_loader, section_header, inline_svg, stream_svg, status_svg
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
    "Operational": COLORS["sky_blue"],
    "PII": COLORS["danger_red"],
    "PII (passenger_count)": COLORS["danger_red"],
    "Commercial": COLORS["success_green"],
    "Regulatory": COLORS["navy"],
    "Safety": COLORS["safety_orange"],
    "Security": COLORS["warning_yellow"],
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

st.markdown(page_header("Data Lineage & Governance", SVG_ICONS["link"]), unsafe_allow_html=True)

# ---------- 1. Lineage Flow Diagram (Sankey) ----------
st.markdown(section_header("Data Lineage Flow — Bronze → Silver → Gold", "sankey"), unsafe_allow_html=True)

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
st.markdown(section_header("Impact Analysis", "impact"), unsafe_allow_html=True)

selected_stream = st.selectbox(
    "Select a stream to analyse impact",
    STREAMS,
    format_func=lambda s: f"{STREAM_ICONS.get(s, '📊')} {s.title()}",
    key="impact_stream",
)

impact = get_impact_analysis(selected_stream)
if impact:
    severity = impact.get("severity", "unknown")
    sev_svg = status_svg(severity)
    st.markdown(f"**Severity if `{selected_stream}` fails:** {sev_svg} {severity.upper()}", unsafe_allow_html=True)

    st.markdown("**Affected Gold Tables:**")
    for t in impact.get("affected_gold_tables", []):
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{inline_svg('cargo', 16)} `{t}`", unsafe_allow_html=True)

    st.markdown("**Affected KPIs:**")
    for k in impact.get("affected_kpis", []):
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{inline_svg('chart_up', 16)} {k}", unsafe_allow_html=True)

    shared = impact.get("shared_gold_with", [])
    if shared:
        st.markdown("**Shares Gold tables with streams:**")
        for s in shared:
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{inline_svg('link', 16)} {s}", unsafe_allow_html=True)

    # Visual tree
    with st.expander("Lineage tree", expanded=False):
        lineage = get_lineage_for_stream(selected_stream)
        if lineage:
            s_svg = stream_svg(selected_stream, 16)
            st.markdown(f"{s_svg} **{selected_stream}**", unsafe_allow_html=True)
            st.markdown(f"&nbsp;&nbsp;├── Bronze: `{lineage.get('bronze', 'N/A')}`")
            st.markdown(f"&nbsp;&nbsp;├── Silver: `{lineage.get('silver', 'N/A')}`")
            gold = lineage.get("gold", [])
            gold_list = gold if isinstance(gold, list) else [gold]
            for g in gold_list:
                st.markdown(f"&nbsp;&nbsp;├── Gold: `{g}`")
            for k in lineage.get("kpis", []):
                st.markdown(f"&nbsp;&nbsp;└── KPI: `{k}`")
else:
    st.warning("No impact data for this stream.")

# ---------- 3. Quality Rules Table ----------
st.markdown(section_header("Quality Rules Catalogue", "rules"), unsafe_allow_html=True)

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
st.markdown(section_header("Quarantine Inspector", "quarantine"), unsafe_allow_html=True)

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
st.markdown(section_header("Reverse Lineage — Trace KPI to Source", "reverse"), unsafe_allow_html=True)

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
            icon = stream_svg(stream_name, 16)
            st.markdown(
                f"**{selected_kpi}** &larr; Gold `{entry.get('gold', '?')}` "
                f"&larr; Silver `{entry.get('silver', '?')}` "
                f"&larr; Bronze `{entry.get('bronze', '?')}` "
                f"({icon} {stream_name})",
                unsafe_allow_html=True,
            )
    else:
        st.info("No lineage trace found for this KPI.")
else:
    st.info("No KPIs found in the lineage model.")

# ---------- 6. Data Classification Tags ----------
st.markdown(section_header("Data Classification Tags", "tags"), unsafe_allow_html=True)

classification_rows: list[dict] = []
for stream, tags in DATA_CLASSIFICATION.items():
    badges_html = " ".join(_badge(tag, TAG_COLORS.get(tag, "#888")) for tag in tags)
    s_svg = stream_svg(stream, 18)
    classification_rows.append({
        "Stream": f"{s_svg} {stream.title()}",
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
