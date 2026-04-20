"""AeroOps AI — Failure injection for testing data quality pipelines.

Provides three injectable failure scenarios that modify generated events
or generation configuration to simulate real-world data issues.
"""

import random

random.seed(42)


def inject_schema_drift(
    events: dict[str, list[dict]],
    stream: str = "runway",
) -> dict[str, list[dict]]:
    """Simulate schema drift by converting wind_speed values from mph → kph.

    Multiplies wind_speed_kph by 4.0, making many values exceed the
    expected 0–200 kph validation range.

    Args:
        events: All-stream event dict from generate_all_events().
        stream: Target stream (default: "runway").

    Returns:
        Modified events dict (mutated in-place and returned).
    """
    if stream not in events:
        raise ValueError(f"Stream '{stream}' not found in events")

    affected = 0
    for event in events[stream]:
        if "wind_speed_kph" in event:
            event["wind_speed_kph"] = round(event["wind_speed_kph"] * 4.0, 1)
            affected += 1

    print(f"  [!] Schema drift injected: {affected:,} runway events "
          f"-- wind_speed_kph multiplied by 4.0")
    return events


def inject_sensor_outage(
    events: dict[str, list[dict]],
    stream: str = "passengers",
    checkpoints: int = 3,
) -> dict[str, list[dict]]:
    """Simulate sensor outage by corrupting events from random checkpoints.

    Sets wait_time_minutes to -1 (invalid) and nullifies checkpoint field
    for events from affected checkpoints, triggering validation failures.

    Args:
        events: All-stream event dict from generate_all_events().
        stream: Target stream (default: "passengers").
        checkpoints: Number of checkpoints to knock offline.

    Returns:
        Modified events dict (mutated in-place and returned).
    """
    if stream not in events:
        raise ValueError(f"Stream '{stream}' not found in events")

    all_checkpoints = list(
        {e.get("checkpoint") for e in events[stream] if e.get("checkpoint")}
    )
    if not all_checkpoints:
        print("  [!] No checkpoints found in stream -- skipping outage injection.")
        return events

    offline = random.sample(all_checkpoints, min(checkpoints, len(all_checkpoints)))
    corrupted = 0
    for e in events[stream]:
        if e.get("checkpoint") in offline:
            e["wait_time_minutes"] = -1
            e["checkpoint"] = None
            corrupted += 1

    print(f"  [!] Sensor outage injected: corrupted {corrupted:,} events from "
          f"checkpoints {offline}")
    return events


def inject_traffic_spike(
    multiplier: float = 3.0,
) -> float:
    """Return a rate multiplier to simulate a traffic spike.

    Pass the returned value as `rate_multiplier` to
    `generate_all_events()` to produce 3× normal event volume.

    Args:
        multiplier: Factor by which to increase event generation rates.

    Returns:
        The multiplier value (for use with generate_all_events).
    """
    print(f"  [!] Traffic spike configured: {multiplier}x event generation rate")
    return multiplier
