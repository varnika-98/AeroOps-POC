# AeroOps AI — Airport IoT Data Simulator
"""Simulator package for generating realistic airport IoT telemetry data."""

from simulator.config import AIRPORT_CONFIG, STREAM_NAMES
from simulator.airport_generator import (
    generate_all_events,
    write_events_to_json,
)
from simulator.pipeline_log_generator import (
    generate_pipeline_logs,
    write_pipeline_logs,
)
from simulator.failure_injector import (
    inject_schema_drift,
    inject_sensor_outage,
    inject_traffic_spike,
)

__all__ = [
    "AIRPORT_CONFIG",
    "STREAM_NAMES",
    "generate_all_events",
    "write_events_to_json",
    "generate_pipeline_logs",
    "write_pipeline_logs",
    "inject_schema_drift",
    "inject_sensor_outage",
    "inject_traffic_spike",
]
