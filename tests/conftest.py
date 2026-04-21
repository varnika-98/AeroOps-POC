"""Shared fixtures for AeroOps unit tests."""

import random
from datetime import datetime

import pytest


@pytest.fixture(autouse=True)
def seed_random():
    """Reset random seed before every test for deterministic results."""
    random.seed(42)


@pytest.fixture
def base_timestamp() -> datetime:
    return datetime(2026, 4, 20, 10, 0, 0)


# ---------------------------------------------------------------------------
# Event factory fixtures — return fresh dicts each call
# ---------------------------------------------------------------------------

@pytest.fixture
def make_flight_event():
    def _factory(**overrides) -> dict:
        event = {
            "event_id": "FLT-20260420-000001",
            "timestamp": "2026-04-20T10:00:00",
            "flight_id": "AA1234",
            "gate": "Gate-A1",
            "terminal": "Terminal-A",
            "status": "scheduled",
            "scheduled_time": "2026-04-20T10:30:00",
            "actual_time": "2026-04-20T10:30:00",
            "delay_minutes": 0,
            "aircraft_type": "A320",
            "passenger_count": 150,
        }
        event.update(overrides)
        return event
    return _factory


@pytest.fixture
def make_passenger_event():
    def _factory(**overrides) -> dict:
        event = {
            "event_id": "PAX-20260420-000001",
            "timestamp": "2026-04-20T10:00:00",
            "terminal": "Terminal-A",
            "checkpoint": "Checkpoint-A1",
            "zone": "Zone-A1",
            "passenger_count": 50,
            "wait_time_minutes": 12.5,
            "throughput_per_hour": 200,
            "queue_length": 15,
        }
        event.update(overrides)
        return event
    return _factory


@pytest.fixture
def make_cargo_event():
    def _factory(**overrides) -> dict:
        event = {
            "event_id": "CGO-20260420-000001",
            "timestamp": "2026-04-20T10:00:00",
            "item_type": "baggage",
            "item_id": "BAG-1234567",
            "flight_id": "AA1234",
            "scan_point": "Scan-A1",
            "status": "checked_in",
            "weight_kg": 23.5,
            "processing_time_sec": 120,
        }
        event.update(overrides)
        return event
    return _factory


@pytest.fixture
def make_environmental_event():
    def _factory(**overrides) -> dict:
        event = {
            "event_id": "ENV-20260420-000001",
            "timestamp": "2026-04-20T10:00:00",
            "terminal": "Terminal-A",
            "zone": "Zone-A1",
            "temperature_c": 22.5,
            "humidity_pct": 45.0,
            "co2_ppm": 500,
            "air_quality_index": 40,
            "hvac_status": "normal",
        }
        event.update(overrides)
        return event
    return _factory


@pytest.fixture
def make_runway_event():
    def _factory(**overrides) -> dict:
        event = {
            "event_id": "RWY-20260420-000001",
            "timestamp": "2026-04-20T10:00:00",
            "runway_id": "RW-09L",
            "surface_temp_c": 30.0,
            "wind_speed_kph": 25.0,
            "wind_direction_deg": 180,
            "visibility_m": 10000,
            "friction_index": 0.75,
            "precipitation": "none",
            "runway_status": "active",
        }
        event.update(overrides)
        return event
    return _factory


@pytest.fixture
def make_security_event():
    def _factory(**overrides) -> dict:
        event = {
            "event_id": "SEC-20260420-000001",
            "timestamp": "2026-04-20T10:00:00",
            "checkpoint_id": "SEC-1",
            "alert_type": "routine_scan",
            "severity": "low",
            "device_type": "X-Ray Scanner",
            "response_time_sec": None,
            "resolution_status": "auto_cleared",
            "zone": "Zone-A1",
        }
        event.update(overrides)
        return event
    return _factory
