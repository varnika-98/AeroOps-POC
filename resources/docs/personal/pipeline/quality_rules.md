# quality_rules.py

> File: `pipeline/quality_rules.py`

## Overview

Declarative data validation ruleset for all 6 IoT streams. Defines field-level constraints (range, enum, regex, not_null) that enforce the schema contract between Bronze (raw) and Silver (trusted) data. The rules are the single source of truth for what constitutes "valid" data in the system.

## ETL Operations

| Operation | Type | Description |
|-----------|------|-------------|
| Record Validation | Transform | Checks each field against its declared rule |
| Failure Tagging | Transform | Returns list of failed rule names for quarantine labeling |

**No I/O** — pure validation logic. Receives a dict, returns pass/fail + reasons.

## Input Data

| Source | Format | Content |
|--------|--------|---------|
| Individual event records | `dict` (in-memory) | One record at a time from `silver_transformation.py` |
| Stream name | `str` | Determines which rule set to apply |

## Output Data

| Return | Format | Content |
|--------|--------|---------|
| `(passed, failed_rules)` | `tuple[bool, list[str]]` | Whether the record passes + list of failed rule names |

**Example output:** `(False, ["wind_speed_range", "friction_range"])`

## Purpose

- **Schema contract** — Defines what valid data looks like per stream
- **Declarative** — Rules are data (dict), not imperative code — easy to extend
- **Diagnostic** — Named rules enable root cause analysis ("which rule fails most?")
- **Decoupled** — Rules are separate from transformation logic (SRP)

## Complete Rule Definitions

### flights (5 rules)
| Rule Name | Field | Type | Criteria |
|-----------|-------|------|----------|
| flight_id_format | flight_id | regex | `^[A-Z0-9]{2}\d{3,4}$` |
| status_enum | status | enum | scheduled, boarding, departed, arrived, delayed, cancelled |
| delay_non_negative | delay_minutes | range | min: 0 |
| passenger_range | passenger_count | range | min: 1, max: 600 |
| scheduled_time_not_null | scheduled_time | not_null | Must exist and be non-empty |

### passengers (4 rules)
| Rule Name | Field | Type | Criteria |
|-----------|-------|------|----------|
| passenger_count_range | passenger_count | range | min: 0, max: 5000 |
| wait_time_range | wait_time_minutes | range | min: 0, max: 180 |
| throughput_non_negative | throughput_per_hour | range | min: 0 |
| checkpoint_not_null | checkpoint | not_null | Must exist and be non-empty |

### cargo (4 rules)
| Rule Name | Field | Type | Criteria |
|-----------|-------|------|----------|
| item_type_enum | item_type | enum | baggage, cargo, mail |
| status_enum | status | enum | checked_in, in_transit, loaded, delivered, lost |
| weight_range | weight_kg | range | min: 0.1, max: 500 |
| processing_time_non_negative | processing_time_sec | range | min: 0 |

### environmental (5 rules)
| Rule Name | Field | Type | Criteria |
|-----------|-------|------|----------|
| temperature_range | temperature_c | range | min: -10, max: 50 |
| humidity_range | humidity_pct | range | min: 0, max: 100 |
| co2_range | co2_ppm | range | min: 200, max: 5000 |
| aqi_range | air_quality_index | range | min: 0, max: 500 |
| hvac_enum | hvac_status | enum | normal, degraded, offline |

### runway (6 rules)
| Rule Name | Field | Type | Criteria |
|-----------|-------|------|----------|
| wind_speed_range | wind_speed_kph | range | min: 0, max: 200 |
| visibility_range | visibility_m | range | min: 0, max: 20000 |
| friction_range | friction_index | range | min: 0, max: 1.0 |
| wind_direction_range | wind_direction_deg | range | min: 0, max: 360 |
| precipitation_enum | precipitation | enum | none, rain, snow, ice |
| runway_status_enum | runway_status | enum | active, maintenance, weather_hold |

### security (4 rules)
| Rule Name | Field | Type | Criteria |
|-----------|-------|------|----------|
| alert_type_enum | alert_type | enum | routine_scan, anomaly, breach, device_alert |
| severity_enum | severity | enum | low, medium, high, critical |
| resolution_enum | resolution_status | enum | auto_cleared, manual_review, escalated |
| response_time_non_negative | response_time_sec | range | min: 0 (allow_null: true) |

## Rule Types

| Type | Logic | Null Handling |
|------|-------|--------------|
| `not_null` | Field must exist and be non-empty string | Fails on None/empty |
| `regex` | `re.match(pattern, str(value))` | Fails on None (unless allow_null) |
| `enum` | `value in allowed` list | Fails on None (unless allow_null) |
| `range` | `float(value)` then check min/max bounds | Fails on None (unless allow_null) |

**`allow_null: true`** — Used for optional fields (e.g., `response_time_sec` in security — null means "no response needed for routine scans").

## How Failure Injection Triggers Rules

| Scenario | Stream | Rules Triggered | Mechanism |
|----------|--------|----------------|-----------|
| Schema Drift | runway | wind_speed_range | Value × 4.0 exceeds max 200 |
| Sensor Outage | passengers | checkpoint_not_null, wait_time_range | Sets null/negative values |
| Traffic Spike | all | (none) | Valid data at higher volume |

## Interview Pitch

"Quality rules implement a declarative validation contract — each stream has a rule set defined as data, not imperative code. The `validate_record` function iterates the rules and returns named failures like `wind_speed_range`. This enables automated root cause analysis: when runway quality drops from 99% to 70%, we query quarantine and immediately see '320 records failed wind_speed_range' — pointing directly to a sensor calibration issue. Adding a new rule is one dict entry, no logic changes needed."

## Interview Q&A

1. **Q: How do you add a new validation rule?**
   A: Add a dict to the stream's list in `QUALITY_RULES`. Example: `{"rule": "airline_code", "field": "airline", "type": "enum", "allowed": ["AA", "UA", "DL"]}`. The system picks it up automatically — no code changes to Silver transformation.

2. **Q: Why are rules declarative (data) instead of code?**
   A: Declarative rules can be serialized (JSON/YAML), versioned, tested in isolation, and potentially edited by non-developers via a UI. They also enable rule metadata (description, severity, owner) without polluting logic.

3. **Q: How does `allow_null` work and when do you use it?**
   A: When `allow_null: true`, a None value passes validation for that rule. Used for optional fields — e.g., security alerts from routine scans have no `response_time_sec` because no response was needed. Without `allow_null`, these valid records would be incorrectly quarantined.

4. **Q: How would you version rules for compliance auditing?**
   A: Move rules to a versioned YAML file. Each pipeline run records which rule version was used in the execution log. This enables re-validation of historical data against old/new rules, and audit trails showing when rules changed and why.
