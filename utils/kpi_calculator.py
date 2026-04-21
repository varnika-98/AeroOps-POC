"""KPI computation functions that read from Gold/Silver/Quarantine Parquet files."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_NO_DATA = {"status": "no_data", "message": "Data file not found"}


def _safe_read(relative_path: str) -> pd.DataFrame | None:
    """Read a Parquet file, returning None if missing or unreadable."""
    full = PROJECT_ROOT / relative_path
    if not full.exists():
        return None
    try:
        return pd.read_parquet(full)
    except Exception:
        return None


def get_pipeline_health() -> dict:
    """Returns pipeline success rate, avg duration, throughput from logs."""
    # Orchestrator writes pipeline_logs.parquet
    df = _safe_read("data/logs/pipeline_logs.parquet")
    if df is None:
        return _NO_DATA.copy()

    total = len(df)
    if total == 0:
        return {"total_runs": 0, "success_rate": 0, "avg_duration_sec": 0, "throughput_per_hour": 0}

    # Count unique pipeline runs (each run logs multiple stages)
    if "run_timestamp" in df.columns:
        unique_runs = df["run_timestamp"].nunique()
    else:
        unique_runs = total

    # Success: a run is successful if it has a gold stage entry (pipeline completed)
    if "status" in df.columns:
        success = int((df["status"] == "success").sum())
    elif "stage" in df.columns:
        # Each complete run has a "gold" stage entry
        success = int((df["stage"] == "gold").sum())
    else:
        success = unique_runs

    avg_dur = round(df["duration_sec"].mean(), 2) if "duration_sec" in df.columns else 0

    records = int(df["total_records"].sum()) if "total_records" in df.columns else 0

    return {
        "total_runs": int(unique_runs),
        "successful_runs": int(success),
        "success_rate": round(success / unique_runs * 100, 2) if unique_runs else 0,
        "avg_duration_sec": avg_dur,
        "total_records_processed": records,
    }


def get_data_quality_scores() -> dict:
    """Returns quality score per stream from quality_kpis."""
    df = _safe_read("data/gold/quality_kpis.parquet")
    if df is None:
        return _NO_DATA.copy()

    result = {}
    # Gold layer stores the column as "validation_rate_pct"
    score_col = (
        "quality_score" if "quality_score" in df.columns
        else "validation_rate_pct" if "validation_rate_pct" in df.columns
        else None
    )
    if "stream" in df.columns and score_col:
        for stream, grp in df.groupby("stream"):
            result[stream] = {
                "quality_score": round(grp[score_col].mean(), 2),
                "min_score": round(grp[score_col].min(), 2),
                "max_score": round(grp[score_col].max(), 2),
                "records": len(grp),
            }
    elif score_col and score_col in df.columns:
        result["overall"] = {
            "quality_score": round(df[score_col].mean(), 2),
            "min_score": round(df[score_col].min(), 2),
            "max_score": round(df[score_col].max(), 2),
            "records": len(df),
        }
    else:
        result["status"] = "schema_mismatch"

    return result


def get_flight_kpis() -> dict:
    """Returns OTP, avg delay, gate utilization from flight_kpis."""
    df = _safe_read("data/gold/flight_kpis.parquet")
    if df is None:
        return _NO_DATA.copy()

    result = {}
    if "otp_pct" in df.columns:
        result["otp_pct"] = round(df["otp_pct"].mean(), 2)
    elif "on_time_pct" in df.columns:
        result["otp_pct"] = round(df["on_time_pct"].mean(), 2)
    if "avg_delay_min" in df.columns:
        result["avg_delay_min"] = round(df["avg_delay_min"].mean(), 2)
    if "gates_used" in df.columns:
        result["gate_utilization_pct"] = round(df["gates_used"].mean(), 2)
    elif "gate_utilization" in df.columns:
        result["gate_utilization_pct"] = round(df["gate_utilization"].mean(), 2)
    if "total_flights" in df.columns:
        result["total_flights"] = int(df["total_flights"].sum())

    return result if result else _NO_DATA.copy()


def get_passenger_kpis() -> dict:
    """Returns throughput, avg wait time from passenger_kpis."""
    df = _safe_read("data/gold/passenger_kpis.parquet")
    if df is None:
        return _NO_DATA.copy()

    result = {}
    if "avg_throughput" in df.columns:
        result["throughput_per_hour"] = round(df["avg_throughput"].mean(), 2)
    elif "throughput_per_hour" in df.columns:
        result["throughput_per_hour"] = round(df["throughput_per_hour"].mean(), 2)
    if "avg_wait_min" in df.columns:
        result["avg_wait_min"] = round(df["avg_wait_min"].mean(), 2)
    if "checkpoint" in df.columns:
        result["checkpoint_count"] = df["checkpoint"].nunique()
    if "total_passengers" in df.columns:
        result["total_passengers"] = int(df["total_passengers"].sum())

    return result if result else _NO_DATA.copy()


def get_safety_kpis() -> dict:
    """Returns avg response time, alert counts from safety_kpis."""
    df = _safe_read("data/gold/safety_kpis.parquet")
    if df is None:
        return _NO_DATA.copy()

    result = {}
    if "avg_response_sec" in df.columns:
        result["avg_response_sec"] = round(df["avg_response_sec"].mean(), 2)
    if "alert_count" in df.columns:
        result["total_alerts"] = int(df["alert_count"].sum())
    elif "total_alerts" in df.columns:
        result["total_alerts"] = int(df["total_alerts"].sum())
    if "auto_cleared" in df.columns and "escalated" in df.columns:
        resolved = int(df["auto_cleared"].sum())
        result["resolved_alerts"] = resolved
        total_a = result.get("total_alerts", 0)
        if total_a > 0:
            result["resolution_rate_pct"] = round(resolved / total_a * 100, 2)
    elif "resolved_alerts" in df.columns:
        result["resolved_alerts"] = int(df["resolved_alerts"].sum())
        if result.get("total_alerts", 0) > 0:
            result["resolution_rate_pct"] = round(
                result["resolved_alerts"] / result["total_alerts"] * 100, 2
            )

    return result if result else _NO_DATA.copy()


def get_environmental_compliance() -> dict:
    """Returns % readings within regulatory bounds."""
    df = _safe_read("data/gold/quality_kpis.parquet")
    if df is None:
        return _NO_DATA.copy()

    result = {}
    if "compliance_pct" in df.columns:
        result["compliance_pct"] = round(df["compliance_pct"].mean(), 2)
    if "readings_in_bounds" in df.columns and "total_readings" in df.columns:
        in_bounds = df["readings_in_bounds"].sum()
        total = df["total_readings"].sum()
        result["in_bounds_pct"] = round(in_bounds / total * 100, 2) if total > 0 else 0
        result["total_readings"] = int(total)

    return result if result else _NO_DATA.copy()


def get_ai_kpis() -> dict:
    """Returns AI/LLM usage KPIs from the metrics log."""
    try:
        from ai.claude_client import load_ai_metrics
        metrics = load_ai_metrics()
    except Exception:
        metrics = []

    if not metrics:
        return _NO_DATA.copy()

    success = [m for m in metrics if m.get("status") == "success"]
    errors = [m for m in metrics if m.get("status") == "error"]

    total_input = sum(m.get("input_tokens", 0) or 0 for m in success)
    total_output = sum(m.get("output_tokens", 0) or 0 for m in success)
    total_cost = sum(m.get("cost_usd", 0) or 0 for m in success)
    latencies = [m["latency_sec"] for m in success if "latency_sec" in m]

    # Per prompt type breakdown
    prompt_types = {}
    for m in success:
        pt = m.get("prompt_type", "unknown")
        if pt not in prompt_types:
            prompt_types[pt] = {"count": 0, "tokens": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0, "latencies": []}
        prompt_types[pt]["count"] += 1
        prompt_types[pt]["tokens"] += (m.get("total_tokens", 0) or 0)
        prompt_types[pt]["input_tokens"] += (m.get("input_tokens", 0) or 0)
        prompt_types[pt]["output_tokens"] += (m.get("output_tokens", 0) or 0)
        prompt_types[pt]["cost"] += (m.get("cost_usd", 0) or 0)
        if "latency_sec" in m:
            prompt_types[pt]["latencies"].append(m["latency_sec"])

    for pt in prompt_types.values():
        lats = pt.pop("latencies")
        pt["avg_latency_sec"] = round(sum(lats) / len(lats), 3) if lats else 0

    return {
        "total_requests": len(metrics),
        "successful_requests": len(success),
        "failed_requests": len(errors),
        "error_rate_pct": round(len(errors) / len(metrics) * 100, 2) if metrics else 0,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost_usd": round(total_cost, 6),
        "avg_latency_sec": round(sum(latencies) / len(latencies), 3) if latencies else 0,
        "avg_tokens_per_request": round((total_input + total_output) / len(success)) if success else 0,
        "by_prompt_type": prompt_types,
        "model": success[-1].get("model", "N/A") if success else "N/A",
        "backend": success[-1].get("backend", "N/A") if success else "N/A",
    }


def get_overall_system_health() -> dict:
    """Aggregates all KPI sources into a system health summary."""
    pipeline = get_pipeline_health()
    quality = get_data_quality_scores()
    flights = get_flight_kpis()
    passengers = get_passenger_kpis()
    safety = get_safety_kpis()
    environmental = get_environmental_compliance()

    # Determine overall status based on thresholds
    issues = []
    if isinstance(pipeline, dict) and pipeline.get("success_rate", 100) < 99:
        issues.append("Pipeline success rate below 99%")
    if isinstance(flights, dict) and flights.get("otp_pct", 100) < 80:
        issues.append("Flight OTP below 80%")
    if isinstance(passengers, dict) and passengers.get("avg_wait_min", 0) > 15:
        issues.append("Security wait time exceeds 15 min")
    if isinstance(safety, dict) and safety.get("avg_response_sec", 0) > 120:
        issues.append("Safety incident response exceeds 120 sec")
    if isinstance(environmental, dict) and environmental.get("compliance_pct", 100) < 95:
        issues.append("Environmental compliance below 95%")

    if not issues:
        status = "healthy"
    elif len(issues) <= 2:
        status = "warning"
    else:
        status = "critical"

    return {
        "status": status,
        "issues": issues,
        "pipeline": pipeline,
        "quality": quality,
        "flights": flights,
        "passengers": passengers,
        "safety": safety,
        "environmental": environmental,
    }
