"""Tests for pipeline.silver_transformation — validated Parquet output."""

import json
import os

import pandas as pd
import pytest

from pipeline.silver_transformation import transform_to_silver


def _write_bronze_json(tmp_path, stream: str, records: list[dict]):
    """Write test records to a bronze JSON file."""
    bronze_dir = tmp_path / "data" / "bronze" / stream
    bronze_dir.mkdir(parents=True, exist_ok=True)
    filepath = bronze_dir / "test_events.json"
    with open(filepath, "w") as f:
        json.dump(records, f)


class TestTransformToSilver:
    def test_valid_records_written_to_silver(self, tmp_path, monkeypatch, make_flight_event):
        monkeypatch.setattr("pipeline.silver_transformation.BASE_DIR", str(tmp_path))
        records = [make_flight_event() for _ in range(5)]
        _write_bronze_json(tmp_path, "flights", records)

        result = transform_to_silver("flights")

        assert result["total_records"] == 5
        assert result["passed"] == 5
        assert result["failed"] == 0
        assert result["quality_score"] == 1.0

        silver_path = tmp_path / "data" / "silver" / "flights.parquet"
        assert silver_path.exists()
        df = pd.read_parquet(silver_path)
        assert len(df) == 5

    def test_invalid_records_quarantined(self, tmp_path, monkeypatch, make_flight_event):
        monkeypatch.setattr("pipeline.silver_transformation.BASE_DIR", str(tmp_path))
        valid = make_flight_event()
        invalid = make_flight_event(flight_id="bad!", status="nope")
        _write_bronze_json(tmp_path, "flights", [valid, invalid])

        result = transform_to_silver("flights")

        assert result["total_records"] == 2
        assert result["passed"] == 1
        assert result["failed"] == 1

        quarantine_path = tmp_path / "data" / "quarantine" / "flights_quarantine.parquet"
        assert quarantine_path.exists()
        df_q = pd.read_parquet(quarantine_path)
        assert len(df_q) == 1
        # Reasons stored as JSON string
        reasons = json.loads(df_q["_quarantine_reasons"].iloc[0])
        assert "flight_id_format" in reasons

    def test_empty_stream(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.silver_transformation.BASE_DIR", str(tmp_path))
        result = transform_to_silver("flights")

        assert result["total_records"] == 0
        assert result["quality_score"] == 1.0

    def test_failure_reasons_counted(self, tmp_path, monkeypatch, make_passenger_event):
        monkeypatch.setattr("pipeline.silver_transformation.BASE_DIR", str(tmp_path))
        records = [
            make_passenger_event(wait_time_minutes=-1, checkpoint=None),
            make_passenger_event(wait_time_minutes=-1),
            make_passenger_event(),
        ]
        _write_bronze_json(tmp_path, "passengers", records)

        result = transform_to_silver("passengers")

        assert result["failed"] == 2
        assert result["passed"] == 1
        assert "wait_time_range" in result["failure_reasons"]
        assert result["failure_reasons"]["wait_time_range"] == 2

    def test_quality_score_calculation(self, tmp_path, monkeypatch, make_cargo_event):
        monkeypatch.setattr("pipeline.silver_transformation.BASE_DIR", str(tmp_path))
        records = [
            make_cargo_event(),
            make_cargo_event(),
            make_cargo_event(weight_kg=600),  # invalid
            make_cargo_event(weight_kg=600),  # invalid
        ]
        _write_bronze_json(tmp_path, "cargo", records)

        result = transform_to_silver("cargo")

        assert result["quality_score"] == 0.5  # 2/4
