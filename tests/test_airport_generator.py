"""Tests for simulator.airport_generator — event generation."""

import math
import random
from datetime import datetime

import pytest

from simulator.airport_generator import (
    STREAM_GENERATORS,
    _diurnal_temperature,
    _is_peak,
    _iso,
    _make_event_id,
    generate_all_events,
    generate_cargo_events,
    generate_environmental_events,
    generate_flight_events,
    generate_passenger_events,
    generate_runway_events,
    generate_security_events,
)
from pipeline.quality_rules import validate_record


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_make_event_id_format(self):
        ts = datetime(2026, 4, 20, 10, 0, 0)
        result = _make_event_id("FLT", ts, 42)
        assert result == "FLT-20260420-000042"

    def test_make_event_id_large_seq(self):
        ts = datetime(2026, 1, 1)
        result = _make_event_id("PAX", ts, 999999)
        assert result == "PAX-20260101-999999"

    def test_iso_format(self):
        ts = datetime(2026, 4, 20, 10, 30, 45)
        assert _iso(ts) == "2026-04-20T10:30:45"

    def test_is_peak_during_morning(self):
        # AIRPORT_CONFIG peak_hours includes morning and evening windows
        assert _is_peak(7) is True

    def test_is_peak_during_off_hours(self):
        assert _is_peak(2) is False

    def test_diurnal_temperature_peak(self):
        # Peak at ~14:00 (hour - 6 = 8, sin(pi*8/12) = sin(2pi/3))
        temp_14 = _diurnal_temperature(14)
        temp_2 = _diurnal_temperature(2)
        assert temp_14 > temp_2

    def test_diurnal_temperature_default_base(self):
        temp = _diurnal_temperature(6)
        # At hour=6: sin(0) = 0, so temp should be ~base
        assert abs(temp - 22.0) < 0.1


# ---------------------------------------------------------------------------
# Stream generator schema tests
# ---------------------------------------------------------------------------

FLIGHT_KEYS = {
    "event_id", "timestamp", "flight_id", "gate", "terminal", "status",
    "scheduled_time", "actual_time", "delay_minutes", "aircraft_type",
    "passenger_count",
}

PASSENGER_KEYS = {
    "event_id", "timestamp", "terminal", "checkpoint", "zone",
    "passenger_count", "wait_time_minutes", "throughput_per_hour", "queue_length",
}

CARGO_KEYS = {
    "event_id", "timestamp", "item_type", "item_id", "flight_id",
    "scan_point", "status", "weight_kg", "processing_time_sec",
}

ENVIRONMENTAL_KEYS = {
    "event_id", "timestamp", "terminal", "zone", "temperature_c",
    "humidity_pct", "co2_ppm", "air_quality_index", "hvac_status",
}

RUNWAY_KEYS = {
    "event_id", "timestamp", "runway_id", "surface_temp_c", "wind_speed_kph",
    "wind_direction_deg", "visibility_m", "friction_index", "precipitation",
    "runway_status",
}

SECURITY_KEYS = {
    "event_id", "timestamp", "checkpoint_id", "alert_type", "severity",
    "device_type", "response_time_sec", "resolution_status", "zone",
}


class TestStreamGenerators:
    """Verify each generator returns correct schema and count."""

    def test_flight_events_schema(self, base_timestamp):
        events = generate_flight_events(base_timestamp, 5, 0)
        assert len(events) == 5
        for e in events:
            assert set(e.keys()) == FLIGHT_KEYS

    def test_passenger_events_schema(self, base_timestamp):
        events = generate_passenger_events(base_timestamp, 5, 0)
        assert len(events) == 5
        for e in events:
            assert set(e.keys()) == PASSENGER_KEYS

    def test_cargo_events_schema(self, base_timestamp):
        events = generate_cargo_events(base_timestamp, 5, 0)
        assert len(events) == 5
        for e in events:
            assert set(e.keys()) == CARGO_KEYS

    def test_environmental_events_schema(self, base_timestamp):
        events = generate_environmental_events(base_timestamp, 5, 0)
        assert len(events) == 5
        for e in events:
            assert set(e.keys()) == ENVIRONMENTAL_KEYS

    def test_runway_events_schema(self, base_timestamp):
        events = generate_runway_events(base_timestamp, 5, 0)
        assert len(events) == 5
        for e in events:
            assert set(e.keys()) == RUNWAY_KEYS

    def test_security_events_schema(self, base_timestamp):
        events = generate_security_events(base_timestamp, 5, 0)
        assert len(events) == 5
        for e in events:
            assert set(e.keys()) == SECURITY_KEYS

    def test_zero_count_returns_empty(self, base_timestamp):
        assert generate_flight_events(base_timestamp, 0, 0) == []

    def test_event_ids_are_unique(self, base_timestamp):
        events = generate_flight_events(base_timestamp, 20, 0)
        ids = [e["event_id"] for e in events]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# generate_all_events tests
# ---------------------------------------------------------------------------

class TestGenerateAllEvents:
    def test_returns_all_streams(self):
        events = generate_all_events(
            base_date=datetime(2026, 4, 20), hours=1, rate_multiplier=1.0
        )
        expected_streams = {"flights", "passengers", "cargo", "environmental", "runway", "security"}
        assert set(events.keys()) == expected_streams

    def test_all_streams_have_events(self):
        events = generate_all_events(
            base_date=datetime(2026, 4, 20), hours=1, rate_multiplier=1.0
        )
        for stream, stream_events in events.items():
            assert len(stream_events) > 0, f"No events for {stream}"

    def test_rate_multiplier_increases_volume(self):
        events_1x = generate_all_events(
            base_date=datetime(2026, 4, 20), hours=1, rate_multiplier=1.0
        )
        random.seed(42)  # Reset for fair comparison
        events_3x = generate_all_events(
            base_date=datetime(2026, 4, 20), hours=1, rate_multiplier=3.0
        )
        total_1x = sum(len(v) for v in events_1x.values())
        total_3x = sum(len(v) for v in events_3x.values())
        assert total_3x > total_1x

    def test_stream_generators_registry(self):
        expected = {"flights", "passengers", "cargo", "environmental", "runway", "security"}
        assert set(STREAM_GENERATORS.keys()) == expected


# ---------------------------------------------------------------------------
# Contract test: generated events pass quality rules
# ---------------------------------------------------------------------------

class TestGeneratorValidatorContract:
    """Generated events should pass quality validation rules."""

    @pytest.mark.parametrize("stream,gen_fn", list(STREAM_GENERATORS.items()))
    def test_generated_events_pass_validation(self, stream, gen_fn, base_timestamp):
        events = gen_fn(base_timestamp, 10, 0)
        for event in events:
            passed, failed = validate_record(event, stream)
            assert passed, (
                f"Generated {stream} event failed validation: {failed}\n"
                f"Event: {event}"
            )
