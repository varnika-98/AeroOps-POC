"""AeroOps AI — Airport IoT event generator for 6 data streams.

Generates realistic 24-hour simulated data for flights, passengers, cargo,
environmental sensors, runway conditions, and security events.
"""

import json
import math
import os
import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

from simulator.config import (
    AIRCRAFT_CAPACITY,
    AIRPORT_CONFIG,
    ALERT_TYPES,
    CARGO_ITEM_TYPES,
    CARGO_STATUSES,
    CHECKPOINTS,
    DEVICE_TYPES,
    FLIGHT_STATUSES,
    GATES,
    HVAC_STATUSES,
    PRECIPITATION_TYPES,
    RESOLUTION_STATUSES,
    RUNWAY_STATUSES,
    SCAN_POINTS,
    SEVERITY_LEVELS,
    STREAM_NAMES,
    ZONES,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bronze")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_peak(hour: int) -> bool:
    """Return True if the given hour falls within a peak window."""
    return any(start <= hour < end for start, end in AIRPORT_CONFIG["peak_hours"])


def _peak_multiplier(hour: int) -> float:
    """Return an event-rate multiplier (2–3× during peaks, 1× otherwise)."""
    if _is_peak(hour):
        return random.uniform(2.0, 3.0)
    return 1.0


def _make_event_id(prefix: str, ts: datetime, seq: int) -> str:
    return f"{prefix}-{ts.strftime('%Y%m%d')}-{seq:06d}"


def _iso(ts: datetime) -> str:
    return ts.isoformat()


def _diurnal_temperature(hour: int, base: float = 22.0, amplitude: float = 5.0) -> float:
    """Realistic indoor temperature with diurnal drift (peaks ~14:00)."""
    return round(base + amplitude * math.sin(math.pi * (hour - 6) / 12), 1)


# ---------------------------------------------------------------------------
# Stream generators — each yields events for one simulated minute
# ---------------------------------------------------------------------------

def generate_flight_events(
    ts: datetime, count: int, seq_start: int
) -> list[dict]:
    """Generate *count* flight events around timestamp *ts*."""
    events = []
    for i in range(count):
        airline = random.choice(AIRPORT_CONFIG["airlines"])
        flight_num = f"{airline}{random.randint(100, 9999)}"
        terminal = random.choice(AIRPORT_CONFIG["terminals"])
        gate = random.choice(
            [g for g in GATES if g.startswith(f"Gate-{terminal[-1]}")]
        )
        aircraft = random.choice(AIRPORT_CONFIG["aircraft_types"])
        capacity = AIRCRAFT_CAPACITY[aircraft]
        pax = random.randint(int(capacity * 0.55), capacity)

        # Delay follows exponential distribution; 70 % on-time
        if random.random() < 0.70:
            delay = 0
            status = random.choice(["scheduled", "boarding", "departed", "arrived"])
        else:
            delay = int(random.expovariate(1 / 25))  # mean ≈ 25 min
            delay = min(delay, 300)
            status = "delayed" if delay > 0 else "scheduled"
            if random.random() < 0.03:
                status = "cancelled"

        scheduled = ts + timedelta(minutes=random.randint(0, 59))
        actual = scheduled + timedelta(minutes=delay) if delay else scheduled

        events.append(
            {
                "event_id": _make_event_id("FLT", ts, seq_start + i),
                "timestamp": _iso(ts + timedelta(seconds=random.randint(0, 59))),
                "flight_id": flight_num,
                "gate": gate,
                "terminal": terminal,
                "status": status,
                "scheduled_time": _iso(scheduled),
                "actual_time": _iso(actual) if status != "cancelled" else None,
                "delay_minutes": delay,
                "aircraft_type": aircraft,
                "passenger_count": pax,
            }
        )
    return events


def generate_passenger_events(
    ts: datetime, count: int, seq_start: int
) -> list[dict]:
    events = []
    for i in range(count):
        terminal = random.choice(AIRPORT_CONFIG["terminals"])
        checkpoint = random.choice(CHECKPOINTS)
        zone = random.choice(ZONES)
        pax = random.randint(5, 120)
        wait = round(random.uniform(1.0, 45.0), 1)
        throughput = random.randint(60, 350)
        queue = random.randint(0, 80)

        events.append(
            {
                "event_id": _make_event_id("PAX", ts, seq_start + i),
                "timestamp": _iso(ts + timedelta(seconds=random.randint(0, 59))),
                "terminal": terminal,
                "checkpoint": checkpoint,
                "zone": zone,
                "passenger_count": pax,
                "wait_time_minutes": wait,
                "throughput_per_hour": throughput,
                "queue_length": queue,
            }
        )
    return events


def generate_cargo_events(
    ts: datetime, count: int, seq_start: int
) -> list[dict]:
    events = []
    for i in range(count):
        airline = random.choice(AIRPORT_CONFIG["airlines"])
        flight_id = f"{airline}{random.randint(100, 9999)}"
        item_type = random.choice(CARGO_ITEM_TYPES)
        item_id = f"BAG-{random.randint(1000000, 9999999)}"
        weight = round(random.uniform(1.0, 150.0), 2)
        proc_time = random.randint(5, 600)

        status_weights = [0.20, 0.30, 0.25, 0.20, 0.05]
        status = random.choices(CARGO_STATUSES, weights=status_weights, k=1)[0]

        events.append(
            {
                "event_id": _make_event_id("CGO", ts, seq_start + i),
                "timestamp": _iso(ts + timedelta(seconds=random.randint(0, 59))),
                "item_type": item_type,
                "item_id": item_id,
                "flight_id": flight_id,
                "scan_point": random.choice(SCAN_POINTS),
                "status": status,
                "weight_kg": weight,
                "processing_time_sec": proc_time,
            }
        )
    return events


def generate_environmental_events(
    ts: datetime, count: int, seq_start: int
) -> list[dict]:
    hour = ts.hour
    events = []
    for i in range(count):
        terminal = random.choice(AIRPORT_CONFIG["terminals"])
        zone = random.choice(ZONES)
        temp = _diurnal_temperature(hour) + round(random.gauss(0, 0.5), 1)
        humidity = round(random.uniform(30.0, 70.0), 1)
        co2 = random.randint(400, 800)
        aqi = random.randint(20, 80)

        # Small chance of degraded/offline HVAC
        hvac_weights = [0.90, 0.08, 0.02]
        hvac = random.choices(HVAC_STATUSES, weights=hvac_weights, k=1)[0]

        # If HVAC is degraded, readings drift
        if hvac == "degraded":
            temp += random.uniform(1.0, 3.0)
            co2 += random.randint(50, 200)
        elif hvac == "offline":
            temp += random.uniform(3.0, 7.0)
            co2 += random.randint(200, 500)

        events.append(
            {
                "event_id": _make_event_id("ENV", ts, seq_start + i),
                "timestamp": _iso(ts + timedelta(seconds=random.randint(0, 59))),
                "terminal": terminal,
                "zone": zone,
                "temperature_c": round(temp, 1),
                "humidity_pct": humidity,
                "co2_ppm": co2,
                "air_quality_index": aqi,
                "hvac_status": hvac,
            }
        )
    return events


def generate_runway_events(
    ts: datetime, count: int, seq_start: int
) -> list[dict]:
    events = []
    for i in range(count):
        runway = random.choice(AIRPORT_CONFIG["runways"])
        surface_temp = round(random.uniform(5.0, 55.0), 1)
        wind_speed = round(random.uniform(0.0, 80.0), 1)
        wind_dir = random.randint(0, 360)
        visibility = random.randint(5000, 15000)
        friction = round(random.uniform(0.5, 0.9), 2)
        precip = random.choices(
            PRECIPITATION_TYPES, weights=[0.70, 0.15, 0.10, 0.05], k=1
        )[0]

        # Weather-hold if visibility low or wind extreme
        if visibility < 6000 or wind_speed > 65:
            status = "weather_hold"
        elif random.random() < 0.05:
            status = "maintenance"
        else:
            status = "active"

        events.append(
            {
                "event_id": _make_event_id("RWY", ts, seq_start + i),
                "timestamp": _iso(ts + timedelta(seconds=random.randint(0, 59))),
                "runway_id": runway,
                "surface_temp_c": surface_temp,
                "wind_speed_kph": wind_speed,
                "wind_direction_deg": wind_dir,
                "visibility_m": visibility,
                "friction_index": friction,
                "precipitation": precip,
                "runway_status": status,
            }
        )
    return events


def generate_security_events(
    ts: datetime, count: int, seq_start: int
) -> list[dict]:
    events = []
    for i in range(count):
        checkpoint = random.choice(AIRPORT_CONFIG["security_checkpoints"])
        zone = random.choice(ZONES)
        device = random.choice(DEVICE_TYPES)

        # 95 % routine scans
        alert_weights = [0.95, 0.03, 0.005, 0.015]
        alert_type = random.choices(ALERT_TYPES, weights=alert_weights, k=1)[0]

        if alert_type == "routine_scan":
            severity = "low"
            response_time = None
            resolution = "auto_cleared"
        elif alert_type == "anomaly":
            severity = random.choice(["medium", "high"])
            response_time = random.randint(10, 120)
            resolution = random.choice(["manual_review", "auto_cleared"])
        elif alert_type == "breach":
            severity = "critical"
            response_time = random.randint(5, 30)
            resolution = "escalated"
        else:  # device_alert
            severity = random.choice(["low", "medium"])
            response_time = random.randint(15, 90)
            resolution = random.choice(["auto_cleared", "manual_review"])

        events.append(
            {
                "event_id": _make_event_id("SEC", ts, seq_start + i),
                "timestamp": _iso(ts + timedelta(seconds=random.randint(0, 59))),
                "checkpoint_id": checkpoint,
                "alert_type": alert_type,
                "severity": severity,
                "device_type": device,
                "response_time_sec": response_time,
                "resolution_status": resolution,
                "zone": zone,
            }
        )
    return events


# ---------------------------------------------------------------------------
# Stream function registry
# ---------------------------------------------------------------------------

STREAM_GENERATORS = {
    "flights": generate_flight_events,
    "passengers": generate_passenger_events,
    "cargo": generate_cargo_events,
    "environmental": generate_environmental_events,
    "runway": generate_runway_events,
    "security": generate_security_events,
}


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def generate_all_events(
    base_date: datetime | None = None,
    hours: int = 24,
    rate_multiplier: float = 1.0,
) -> dict[str, list[dict]]:
    """Generate simulated IoT events for all streams.

    Args:
        base_date: Starting datetime (default: today at midnight).
        hours: Number of hours to simulate.
        rate_multiplier: Global event-rate multiplier (used by failure injector).

    Returns:
        Dict mapping stream name → list of event dicts.
    """
    if base_date is None:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    all_events: dict[str, list[dict]] = {s: [] for s in STREAM_NAMES}
    epm = AIRPORT_CONFIG["events_per_minute"]

    for minute_offset in range(hours * 60):
        ts = base_date + timedelta(minutes=minute_offset)
        hour = ts.hour
        peak_mult = _peak_multiplier(hour)

        for stream in STREAM_NAMES:
            base_count = epm[stream]
            count = max(1, int(base_count * peak_mult * rate_multiplier))
            seq_start = len(all_events[stream])
            gen_fn = STREAM_GENERATORS[stream]
            all_events[stream].extend(gen_fn(ts, count, seq_start))

    return all_events


def write_events_to_json(
    all_events: dict[str, list[dict]],
    output_dir: str | None = None,
) -> dict[str, str]:
    """Write each stream's events to a JSON file under data/bronze/{stream}/.

    Returns:
        Dict mapping stream name → file path written.
    """
    if output_dir is None:
        output_dir = DATA_DIR

    paths: dict[str, str] = {}
    for stream, events in all_events.items():
        stream_dir = os.path.join(output_dir, stream)
        os.makedirs(stream_dir, exist_ok=True)
        file_path = os.path.join(stream_dir, f"{stream}_events.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, default=str)
        paths[stream] = file_path
        print(f"  [OK] {stream}: {len(events):,} events -> {file_path}")

    return paths


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("AeroOps AI - Airport IoT Data Simulator")
    print("=" * 60)
    print()

    events = generate_all_events()

    total = sum(len(v) for v in events.values())
    print(f"Generated {total:,} total events across {len(events)} streams.\n")
    print("Writing to data/bronze/ ...")

    write_events_to_json(events)

    print("\nDone!")
