"""AeroOps AI — Gold layer aggregation (KPI computation via DuckDB)."""

import os

import duckdb
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
QUARANTINE_DIR = os.path.join(BASE_DIR, "data", "quarantine")
LOGS_DIR = os.path.join(BASE_DIR, "data", "logs")


def _silver_path(stream: str) -> str:
    return os.path.join(SILVER_DIR, f"{stream}.parquet")


def _has_silver(stream: str) -> bool:
    return os.path.isfile(_silver_path(stream))


def _write_gold(name: str, df: pd.DataFrame) -> int:
    """Write a DataFrame to the Gold directory and return the row count."""
    os.makedirs(GOLD_DIR, exist_ok=True)
    if df.empty:
        return 0
    df.to_parquet(os.path.join(GOLD_DIR, f"{name}.parquet"), index=False)
    return len(df)


def _compute_flight_kpis(con: duckdb.DuckDBPyConnection) -> int:
    if not _has_silver("flights"):
        return 0
    path = _silver_path("flights").replace("\\", "/")
    df = con.execute(f"""
        SELECT
            DATE_TRUNC('hour', CAST(scheduled_time AS TIMESTAMP)) AS hour,
            COUNT(*)                                               AS total_flights,
            COUNT(*) FILTER (WHERE CAST(delay_minutes AS DOUBLE) <= 15) AS on_time,
            ROUND(
                COUNT(*) FILTER (WHERE CAST(delay_minutes AS DOUBLE) <= 15)
                * 100.0 / COUNT(*), 1
            )                                                      AS otp_pct,
            ROUND(AVG(CAST(delay_minutes AS DOUBLE)), 1)           AS avg_delay_min,
            MAX(CAST(delay_minutes AS DOUBLE))                     AS max_delay_min,
            COUNT(DISTINCT gate)                                   AS gates_used
        FROM read_parquet('{path}')
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    return _write_gold("flight_kpis", df)


def _compute_passenger_kpis(con: duckdb.DuckDBPyConnection) -> int:
    if not _has_silver("passengers"):
        return 0
    path = _silver_path("passengers").replace("\\", "/")
    df = con.execute(f"""
        SELECT
            checkpoint,
            ROUND(AVG(CAST(wait_time_minutes AS DOUBLE)), 1)    AS avg_wait_min,
            MAX(CAST(wait_time_minutes AS DOUBLE))              AS max_wait_min,
            ROUND(AVG(CAST(throughput_per_hour AS DOUBLE)), 0)  AS avg_throughput,
            SUM(CAST(passenger_count AS INT))                   AS total_passengers
        FROM read_parquet('{path}')
        GROUP BY checkpoint
        ORDER BY avg_wait_min DESC
    """).fetchdf()
    return _write_gold("passenger_kpis", df)


def _compute_pipeline_kpis(con: duckdb.DuckDBPyConnection) -> int:
    logs_path = os.path.join(LOGS_DIR, "pipeline_logs.parquet").replace("\\", "/")
    if not os.path.isfile(logs_path):
        return 0
    df = con.execute(f"""
        SELECT
            stream,
            COUNT(*)                                           AS run_count,
            ROUND(AVG(duration_sec), 2)                        AS avg_duration_sec,
            ROUND(AVG(quality_score) * 100, 1)                 AS avg_quality_pct,
            SUM(total_records)                                 AS total_records_processed,
            ROUND(SUM(total_records) / NULLIF(SUM(duration_sec), 0), 0)
                                                               AS records_per_sec
        FROM read_parquet('{logs_path}')
        GROUP BY stream
        ORDER BY stream
    """).fetchdf()
    return _write_gold("pipeline_kpis", df)


def _compute_quality_kpis(con: duckdb.DuckDBPyConnection) -> int:
    """Compute validation pass rates and quarantine percentages per stream."""
    rows: list[dict] = []
    streams = ["flights", "passengers", "cargo", "environmental", "runway", "security"]

    for stream in streams:
        silver_count = 0
        quarantine_count = 0

        silver_p = _silver_path(stream).replace("\\", "/")
        if os.path.isfile(silver_p):
            silver_count = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{silver_p}')"
            ).fetchone()[0]

        quarantine_p = os.path.join(
            QUARANTINE_DIR, f"{stream}_quarantine.parquet"
        ).replace("\\", "/")
        if os.path.isfile(quarantine_p):
            quarantine_count = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{quarantine_p}')"
            ).fetchone()[0]

        total = silver_count + quarantine_count
        if total == 0:
            continue

        rows.append({
            "stream": stream,
            "total_records": total,
            "valid_records": silver_count,
            "quarantined_records": quarantine_count,
            "validation_rate_pct": round(silver_count * 100.0 / total, 1),
            "quarantine_pct": round(quarantine_count * 100.0 / total, 1),
        })

    if not rows:
        return 0
    return _write_gold("quality_kpis", pd.DataFrame(rows))


def _compute_safety_kpis(con: duckdb.DuckDBPyConnection) -> int:
    if not _has_silver("security"):
        return 0
    path = _silver_path("security").replace("\\", "/")
    df = con.execute(f"""
        SELECT
            severity,
            COUNT(*)                                                    AS alert_count,
            ROUND(AVG(CAST(response_time_sec AS DOUBLE)), 1)           AS avg_response_sec,
            COUNT(*) FILTER (WHERE resolution_status = 'auto_cleared')  AS auto_cleared,
            COUNT(*) FILTER (WHERE resolution_status = 'escalated')     AS escalated,
            ROUND(
                COUNT(*) FILTER (WHERE resolution_status != 'escalated')
                * 100.0 / COUNT(*), 1
            )                                                           AS resolution_rate_pct
        FROM read_parquet('{path}')
        GROUP BY severity
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
            END
    """).fetchdf()
    return _write_gold("safety_kpis", df)


def aggregate_to_gold() -> dict:
    """Compute Gold layer KPIs from Silver Parquet data using DuckDB.

    Returns:
        Summary dict mapping each KPI table name to its row count.
    """
    con = duckdb.connect()
    try:
        summary = {
            "flight_kpis": _compute_flight_kpis(con),
            "passenger_kpis": _compute_passenger_kpis(con),
            "pipeline_kpis": _compute_pipeline_kpis(con),
            "quality_kpis": _compute_quality_kpis(con),
            "safety_kpis": _compute_safety_kpis(con),
        }
    finally:
        con.close()

    return summary
