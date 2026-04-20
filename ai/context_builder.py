"""Assemble grounding context for Claude from live data."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# KPI thresholds — values below (or above for wait/response) trigger warnings
KPI_THRESHOLDS = {
    "pipeline_success_rate": {"target": 99.0, "unit": "%", "direction": "above"},
    "data_quality_score": {"target": 95.0, "unit": "%", "direction": "above"},
    "flight_otp": {"target": 80.0, "unit": "%", "direction": "above"},
    "passenger_throughput": {"target": 2000, "unit": "pax/hr", "direction": "above"},
    "avg_security_wait": {"target": 15, "unit": "min", "direction": "below"},
    "safety_incident_response": {"target": 120, "unit": "sec", "direction": "below"},
    "environmental_compliance": {"target": 95.0, "unit": "%", "direction": "above"},
}


def _safe_read_parquet(path: str) -> pd.DataFrame | None:
    """Read a Parquet file, returning None if it doesn't exist or is unreadable."""
    full = PROJECT_ROOT / path
    if not full.exists():
        return None
    try:
        return pd.read_parquet(full)
    except Exception:
        return None


def _get_pipeline_health() -> dict:
    """Latest run results per stream from pipeline logs."""
    df = _safe_read_parquet("data/logs/pipeline_logs.parquet")
    if df is None:
        return {"status": "no_data", "message": "Pipeline log data unavailable"}

    summary = {}
    try:
        if "stream" in df.columns and "status" in df.columns:
            total = len(df)
            success = (df["status"] == "success").sum() if total > 0 else 0
            summary["total_runs"] = int(total)
            summary["successful_runs"] = int(success)
            summary["success_rate"] = round(success / total * 100, 2) if total > 0 else 0

            if "duration_sec" in df.columns:
                summary["avg_duration_sec"] = round(df["duration_sec"].mean(), 2)

            # Per-stream breakdown
            per_stream = {}
            for stream, grp in df.groupby("stream"):
                s_total = len(grp)
                s_success = (grp["status"] == "success").sum()
                per_stream[stream] = {
                    "runs": int(s_total),
                    "success_rate": round(s_success / s_total * 100, 2) if s_total > 0 else 0,
                }
            summary["per_stream"] = per_stream
        else:
            summary["status"] = "schema_mismatch"
    except Exception as e:
        summary["error"] = str(e)
    return summary


def _get_kpi_summary() -> dict:
    """Current KPI values vs thresholds."""
    kpis = {}

    # Flight KPIs
    df = _safe_read_parquet("data/gold/flight_kpis.parquet")
    if df is not None and not df.empty:
        if "on_time_pct" in df.columns:
            kpis["flight_otp"] = round(df["on_time_pct"].mean(), 2)
        if "avg_delay_min" in df.columns:
            kpis["avg_flight_delay_min"] = round(df["avg_delay_min"].mean(), 2)
        if "gate_utilization" in df.columns:
            kpis["gate_utilization"] = round(df["gate_utilization"].mean(), 2)

    # Passenger KPIs
    df = _safe_read_parquet("data/gold/passenger_kpis.parquet")
    if df is not None and not df.empty:
        if "throughput_per_hour" in df.columns:
            kpis["passenger_throughput"] = round(df["throughput_per_hour"].mean(), 2)
        if "avg_wait_min" in df.columns:
            kpis["avg_security_wait"] = round(df["avg_wait_min"].mean(), 2)

    # Quality KPIs
    df = _safe_read_parquet("data/gold/quality_kpis.parquet")
    if df is not None and not df.empty:
        if "quality_score" in df.columns:
            kpis["data_quality_score"] = round(df["quality_score"].mean(), 2)
        if "compliance_pct" in df.columns:
            kpis["environmental_compliance"] = round(df["compliance_pct"].mean(), 2)

    # Safety KPIs
    df = _safe_read_parquet("data/gold/safety_kpis.parquet")
    if df is not None and not df.empty:
        if "avg_response_sec" in df.columns:
            kpis["safety_incident_response"] = round(df["avg_response_sec"].mean(), 2)

    # Evaluate against thresholds
    evaluated = {}
    for key, threshold in KPI_THRESHOLDS.items():
        value = kpis.get(key)
        if value is None:
            evaluated[key] = {"value": None, "status": "no_data", **threshold}
            continue
        if threshold["direction"] == "above":
            status = "healthy" if value >= threshold["target"] else "warning"
        else:
            status = "healthy" if value <= threshold["target"] else "warning"
        evaluated[key] = {"value": value, "status": status, **threshold}

    return evaluated


