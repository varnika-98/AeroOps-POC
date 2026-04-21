"""Tests for simulator.failure_injector — failure injection scenarios."""

import copy
from datetime import datetime

import pytest

from simulator.failure_injector import (
    inject_schema_drift,
    inject_sensor_outage,
    inject_traffic_spike,
)
from simulator.airport_generator import generate_runway_events, generate_passenger_events
from pipeline.quality_rules import validate_record


@pytest.fixture
def runway_events():
    """Fresh runway events dict for each test."""
    ts = datetime(2026, 4, 20, 10, 0, 0)
    return {"runway": generate_runway_events(ts, 20, 0)}


@pytest.fixture
def passenger_events():
    """Fresh passenger events dict for each test."""
    ts = datetime(2026, 4, 20, 10, 0, 0)
    return {"passengers": generate_passenger_events(ts, 20, 0)}


class TestInjectSchemaDrift:
    def test_mutates_wind_speed(self, runway_events):
        original_speeds = [e["wind_speed_kph"] for e in runway_events["runway"]]
        inject_schema_drift(runway_events, stream="runway")
        for i, event in enumerate(runway_events["runway"]):
            assert event["wind_speed_kph"] == pytest.approx(original_speeds[i] * 4.0, rel=1e-3)

    def test_causes_validation_failures(self, runway_events):
        inject_schema_drift(runway_events, stream="runway")
        failures = 0
        for event in runway_events["runway"]:
            passed, _ = validate_record(event, "runway")
            if not passed:
                failures += 1
        assert failures > 0, "Schema drift should cause some validation failures"

    def test_raises_on_missing_stream(self, runway_events):
        with pytest.raises(ValueError, match="Stream 'nonexistent' not found"):
            inject_schema_drift(runway_events, stream="nonexistent")

    def test_returns_same_dict(self, runway_events):
        result = inject_schema_drift(runway_events, stream="runway")
        assert result is runway_events


class TestInjectSensorOutage:
    def test_corrupts_records(self, passenger_events):
        inject_sensor_outage(passenger_events, stream="passengers", checkpoints=2)
        corrupted = [e for e in passenger_events["passengers"] if e["checkpoint"] is None]
        assert len(corrupted) > 0

    def test_sets_negative_wait_time(self, passenger_events):
        inject_sensor_outage(passenger_events, stream="passengers", checkpoints=2)
        for event in passenger_events["passengers"]:
            if event["checkpoint"] is None:
                assert event["wait_time_minutes"] == -1

    def test_causes_validation_failures(self, passenger_events):
        inject_sensor_outage(passenger_events, stream="passengers", checkpoints=2)
        failures = 0
        for event in passenger_events["passengers"]:
            passed, _ = validate_record(event, "passengers")
            if not passed:
                failures += 1
        assert failures > 0

    def test_raises_on_missing_stream(self, passenger_events):
        with pytest.raises(ValueError, match="not found"):
            inject_sensor_outage(passenger_events, stream="nonexistent")


class TestInjectTrafficSpike:
    def test_returns_multiplier(self):
        assert inject_traffic_spike(3.0) == 3.0

    def test_default_multiplier(self):
        assert inject_traffic_spike() == 3.0

    def test_custom_multiplier(self):
        assert inject_traffic_spike(5.0) == 5.0
