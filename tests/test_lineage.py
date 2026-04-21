"""Tests for utils.lineage — data lineage tracking."""

import pytest

from utils.lineage import LINEAGE_MODEL, get_impact_analysis, get_reverse_lineage


# ---------------------------------------------------------------------------
# LINEAGE_MODEL structure
# ---------------------------------------------------------------------------

class TestLineageModel:
    EXPECTED_STREAMS = ["flights", "passengers", "cargo", "environmental", "runway", "security"]

    def test_all_streams_present(self):
        for stream in self.EXPECTED_STREAMS:
            assert stream in LINEAGE_MODEL

    def test_each_stream_has_required_keys(self):
        for stream, model in LINEAGE_MODEL.items():
            assert "bronze" in model, f"{stream} missing 'bronze'"
            assert "silver" in model, f"{stream} missing 'silver'"
            assert "gold" in model, f"{stream} missing 'gold'"
            assert "kpis" in model, f"{stream} missing 'kpis'"

    def test_gold_is_list(self):
        for stream, model in LINEAGE_MODEL.items():
            assert isinstance(model["gold"], list)

    def test_kpis_is_list(self):
        for stream, model in LINEAGE_MODEL.items():
            assert isinstance(model["kpis"], list)
            assert len(model["kpis"]) > 0


# ---------------------------------------------------------------------------
# get_impact_analysis — pure logic, no I/O
# ---------------------------------------------------------------------------

class TestGetImpactAnalysis:
    def test_returns_affected_kpis(self):
        result = get_impact_analysis("flights")
        assert "affected_kpis" in result
        assert len(result["affected_kpis"]) > 0

    def test_returns_gold_tables(self):
        result = get_impact_analysis("flights")
        assert "affected_gold_tables" in result
        assert isinstance(result["affected_gold_tables"], list)

    def test_severity_high_for_flights(self):
        result = get_impact_analysis("flights")
        # flights has 3 KPIs → severity "high"
        assert result["severity"] == "high"

    def test_severity_medium_for_cargo(self):
        result = get_impact_analysis("cargo")
        # cargo has 2 KPIs → severity "medium"
        assert result["severity"] == "medium"

    def test_shared_gold_tables(self):
        # cargo and flights share flight_kpis.parquet
        result = get_impact_analysis("cargo")
        assert "flights" in result["shared_gold_with"]

    def test_unknown_stream(self):
        result = get_impact_analysis("nonexistent")
        assert "error" in result

    @pytest.mark.parametrize("stream", LINEAGE_MODEL.keys())
    def test_all_streams_return_valid_result(self, stream):
        result = get_impact_analysis(stream)
        assert "error" not in result
        assert result["stream"] == stream


# ---------------------------------------------------------------------------
# get_reverse_lineage — pure logic, no I/O
# ---------------------------------------------------------------------------

class TestGetReverseLineage:
    def test_flight_otp_traces_to_flights(self):
        sources = get_reverse_lineage("Flight OTP")
        assert len(sources) == 1
        assert sources[0]["stream"] == "flights"

    def test_unknown_kpi_returns_empty(self):
        sources = get_reverse_lineage("Nonexistent KPI")
        assert sources == []

    def test_source_has_required_keys(self):
        sources = get_reverse_lineage("Flight OTP")
        for src in sources:
            assert "stream" in src
            assert "bronze" in src
            assert "silver" in src
            assert "gold" in src

    def test_all_kpis_traceable(self):
        """Every KPI defined in LINEAGE_MODEL should be traceable."""
        all_kpis = set()
        for model in LINEAGE_MODEL.values():
            all_kpis.update(model["kpis"])

        for kpi in all_kpis:
            sources = get_reverse_lineage(kpi)
            assert len(sources) > 0, f"KPI '{kpi}' has no reverse lineage"
