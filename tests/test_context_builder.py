"""Tests for ai.context_builder — AI context assembly."""

import pytest

from ai.context_builder import KPI_THRESHOLDS, format_context_for_prompt


# ---------------------------------------------------------------------------
# format_context_for_prompt — pure string formatting, no I/O
# ---------------------------------------------------------------------------

class TestFormatContextForPrompt:
    def test_includes_timestamp(self):
        ctx = {"timestamp": "2026-04-20T10:00:00"}
        result = format_context_for_prompt(ctx)
        assert "2026-04-20T10:00:00" in result

    def test_includes_pipeline_health(self):
        ctx = {
            "timestamp": "2026-04-20T10:00:00",
            "pipeline_health": {
                "total_runs": 10,
                "success_rate": 95.0,
                "avg_duration_sec": 1.5,
            },
        }
        result = format_context_for_prompt(ctx)
        assert "PIPELINE HEALTH" in result
        assert "95.0" in result

    def test_includes_per_stream_health(self):
        ctx = {
            "timestamp": "now",
            "pipeline_health": {
                "total_runs": 5,
                "success_rate": 100,
                "avg_duration_sec": 1.0,
                "per_stream": {
                    "flights": {"success_rate": 100, "runs": 5},
                },
            },
        }
        result = format_context_for_prompt(ctx)
        assert "flights" in result

    def test_includes_kpis(self):
        ctx = {
            "timestamp": "now",
            "kpi_summary": {
                "flight_otp": {"value": 85.0, "status": "healthy", "target": 80, "unit": "%"},
            },
        }
        result = format_context_for_prompt(ctx)
        assert "KPIs" in result
        assert "85.0" in result
        assert "✅" in result

    def test_warning_kpi_shows_warning_icon(self):
        ctx = {
            "timestamp": "now",
            "kpi_summary": {
                "flight_otp": {"value": 70.0, "status": "warning", "target": 80, "unit": "%"},
            },
        }
        result = format_context_for_prompt(ctx)
        assert "⚠️" in result

    def test_skips_no_data_kpis(self):
        ctx = {
            "timestamp": "now",
            "kpi_summary": {
                "flight_otp": {"value": None, "status": "no_data", "target": 80, "unit": "%"},
            },
        }
        result = format_context_for_prompt(ctx)
        assert "KPIs" not in result

    def test_includes_quality_issues(self):
        ctx = {
            "timestamp": "now",
            "quality_issues": {
                "passengers_quarantine": {
                    "quarantined_records": 50,
                    "top_failure_reasons": {"wait_time_range": 30, "checkpoint_not_null": 20},
                },
            },
        }
        result = format_context_for_prompt(ctx)
        assert "QUALITY ISSUES" in result
        assert "50 quarantined" in result

    def test_includes_anomalies(self):
        ctx = {
            "timestamp": "now",
            "anomalies": {
                "count": 2,
                "recent_failures": [
                    {"stream": "flights", "stage": "silver", "quality_score": 0.95, "failed_records": 5, "total_records": 100},
                ],
            },
        }
        result = format_context_for_prompt(ctx)
        assert "ANOMALIES" in result

    def test_includes_lineage_impact(self):
        ctx = {
            "timestamp": "now",
            "lineage_impact": {
                "flights": {"affected_kpis": ["Flight OTP", "Avg Delay"]},
            },
        }
        result = format_context_for_prompt(ctx)
        assert "IMPACT" in result
        assert "Flight OTP" in result

    def test_empty_context(self):
        result = format_context_for_prompt({})
        assert "Timestamp: N/A" in result

    def test_no_anomalies_skips_section(self):
        ctx = {"timestamp": "now", "anomalies": {"count": 0, "recent_failures": []}}
        result = format_context_for_prompt(ctx)
        assert "ANOMALIES" not in result


# ---------------------------------------------------------------------------
# KPI_THRESHOLDS structure
# ---------------------------------------------------------------------------

class TestKPIThresholds:
    def test_all_thresholds_have_required_keys(self):
        for name, threshold in KPI_THRESHOLDS.items():
            assert "target" in threshold, f"{name} missing 'target'"
            assert "unit" in threshold, f"{name} missing 'unit'"
            assert "direction" in threshold, f"{name} missing 'direction'"

    def test_direction_values_are_valid(self):
        for name, threshold in KPI_THRESHOLDS.items():
            assert threshold["direction"] in ("above", "below"), (
                f"{name} has invalid direction: {threshold['direction']}"
            )
