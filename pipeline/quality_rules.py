"""AeroOps AI — Quality validation rules per IoT stream."""

import re
from typing import Any

QUALITY_RULES = {
    "flights": [
        {"rule": "flight_id_format", "field": "flight_id", "type": "regex", "pattern": r"^[A-Z0-9]{2}\d{3,4}$"},
        {"rule": "status_enum", "field": "status", "type": "enum", "allowed": ["scheduled", "boarding", "departed", "arrived", "delayed", "cancelled"]},
        {"rule": "delay_non_negative", "field": "delay_minutes", "type": "range", "min": 0},
        {"rule": "passenger_range", "field": "passenger_count", "type": "range", "min": 1, "max": 600},
        {"rule": "scheduled_time_not_null", "field": "scheduled_time", "type": "not_null"},
    ],
    "passengers": [
        {"rule": "passenger_count_range", "field": "passenger_count", "type": "range", "min": 0, "max": 5000},
        {"rule": "wait_time_range", "field": "wait_time_minutes", "type": "range", "min": 0, "max": 180},
        {"rule": "throughput_non_negative", "field": "throughput_per_hour", "type": "range", "min": 0},
        {"rule": "checkpoint_not_null", "field": "checkpoint", "type": "not_null"},
    ],
    "cargo": [
        {"rule": "item_type_enum", "field": "item_type", "type": "enum", "allowed": ["baggage", "cargo", "mail"]},
        {"rule": "status_enum", "field": "status", "type": "enum", "allowed": ["checked_in", "in_transit", "loaded", "delivered", "lost"]},
        {"rule": "weight_range", "field": "weight_kg", "type": "range", "min": 0.1, "max": 500},
        {"rule": "processing_time_non_negative", "field": "processing_time_sec", "type": "range", "min": 0},
    ],
    "environmental": [
        {"rule": "temperature_range", "field": "temperature_c", "type": "range", "min": -10, "max": 50},
        {"rule": "humidity_range", "field": "humidity_pct", "type": "range", "min": 0, "max": 100},
        {"rule": "co2_range", "field": "co2_ppm", "type": "range", "min": 200, "max": 5000},
        {"rule": "aqi_range", "field": "air_quality_index", "type": "range", "min": 0, "max": 500},
        {"rule": "hvac_enum", "field": "hvac_status", "type": "enum", "allowed": ["normal", "degraded", "offline"]},
    ],
    "runway": [
        {"rule": "wind_speed_range", "field": "wind_speed_kph", "type": "range", "min": 0, "max": 200},
        {"rule": "visibility_range", "field": "visibility_m", "type": "range", "min": 0, "max": 20000},
        {"rule": "friction_range", "field": "friction_index", "type": "range", "min": 0.0, "max": 1.0},
        {"rule": "wind_direction_range", "field": "wind_direction_deg", "type": "range", "min": 0, "max": 360},
        {"rule": "precipitation_enum", "field": "precipitation", "type": "enum", "allowed": ["none", "rain", "snow", "ice"]},
        {"rule": "runway_status_enum", "field": "runway_status", "type": "enum", "allowed": ["active", "maintenance", "weather_hold"]},
    ],
    "security": [
        {"rule": "alert_type_enum", "field": "alert_type", "type": "enum", "allowed": ["routine_scan", "anomaly", "breach", "device_alert"]},
        {"rule": "severity_enum", "field": "severity", "type": "enum", "allowed": ["low", "medium", "high", "critical"]},
        {"rule": "resolution_enum", "field": "resolution_status", "type": "enum", "allowed": ["auto_cleared", "manual_review", "escalated"]},
        {"rule": "response_time_non_negative", "field": "response_time_sec", "type": "range", "min": 0, "allow_null": True},
    ],
}


def _check_rule(value: Any, rule: dict) -> bool:
    """Check a single value against a rule definition."""
    allow_null = rule.get("allow_null", False)

    if value is None:
        return rule["type"] != "not_null" and allow_null

    rule_type = rule["type"]

    if rule_type == "not_null":
        return value is not None and str(value).strip() != ""

    if rule_type == "regex":
        return bool(re.match(rule["pattern"], str(value)))

    if rule_type == "enum":
        return value in rule["allowed"]

    if rule_type == "range":
        try:
            num = float(value)
        except (TypeError, ValueError):
            return False
        if "min" in rule and num < rule["min"]:
            return False
        if "max" in rule and num > rule["max"]:
            return False
        return True

    return True


def validate_record(record: dict, stream: str) -> tuple[bool, list[str]]:
    """Validate a record against all rules for its stream.

    Returns:
        (passed, failed_rules): A boolean indicating overall pass/fail and a
        list of rule names that failed.
    """
    rules = QUALITY_RULES.get(stream, [])
    failed: list[str] = []

    for rule in rules:
        field = rule["field"]
        value = record.get(field)
        if not _check_rule(value, rule):
            failed.append(rule["rule"])

    return (len(failed) == 0, failed)
