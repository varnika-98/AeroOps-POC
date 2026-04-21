"""Tests for pipeline.quality_rules — validation engine."""

import pytest

from pipeline.quality_rules import QUALITY_RULES, _check_rule, validate_record


# ---------------------------------------------------------------------------
# _check_rule — unit tests per rule type
# ---------------------------------------------------------------------------

class TestCheckRule:
    """Tests for the low-level _check_rule function."""

    # --- range ---
    def test_range_within(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule(50, rule) is True

    def test_range_at_min(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule(0, rule) is True

    def test_range_at_max(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule(100, rule) is True

    def test_range_below_min(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule(-1, rule) is False

    def test_range_above_max(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule(101, rule) is False

    def test_range_no_max(self):
        rule = {"type": "range", "min": 0}
        assert _check_rule(99999, rule) is True

    def test_range_string_number(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule("50", rule) is True

    def test_range_non_numeric(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule("abc", rule) is False

    def test_range_none_without_allow_null(self):
        rule = {"type": "range", "min": 0, "max": 100}
        assert _check_rule(None, rule) is False

    def test_range_none_with_allow_null(self):
        rule = {"type": "range", "min": 0, "max": 100, "allow_null": True}
        assert _check_rule(None, rule) is True

    # --- enum ---
    def test_enum_valid(self):
        rule = {"type": "enum", "allowed": ["a", "b", "c"]}
        assert _check_rule("b", rule) is True

    def test_enum_invalid(self):
        rule = {"type": "enum", "allowed": ["a", "b", "c"]}
        assert _check_rule("d", rule) is False

    def test_enum_none(self):
        rule = {"type": "enum", "allowed": ["a", "b"]}
        assert _check_rule(None, rule) is False

    # --- regex ---
    def test_regex_match(self):
        rule = {"type": "regex", "pattern": r"^[A-Z0-9]{2}\d{3,4}$"}
        assert _check_rule("AA1234", rule) is True

    def test_regex_no_match(self):
        rule = {"type": "regex", "pattern": r"^[A-Z0-9]{2}\d{3,4}$"}
        assert _check_rule("invalid", rule) is False

    def test_regex_none(self):
        rule = {"type": "regex", "pattern": r"^[A-Z]+$"}
        assert _check_rule(None, rule) is False

    # --- not_null ---
    def test_not_null_with_value(self):
        rule = {"type": "not_null"}
        assert _check_rule("hello", rule) is True

    def test_not_null_with_none(self):
        rule = {"type": "not_null"}
        assert _check_rule(None, rule) is False

    def test_not_null_with_empty_string(self):
        rule = {"type": "not_null"}
        assert _check_rule("", rule) is False

    def test_not_null_with_whitespace(self):
        rule = {"type": "not_null"}
        assert _check_rule("   ", rule) is False


# ---------------------------------------------------------------------------
# validate_record — integration tests per stream
# ---------------------------------------------------------------------------

class TestValidateRecord:
    """Tests for the full-record validate_record function."""

    def test_valid_flight(self, make_flight_event):
        event = make_flight_event()
        passed, failed = validate_record(event, "flights")
        assert passed is True
        assert failed == []

    def test_invalid_flight_id(self, make_flight_event):
        event = make_flight_event(flight_id="bad-id!")
        passed, failed = validate_record(event, "flights")
        assert passed is False
        assert "flight_id_format" in failed

    def test_invalid_flight_status(self, make_flight_event):
        event = make_flight_event(status="unknown_status")
        passed, failed = validate_record(event, "flights")
        assert passed is False
        assert "status_enum" in failed

    def test_negative_delay(self, make_flight_event):
        event = make_flight_event(delay_minutes=-5)
        passed, failed = validate_record(event, "flights")
        assert passed is False
        assert "delay_non_negative" in failed

    def test_null_scheduled_time(self, make_flight_event):
        event = make_flight_event(scheduled_time=None)
        passed, failed = validate_record(event, "flights")
        assert passed is False
        assert "scheduled_time_not_null" in failed

    def test_valid_passenger(self, make_passenger_event):
        event = make_passenger_event()
        passed, failed = validate_record(event, "passengers")
        assert passed is True
        assert failed == []

    def test_invalid_wait_time(self, make_passenger_event):
        event = make_passenger_event(wait_time_minutes=-1)
        passed, failed = validate_record(event, "passengers")
        assert passed is False
        assert "wait_time_range" in failed

    def test_null_checkpoint(self, make_passenger_event):
        event = make_passenger_event(checkpoint=None)
        passed, failed = validate_record(event, "passengers")
        assert passed is False
        assert "checkpoint_not_null" in failed

    def test_valid_cargo(self, make_cargo_event):
        event = make_cargo_event()
        passed, failed = validate_record(event, "cargo")
        assert passed is True

    def test_invalid_cargo_weight(self, make_cargo_event):
        event = make_cargo_event(weight_kg=600)
        passed, failed = validate_record(event, "cargo")
        assert passed is False
        assert "weight_range" in failed

    def test_valid_environmental(self, make_environmental_event):
        event = make_environmental_event()
        passed, failed = validate_record(event, "environmental")
        assert passed is True

    def test_invalid_temperature(self, make_environmental_event):
        event = make_environmental_event(temperature_c=60)
        passed, failed = validate_record(event, "environmental")
        assert passed is False
        assert "temperature_range" in failed

    def test_valid_runway(self, make_runway_event):
        event = make_runway_event()
        passed, failed = validate_record(event, "runway")
        assert passed is True

    def test_invalid_wind_speed(self, make_runway_event):
        event = make_runway_event(wind_speed_kph=250)
        passed, failed = validate_record(event, "runway")
        assert passed is False
        assert "wind_speed_range" in failed

    def test_valid_security(self, make_security_event):
        event = make_security_event()
        passed, failed = validate_record(event, "security")
        assert passed is True

    def test_invalid_alert_type(self, make_security_event):
        event = make_security_event(alert_type="unknown")
        passed, failed = validate_record(event, "security")
        assert passed is False
        assert "alert_type_enum" in failed

    def test_unknown_stream_returns_pass(self, make_flight_event):
        event = make_flight_event()
        passed, failed = validate_record(event, "nonexistent_stream")
        assert passed is True
        assert failed == []

    def test_multiple_failures(self, make_flight_event):
        event = make_flight_event(
            flight_id="bad!", status="nope", delay_minutes=-1, scheduled_time=None
        )
        passed, failed = validate_record(event, "flights")
        assert passed is False
        assert len(failed) == 4


# ---------------------------------------------------------------------------
# QUALITY_RULES constant structure
# ---------------------------------------------------------------------------

class TestQualityRulesConfig:
    """Ensure the QUALITY_RULES config has expected structure."""

    EXPECTED_STREAMS = ["flights", "passengers", "cargo", "environmental", "runway", "security"]

    def test_all_streams_present(self):
        for stream in self.EXPECTED_STREAMS:
            assert stream in QUALITY_RULES, f"Missing stream: {stream}"

    def test_rules_have_required_keys(self):
        for stream, rules in QUALITY_RULES.items():
            for rule in rules:
                assert "rule" in rule, f"Missing 'rule' key in {stream}"
                assert "field" in rule, f"Missing 'field' key in {stream}"
                assert "type" in rule, f"Missing 'type' key in {stream}"

    def test_rule_types_are_valid(self):
        valid_types = {"range", "enum", "regex", "not_null"}
        for stream, rules in QUALITY_RULES.items():
            for rule in rules:
                assert rule["type"] in valid_types, (
                    f"Invalid rule type '{rule['type']}' in {stream}/{rule['rule']}"
                )
