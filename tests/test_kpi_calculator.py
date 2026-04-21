"""Tests for utils.kpi_calculator — KPI computation functions."""

import pandas as pd
import pytest

from utils import kpi_calculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_safe_read(data_map: dict):
    """Return a monkeypatch-ready _safe_read that serves DataFrames from a dict."""
    def _fake_read(relative_path: str) -> pd.DataFrame | None:
        return data_map.get(relative_path)
    return _fake_read


# ---------------------------------------------------------------------------
# get_pipeline_health
# ---------------------------------------------------------------------------

class TestGetPipelineHealth:
    def test_no_data(self, monkeypatch):
        monkeypatch.setattr(kpi_calculator, "_safe_read", _mock_safe_read({}))
        result = kpi_calculator.get_pipeline_health()
        assert result["status"] == "no_data"

    def test_with_data(self, monkeypatch):
        df = pd.DataFrame({
            "run_timestamp": ["2026-04-20T10:00:00"] * 6,
            "stage": ["bronze", "silver", "gold"] * 2,
            "stream": ["flights", "flights", "flights", "passengers", "passengers", "passengers"],
            "total_records": [100, 100, 100, 200, 200, 200],
            "quality_score": [1.0, 0.98, 0.0, 1.0, 1.0, 0.0],
            "duration_sec": [0.5, 1.2, 0.3, 0.4, 1.0, 0.2],
        })
        monkeypatch.setattr(
            kpi_calculator, "_safe_read",
            _mock_safe_read({"data/logs/pipeline_logs.parquet": df}),
        )
        result = kpi_calculator.get_pipeline_health()
        assert "total_runs" in result
        assert "success_rate" in result
        assert result["total_records_processed"] == 900

    def test_empty_df(self, monkeypatch):
        df = pd.DataFrame(columns=["run_timestamp", "stage", "stream", "total_records", "quality_score", "duration_sec"])
        monkeypatch.setattr(
            kpi_calculator, "_safe_read",
            _mock_safe_read({"data/logs/pipeline_logs.parquet": df}),
        )
        result = kpi_calculator.get_pipeline_health()
        assert result["total_runs"] == 0


# ---------------------------------------------------------------------------
# get_data_quality_scores
# ---------------------------------------------------------------------------

class TestGetDataQualityScores:
    def test_no_data(self, monkeypatch):
        monkeypatch.setattr(kpi_calculator, "_safe_read", _mock_safe_read({}))
        result = kpi_calculator.get_data_quality_scores()
        assert result["status"] == "no_data"

    def test_with_validation_rate(self, monkeypatch):
        df = pd.DataFrame({
            "stream": ["flights", "passengers"],
            "validation_rate_pct": [98.5, 95.0],
        })
        monkeypatch.setattr(
            kpi_calculator, "_safe_read",
            _mock_safe_read({"data/gold/quality_kpis.parquet": df}),
        )
        result = kpi_calculator.get_data_quality_scores()
        assert "flights" in result
        assert result["flights"]["quality_score"] == 98.5


# ---------------------------------------------------------------------------
# get_flight_kpis
# ---------------------------------------------------------------------------

class TestGetFlightKpis:
    def test_no_data(self, monkeypatch):
        monkeypatch.setattr(kpi_calculator, "_safe_read", _mock_safe_read({}))
        result = kpi_calculator.get_flight_kpis()
        assert result["status"] == "no_data"

    def test_with_data(self, monkeypatch):
        df = pd.DataFrame({
            "otp_pct": [85.0, 90.0],
            "avg_delay_min": [10.0, 15.0],
            "gates_used": [20, 25],
            "total_flights": [50, 60],
        })
        monkeypatch.setattr(
            kpi_calculator, "_safe_read",
            _mock_safe_read({"data/gold/flight_kpis.parquet": df}),
        )
        result = kpi_calculator.get_flight_kpis()
        assert result["otp_pct"] == 87.5
        assert result["total_flights"] == 110


# ---------------------------------------------------------------------------
# get_passenger_kpis
# ---------------------------------------------------------------------------

class TestGetPassengerKpis:
    def test_no_data(self, monkeypatch):
        monkeypatch.setattr(kpi_calculator, "_safe_read", _mock_safe_read({}))
        result = kpi_calculator.get_passenger_kpis()
        assert result["status"] == "no_data"

    def test_with_data(self, monkeypatch):
        df = pd.DataFrame({
            "checkpoint": ["A1", "A2"],
            "avg_throughput": [200, 300],
            "avg_wait_min": [10.0, 12.0],
            "total_passengers": [1000, 1500],
        })
        monkeypatch.setattr(
            kpi_calculator, "_safe_read",
            _mock_safe_read({"data/gold/passenger_kpis.parquet": df}),
        )
        result = kpi_calculator.get_passenger_kpis()
        assert result["throughput_per_hour"] == 250.0
        assert result["total_passengers"] == 2500


# ---------------------------------------------------------------------------
# get_safety_kpis
# ---------------------------------------------------------------------------

class TestGetSafetyKpis:
    def test_no_data(self, monkeypatch):
        monkeypatch.setattr(kpi_calculator, "_safe_read", _mock_safe_read({}))
        result = kpi_calculator.get_safety_kpis()
        assert result["status"] == "no_data"

    def test_with_data(self, monkeypatch):
        df = pd.DataFrame({
            "severity": ["low", "high"],
            "alert_count": [100, 10],
            "avg_response_sec": [30.0, 60.0],
            "auto_cleared": [90, 5],
            "escalated": [10, 5],
        })
        monkeypatch.setattr(
            kpi_calculator, "_safe_read",
            _mock_safe_read({"data/gold/safety_kpis.parquet": df}),
        )
        result = kpi_calculator.get_safety_kpis()
        assert result["total_alerts"] == 110
        assert "avg_response_sec" in result


# ---------------------------------------------------------------------------
# get_ai_kpis
# ---------------------------------------------------------------------------

class TestGetAiKpis:
    def test_no_metrics(self, monkeypatch):
        monkeypatch.setattr(
            "ai.claude_client.load_ai_metrics", lambda: [], raising=False
        )
        result = kpi_calculator.get_ai_kpis()
        assert result["status"] == "no_data"

    def test_with_metrics(self, monkeypatch):
        metrics = [
            {
                "status": "success",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "cost_usd": 0.001,
                "latency_sec": 1.5,
                "prompt_type": "diagnose",
                "model": "claude-haiku",
                "backend": "anthropic",
            },
            {
                "status": "success",
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300,
                "cost_usd": 0.002,
                "latency_sec": 2.0,
                "prompt_type": "recommend",
                "model": "claude-haiku",
                "backend": "anthropic",
            },
        ]
        monkeypatch.setattr(
            "ai.claude_client.load_ai_metrics", lambda: metrics, raising=False
        )
        result = kpi_calculator.get_ai_kpis()
        assert result["total_requests"] == 2
        assert result["successful_requests"] == 2
        assert result["total_input_tokens"] == 300