def _get_quality_issues() -> dict:
    """Top validation failures and quarantine spikes."""
    issues = {}

    quarantine_dir = PROJECT_ROOT / "data" / "quarantine"
    if quarantine_dir.exists():
        quarantine_files = list(quarantine_dir.glob("*.parquet"))
        for qf in quarantine_files:
            try:
                df = pd.read_parquet(qf)
                stream_name = qf.stem
                issues[stream_name] = {
                    "quarantined_records": len(df),
                    "columns": list(df.columns),
                }
                if "failure_reason" in df.columns:
                    top_reasons = df["failure_reason"].value_counts().head(5).to_dict()
                    issues[stream_name]["top_failure_reasons"] = top_reasons
                if "timestamp" in df.columns:
                    issues[stream_name]["latest"] = str(df["timestamp"].max())
            except Exception:
                continue

    if not issues:
        issues["status"] = "no_quarantine_data"
    return issues


def _get_anomalies() -> dict:
    """Detected issues from logs."""
    df = _safe_read_parquet("data/logs/pipeline_logs.parquet")
    if df is None:
        return {"status": "no_data"}

    anomalies = []
    try:
        if "status" in df.columns:
            failures = df[df["status"] != "success"]
            if not failures.empty:
                for _, row in failures.head(10).iterrows():
                    entry = {"stream": row.get("stream", "unknown"), "status": row.get("status")}
                    if "error_message" in df.columns:
                        entry["error"] = row.get("error_message", "")
                    if "timestamp" in df.columns:
                        entry["timestamp"] = str(row.get("timestamp", ""))
                    anomalies.append(entry)
    except Exception as e:
        return {"error": str(e)}

    return {"count": len(anomalies), "recent_failures": anomalies}


def _get_recent_alerts() -> list:
    """Last N alerts by severity."""
    df = _safe_read_parquet("data/logs/alerts.parquet")
    if df is None:
        return []

    try:
        if "severity" in df.columns:
            df = df.sort_values("severity", ascending=False)
        return df.head(20).to_dict(orient="records")
    except Exception:
        return []


def build_ai_context() -> dict:
    """Assemble grounding context for Claude from live data.

    Reads from data/gold/, data/logs/, data/quarantine/.
    Returns structured context dict with:
    - pipeline_health: latest run results per stream
    - kpi_summary: current KPI values vs thresholds
    - quality_issues: top validation failures, quarantine spikes
    - anomalies: detected issues
    - lineage_impact: which Gold KPIs are affected
    - recent_alerts: last N alerts by severity
    """
    from utils.lineage import get_impact_analysis

    context = {
        "timestamp": datetime.now().isoformat(),
        "airport": "AeroOps International Airport (AOP)",
        "pipeline_health": _get_pipeline_health(),
        "kpi_summary": _get_kpi_summary(),
        "quality_issues": _get_quality_issues(),
        "anomalies": _get_anomalies(),
        "recent_alerts": _get_recent_alerts(),
    }

    # Compute lineage impact for any streams with issues
    lineage_impact = {}
    anomalies = context.get("anomalies", {})
    if isinstance(anomalies, dict):
        for failure in anomalies.get("recent_failures", []):
            stream = failure.get("stream")
            if stream and stream not in lineage_impact:
                lineage_impact[stream] = get_impact_analysis(stream)
    context["lineage_impact"] = lineage_impact

    return context


