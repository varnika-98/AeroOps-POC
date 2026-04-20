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
        # Actual columns: run_timestamp, stage, stream, total_records, passed, failed, quality_score, duration_sec
        if "stream" in df.columns and "quality_score" in df.columns:
            total = len(df)
            success = (df["quality_score"] >= 1.0).sum() if total > 0 else 0
            summary["total_runs"] = int(total)
            summary["successful_runs"] = int(success)
            summary["success_rate"] = round(success / total * 100, 2) if total > 0 else 0

            if "duration_sec" in df.columns:
                summary["avg_duration_sec"] = round(df["duration_sec"].mean(), 2)

            # Per-stream breakdown
            per_stream = {}
            for stream, grp in df.groupby("stream"):
                s_total = len(grp)
                s_success = (grp["quality_score"] >= 1.0).sum()
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

    # Flight KPIs (columns: hour, total_flights, on_time, otp_pct, avg_delay_min, max_delay_min, gates_used)
    df = _safe_read_parquet("data/gold/flight_kpis.parquet")
    if df is not None and not df.empty:
        if "otp_pct" in df.columns:
            kpis["flight_otp"] = round(df["otp_pct"].mean(), 2)
        if "avg_delay_min" in df.columns:
            kpis["avg_flight_delay_min"] = round(df["avg_delay_min"].mean(), 2)

    # Passenger KPIs (columns: checkpoint, avg_wait_min, max_wait_min, avg_throughput, total_passengers)
    df = _safe_read_parquet("data/gold/passenger_kpis.parquet")
    if df is not None and not df.empty:
        if "avg_throughput" in df.columns:
            kpis["passenger_throughput"] = round(df["avg_throughput"].mean(), 2)
        if "avg_wait_min" in df.columns:
            kpis["avg_security_wait"] = round(df["avg_wait_min"].mean(), 2)

    # Quality KPIs (columns: stream, total_records, valid_records, quarantined_records, validation_rate_pct, quarantine_pct)
    df = _safe_read_parquet("data/gold/quality_kpis.parquet")
    if df is not None and not df.empty:
        if "validation_rate_pct" in df.columns:
            kpis["data_quality_score"] = round(df["validation_rate_pct"].mean(), 2)

    # Pipeline KPIs (columns: stream, run_count, avg_duration_sec, avg_quality_pct, total_records_processed, records_per_sec)
    df = _safe_read_parquet("data/gold/pipeline_kpis.parquet")
    if df is not None and not df.empty:
        if "avg_quality_pct" in df.columns:
            kpis["pipeline_success_rate"] = round(df["avg_quality_pct"].mean(), 2)

    # Safety KPIs (columns: severity, alert_count, avg_response_sec, auto_cleared, escalated, resolution_rate_pct)
    df = _safe_read_parquet("data/gold/safety_kpis.parquet")
    if df is not None and not df.empty:
        if "avg_response_sec" in df.columns:
            kpis["safety_incident_response"] = round(df["avg_response_sec"].mean(), 2)

    # Environmental compliance from quality KPIs (use overall validation rate)
    if "data_quality_score" in kpis:
        kpis["environmental_compliance"] = kpis["data_quality_score"]

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
        # Actual columns: run_timestamp, stage, stream, total_records, passed, failed, quality_score, duration_sec
        if "quality_score" in df.columns:
            # Exclude gold stage — quality_score is always 0.0 there (aggregation, no validation)
            silver_df = df[df["stage"] == "silver"] if "stage" in df.columns else df
            failures = silver_df[silver_df["quality_score"] < 1.0]
            if not failures.empty:
                for _, row in failures.head(10).iterrows():
                    entry = {
                        "stream": row.get("stream", "unknown"),
                        "stage": row.get("stage", "unknown"),
                        "quality_score": round(row.get("quality_score", 0), 4),
                        "failed_records": int(row.get("failed", 0)),
                        "total_records": int(row.get("total_records", 0)),
                    }
                    if "run_timestamp" in df.columns:
                        entry["timestamp"] = str(row.get("run_timestamp", ""))
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
    """Render the context dict into a compact text block for the LLM."""
    lines = []
    lines.append(f"Timestamp: {context.get('timestamp', 'N/A')}")

    # Pipeline Health
    ph = context.get("pipeline_health", {})
    if ph.get("status") not in ("no_data", "schema_mismatch"):
        lines.append("\n=== PIPELINE HEALTH ===")
        lines.append(f"Runs: {ph.get('total_runs', 'N/A')}, Success: {ph.get('success_rate', 'N/A')}%, Avg duration: {ph.get('avg_duration_sec', 'N/A')}s")
        per_stream = ph.get("per_stream", {})
        if per_stream:
            for stream, stats in per_stream.items():
                lines.append(f"  {stream}: {stats.get('success_rate', 'N/A')}% ({stats.get('runs', 0)} runs)")

    # KPI Summary — only include KPIs with data
    kpis = context.get("kpi_summary", {})
    kpi_lines = []
    for kpi_name, info in kpis.items():
        if isinstance(info, dict) and info.get("status") != "no_data":
            value = info.get("value", "N/A")
            target = info.get("target", "N/A")
            unit = info.get("unit", "")
            indicator = "✅" if info.get("status") == "healthy" else "⚠️"
            kpi_lines.append(f"  {indicator} {kpi_name}: {value} {unit} (target: {target} {unit})")
    if kpi_lines:
        lines.append("\n=== KPIs ===")
        lines.extend(kpi_lines)

    # Quality Issues
    qi = context.get("quality_issues", {})
    qi_lines = []
    for stream, info in qi.items():
        if isinstance(info, dict) and info.get("quarantined_records", 0) > 0:
            qi_lines.append(f"  {stream}: {info['quarantined_records']} quarantined")
            for reason, count in info.get("top_failure_reasons", {}).items():
                qi_lines.append(f"    - {reason}: {count}")
    if qi_lines:
        lines.append("\n=== QUALITY ISSUES ===")
        lines.extend(qi_lines)

    # Anomalies — only if any exist
    anomalies = context.get("anomalies", {})
    if anomalies.get("count", 0) > 0:
        lines.append(f"\n=== ANOMALIES ({anomalies['count']}) ===")
        for f in anomalies.get("recent_failures", [])[:5]:
            lines.append(f"  {f.get('stream')}/{f.get('stage')}: quality={f.get('quality_score')}, failed={f.get('failed_records')}/{f.get('total_records')}")

    # Lineage Impact — only if any
    impact = context.get("lineage_impact", {})
    if impact:
        lines.append("\n=== IMPACT ===")
        for stream, info in impact.items():
            if isinstance(info, dict):
                kpis_affected = ", ".join(info.get("affected_kpis", []))
                if kpis_affected:
                    lines.append(f"  {stream} → KPIs: {kpis_affected}")

    return "\n".join(lines)
