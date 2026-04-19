"""AeroOps AI — Airport configuration constants and helper lookups."""

AIRPORT_CONFIG = {
    "name": "AeroOps International Airport",
    "code": "AOP",
    "terminals": ["Terminal 1", "Terminal 2", "Terminal 3"],
    "gates_per_terminal": 20,
    "runways": ["09L/27R", "09R/27L", "04/22"],
    "security_checkpoints": ["SEC-T1-A", "SEC-T1-B", "SEC-T2-A", "SEC-T2-B", "SEC-T3-A"],
    "airlines": ["AA", "UA", "DL", "SW", "B6", "AS", "NK", "F9"],
    "aircraft_types": ["B737-800", "A320", "B777-300", "A350-900", "E175", "B787-9"],
    "peak_hours": [(7, 9), (11, 13), (17, 19)],
    "events_per_minute": {
        "flights": 2,
        "passengers": 10,
        "cargo": 5,
        "environmental": 8,
        "runway": 3,
        "security": 6,
    },
}

STREAM_NAMES = list(AIRPORT_CONFIG["events_per_minute"].keys())

# --- Helper lookups ---

GATES = [
    f"Gate-{t[-1]}{g:02d}"
    for t in AIRPORT_CONFIG["terminals"]
    for g in range(1, AIRPORT_CONFIG["gates_per_terminal"] + 1)
]

ZONES = [
    f"{area}-{wing}"
    for area in ["Departures", "Arrivals", "Concourse"]
    for wing in ["North", "South", "East", "West"]
]

CHECKPOINTS = [
    f"Security-{letter}" for letter in "ABCDEFGHIJ"
]

SCAN_POINTS = [f"Conveyor-B{i}" for i in range(1, 16)]

CARGO_ITEM_TYPES = ["baggage", "cargo", "mail"]

FLIGHT_STATUSES = [
    "scheduled", "boarding", "departed", "arrived", "delayed", "cancelled",
]

CARGO_STATUSES = [
    "checked_in", "in_transit", "loaded", "delivered", "lost",
]

HVAC_STATUSES = ["normal", "degraded", "offline"]

PRECIPITATION_TYPES = ["none", "rain", "snow", "ice"]

RUNWAY_STATUSES = ["active", "maintenance", "weather_hold"]

ALERT_TYPES = ["routine_scan", "anomaly", "breach", "device_alert"]

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

DEVICE_TYPES = ["x_ray_scanner", "metal_detector", "cctv"]

RESOLUTION_STATUSES = ["auto_cleared", "manual_review", "escalated"]

# Aircraft type → typical passenger capacity
AIRCRAFT_CAPACITY = {
    "B737-800": 189,
    "A320": 180,
    "B777-300": 396,
    "A350-900": 325,
    "E175": 76,
    "B787-9": 296,
}
