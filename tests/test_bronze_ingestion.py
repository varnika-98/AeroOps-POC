"""Tests for pipeline.bronze_ingestion — raw JSON storage."""

import json

import pytest

from pipeline.bronze_ingestion import ingest_to_bronze


class TestIngestToBronze:
    def test_writes_json_file(self, tmp_path, monkeypatch, make_flight_event):
        monkeypatch.setattr("pipeline.bronze_ingestion.BASE_DIR", str(tmp_path))
        events = [make_flight_event(), make_flight_event(flight_id="BB5678")]

        filepath = ingest_to_bronze("flights", events)

        assert filepath.endswith(".json")
        with open(filepath, "r") as f:
            data = json.load(f)
        assert len(data) == 2

    def test_adds_ingested_at(self, tmp_path, monkeypatch, make_flight_event):
        monkeypatch.setattr("pipeline.bronze_ingestion.BASE_DIR", str(tmp_path))
        events = [make_flight_event()]

        filepath = ingest_to_bronze("flights", events)

        with open(filepath, "r") as f:
            data = json.load(f)
        assert "_ingested_at" in data[0]

    def test_creates_stream_directory(self, tmp_path, monkeypatch, make_flight_event):
        monkeypatch.setattr("pipeline.bronze_ingestion.BASE_DIR", str(tmp_path))
        ingest_to_bronze("flights", [make_flight_event()])

        bronze_dir = tmp_path / "data" / "bronze" / "flights"
        assert bronze_dir.exists()

    def test_raises_on_empty_events(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.bronze_ingestion.BASE_DIR", str(tmp_path))
        with pytest.raises(ValueError, match="No events provided"):
            ingest_to_bronze("flights", [])

    def test_preserves_original_fields(self, tmp_path, monkeypatch, make_cargo_event):
        monkeypatch.setattr("pipeline.bronze_ingestion.BASE_DIR", str(tmp_path))
        event = make_cargo_event(weight_kg=42.5)

        filepath = ingest_to_bronze("cargo", [event])

        with open(filepath, "r") as f:
            data = json.load(f)
        assert data[0]["weight_kg"] == 42.5
        assert data[0]["item_type"] == "baggage"