def format_context_for_prompt(context: dict) -> str:
    """Render the context dict into a readable text block for Claude."""
    lines = []
    lines.append(f"Timestamp: {context.get('timestamp', 'N/A')}")
    lines.append(f"Airport: {context.get('airport', 'N/A')}")
    lines.append("")

    # Pipeline Health
    lines.append("=== PIPELINE HEALTH ===")
    ph = context.get("pipeline_health", {})
    if ph.get("status") == "no_data":
        lines.append("No pipeline data available.")
    else:
        lines.append(f"Total runs: {ph.get('total_runs', 'N/A')}")
        lines.append(f"Success rate: {ph.get('success_rate', 'N/A')}%")
        lines.append(f"Avg duration: {ph.get('avg_duration_sec', 'N/A')}s")
        per_stream = ph.get("per_stream", {})
        if per_stream:
            lines.append("Per-stream breakdown:")
            for stream, stats in per_stream.items():
                lines.append(f"  {stream}: {stats.get('success_rate', 'N/A')}% "
                             f"({stats.get('runs', 0)} runs)")
    lines.append("")

    # KPI Summary
    lines.append("=== KPI SUMMARY ===")
    kpis = context.get("kpi_summary", {})
    for kpi_name, info in kpis.items():
        if isinstance(info, dict):
            value = info.get("value", "N/A")
            status = info.get("status", "unknown")
            target = info.get("target", "N/A")
            unit = info.get("unit", "")
            indicator = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❓"
            lines.append(f"  {indicator} {kpi_name}: {value} {unit} (target: {target} {unit}) [{status}]")
    lines.append("")

    # Quality Issues
    lines.append("=== QUALITY ISSUES ===")
    qi = context.get("quality_issues", {})
    if qi.get("status") == "no_quarantine_data":
        lines.append("No quarantine data found.")
    else:
        for stream, info in qi.items():
            if isinstance(info, dict):
                lines.append(f"  {stream}: {info.get('quarantined_records', 0)} quarantined records")
                for reason, count in info.get("top_failure_reasons", {}).items():
                    lines.append(f"    - {reason}: {count}")
    lines.append("")

    # Anomalies
    lines.append("=== ANOMALIES ===")
    anomalies = context.get("anomalies", {})
    if anomalies.get("status") == "no_data":
        lines.append("No anomaly data available.")
    else:
        lines.append(f"Total failures detected: {anomalies.get('count', 0)}")
        for failure in anomalies.get("recent_failures", []):
            lines.append(f"  - Stream: {failure.get('stream', 'unknown')} | "
                         f"Status: {failure.get('status', 'unknown')} | "
                         f"Error: {failure.get('error', 'N/A')} | "
                         f"Time: {failure.get('timestamp', 'N/A')}")
    lines.append("")

    # Lineage Impact
    lines.append("=== LINEAGE IMPACT ===")
    impact = context.get("lineage_impact", {})
    if not impact:
        lines.append("No lineage impact detected.")
    else:
        for stream, info in impact.items():
            lines.append(f"  Stream '{stream}' failure impacts:")
            if isinstance(info, dict):
                for kpi in info.get("affected_kpis", []):
                    lines.append(f"    - KPI: {kpi}")
                for gold in info.get("affected_gold_tables", []):
                    lines.append(f"    - Gold table: {gold}")
    lines.append("")

    # Recent Alerts
    lines.append("=== RECENT ALERTS ===")
    alerts = context.get("recent_alerts", [])
    if not alerts:
        lines.append("No recent alerts.")
    else:
        for alert in alerts[:10]:
            if isinstance(alert, dict):
                lines.append(f"  [{alert.get('severity', 'N/A')}] "
                             f"{alert.get('message', alert.get('description', 'N/A'))}")
    lines.append("")

    return "\n".join(lines)
