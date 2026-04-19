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
    df = _safe_read("data/logs/pipeline_runs.parquet")
    if df is None:
        return _NO_DATA.copy()

    total = len(df)
    if total == 0:
        return {"total_runs": 0, "success_rate": 0, "avg_duration_sec": 0, "throughput_per_hour": 0}

    success = (df["status"] == "success").sum() if "status" in df.columns else 0
    avg_dur = round(df["duration_sec"].mean(), 2) if "duration_sec" in df.columns else 0

    # Estimate throughput from records processed
    records = df["records_processed"].sum() if "records_processed" in df.columns else 0

    return {
        "total_runs": int(total),
        "successful_runs": int(success),
        "success_rate": round(success / total * 100, 2),
        "avg_duration_sec": avg_dur,
        "total_records_processed": int(records),
    }


def get_data_quality_scores() -> dict:
    """Returns quality score per stream from quality_kpis."""
    df = _safe_read("data/gold/quality_kpis.parquet")
    if df is None:
        return _NO_DATA.copy()

    result = {}
    if "stream" in df.columns and "quality_score" in df.columns:
        for stream, grp in df.groupby("stream"):
            result[stream] = {
                "quality_score": round(grp["quality_score"].mean(), 2),
                "min_score": round(grp["quality_score"].min(), 2),
                "max_score": round(grp["quality_score"].max(), 2),
                "records": len(grp),
            }
    elif "quality_score" in df.columns:
        result["overall"] = {
            "quality_score": round(df["quality_score"].mean(), 2),
            "min_score": round(df["quality_score"].min(), 2),
            "max_score": round(df["quality_score"].max(), 2),
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
    if "on_time_pct" in df.columns:
        result["otp_pct"] = round(df["on_time_pct"].mean(), 2)
    if "avg_delay_min" in df.columns:
        result["avg_delay_min"] = round(df["avg_delay_min"].mean(), 2)
    if "gate_utilization" in df.columns:
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
    if "throughput_per_hour" in df.columns:
        result["throughput_per_hour"] = round(df["throughput_per_hour"].mean(), 2)
    if "avg_wait_min" in df.columns:
        result["avg_wait_min"] = round(df["avg_wait_min"].mean(), 2)
    if "checkpoint_efficiency" in df.columns:
        result["checkpoint_efficiency_pct"] = round(df["checkpoint_efficiency"].mean(), 2)
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
    if "total_alerts" in df.columns:
        result["total_alerts"] = int(df["total_alerts"].sum())
    if "resolved_alerts" in df.columns:
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
