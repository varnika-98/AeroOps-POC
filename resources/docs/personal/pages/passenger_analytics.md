# Passenger Analytics

> File: `app/pages/1_Passenger_Analytics.py`

## Overview

Passenger Analytics provides flight operations and passenger flow intelligence — on-time performance, delay patterns, checkpoint throughput, and baggage processing. It's the operational intelligence layer that airport managers use to identify bottlenecks and optimize passenger experience.

**Supporting files:** `utils/kpi_calculator.py` (`get_flight_kpis`, `get_passenger_kpis`), `utils/charts.py` (gauge, time_series, bar, funnel), `utils/theme.py`

## Metrics

### KPI Cards

| Metric | Calculation | Thresholds | Data Source |
|--------|-------------|------------|-------------|
| **Flight OTP %** | `flight_kpi.get("otp_pct")` | 🟢 ≥80% · 🟡 ≥60% · 🔴 <60% | `gold/flight_kpis.parquet` |
| **Total Flights** | `flight_kpi.get("total_flights")` | Neutral | `gold/flight_kpis.parquet` |
| **Avg Delay (min)** | `flight_kpi.get("avg_delay_min")` | 🟢 ≤10 · 🟡 ≤20 · 🔴 >20 | `gold/flight_kpis.parquet` |
| **Passenger Throughput** | `passenger_kpi.get("throughput_per_hour")` | Neutral | `gold/passenger_kpis.parquet` |

### Charts

| Chart | Type | Key Details |
|-------|------|-------------|
| **OTP Gauge** | Gauge | 0-100%, threshold line at 80%, color zones green/yellow/red |
| **OTP Trend** | Line | Hourly OTP% with dashed 80% target line |
| **Delay Distribution** | Histogram | 40 bins of delay_minutes from `silver/flights.parquet` |
| **Flight Status** | Lollipop | Count per status (on_time, delayed, cancelled, etc.) |
| **Checkpoint Wait Times** | Bar | Avg wait_time_minutes per checkpoint |
| **Throughput vs Capacity** | Line | Hourly throughput with 300 pax/hr capacity target line |
| **Baggage Funnel** | Funnel | Stages: checked_in → in_transit → loaded → delivered |

### Color Mappings
- **OTP Gauge zones:** Green (≥80%), Yellow (60-79%), Red (<60%)
- **Delay markers:** Multi-color per flight status
- **Funnel gradient:** Teal shades (#0D3B66 → #28B5C4)
- **Capacity target:** Dashed red line at 300 pax/hr

## Purpose & Inference

| Metric | Purpose | What to Infer |
|--------|---------|---------------|
| Flight OTP % | Core airline performance indicator | <80% triggers regulatory attention; check delay distribution for root cause |
| Avg Delay | Passenger impact quantification | High delay with normal OTP means few flights are extremely delayed (outliers) |
| Delay Distribution | Pattern identification | Bimodal distribution suggests two distinct delay causes (weather vs operational) |
| Checkpoint Wait Times | Bottleneck identification | Uneven distribution across checkpoints suggests staffing or equipment issues |
| Throughput vs Capacity | Capacity planning | Consistently near/above 300 pax/hr means infrastructure expansion needed |
| Baggage Funnel | Process efficiency tracking | Sharp drop between stages indicates a processing bottleneck at that stage |
| Flight Status Breakdown | Operational health snapshot | High cancellation rate may correlate with runway/weather issues |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/gold/flight_kpis.parquet` | Gold | `get_flight_kpis()` | OTP%, avg delay, total flights, gate utilization |
| `data/gold/passenger_kpis.parquet` | Gold | `get_passenger_kpis()` | Throughput/hr, avg wait time, totals |
| `data/silver/flights.parquet` | Silver | Direct read | Raw flight records: delay_minutes, status, timestamps |
| `data/silver/passengers.parquet` | Silver | Direct read | Checkpoint, wait_time_minutes, timestamps |
| `data/silver/cargo.parquet` | Silver | Direct read | Cargo status (checked_in, in_transit, loaded, delivered) |

**Write operations:** None (read-only page)

## Interview Pitch

*"Passenger Analytics combines flight operations and terminal efficiency into one view. The OTP gauge and trend give us real-time and historical performance. What's interesting is the checkpoint throughput vs capacity chart — it reveals terminal bottlenecks before they cause delays. The baggage funnel tracks every cargo stage, so if bags are stuck 'in_transit', we know exactly where to look. All data flows from our simulated IoT sensors through the medallion pipeline."*

## Interview Questions

1. **Q: How is On-Time Performance calculated?**
   A: A flight is "on-time" if `delay_minutes ≤ 15` (industry standard). OTP% = (on-time flights / total flights) × 100. We compute this hourly in the Gold layer via DuckDB aggregation, enabling trend analysis.

2. **Q: What does the baggage funnel tell you that a simple count wouldn't?**
   A: The funnel shows conversion rates between stages. If 1000 bags are checked_in but only 800 are loaded, there's a 20% drop — that's actionable. A simple total count hides where the process breaks down.

3. **Q: How would you detect if a checkpoint scanner goes offline?**
   A: The Passenger Sensor Outage failure scenario simulates exactly this — it nullifies checkpoint names and sets wait_time to -1. Quality rules catch the not_null and range violations, quarantine the records, and the dashboard shows the affected checkpoint's throughput drop to zero.

4. **Q: Why use a gauge chart for OTP instead of just a number?**
   A: The gauge provides instant visual context — green/yellow/red zones communicate health status faster than reading "78.4%". Combined with the trend line showing trajectory, it answers both "where are we?" and "where are we heading?"
