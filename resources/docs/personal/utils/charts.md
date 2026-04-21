# charts.py

> File: `utils/charts.py`

## Overview

Reusable Plotly chart builders that enforce consistent styling across all dashboard visualizations. Each function takes a DataFrame and returns a configured `go.Figure` ready for `st.plotly_chart()`.

## Data Dependencies

None — receives DataFrames as parameters, returns Plotly figures. Imports `COLORS` from `theme.py` for consistent styling.

## Key Functions

### `gauge_chart(value, title, max_val=100, thresholds=None) → go.Figure`
Gauge/indicator chart with green/yellow/red zones.
- **Default thresholds:** Green ≥good, Yellow ≥warning, Red below
- **Used by:** Passenger Analytics (OTP), KPI Metrics (quality gauges, compliance)

### `time_series_chart(df, x_col, y_col, title, color=None) → go.Figure`
Line chart with markers and grid.
- **Used by:** Passenger Analytics (OTP trend, throughput), Pipeline Health (throughput)

### `bar_chart(df, x_col, y_col, title, color=None, horizontal=False) → go.Figure`
Vertical or horizontal bar chart.
- **Used by:** KPI Metrics (validation rates, quarantine counts), Passenger Analytics (checkpoints)

### `stacked_bar_chart(df, x_col, y_cols, title, colors=None) → go.Figure`
Multi-series stacked bar chart with `barmode="stack"`.
- **Used by:** Pipeline Health (success/failure trend)

### `heatmap_chart(df, x_col, y_col, z_col, title) → go.Figure`
Pivot table heatmap with green→yellow→red colorscale.
- **Used by:** Available for cross-stream analysis

### `funnel_chart(labels, values, title) → go.Figure`
Funnel for stage-based processing.
- **Used by:** Passenger Analytics (baggage funnel)

### `sankey_chart(sources, targets, values, labels, title) → go.Figure`
Flow diagram for data lineage visualization.
- **Used by:** Data Lineage (B→S→G flow)

### `gantt_chart(df, start_col, end_col, label_col, title) → go.Figure`
Timeline chart for pipeline run visualization.
- **Used by:** Pipeline Health (run timeline)

### `_apply_layout(fig, title) → go.Figure`
Internal — applies consistent layout defaults:
```python
font: system-ui | bg: white | title: navy 16px | margin: 40px
```

## Layout Defaults
All charts use white background, navy titles, system-ui font family, and 40px margins. Pages that need transparent backgrounds override with `fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")`.

## Interview Questions

1. **Q: Why build chart wrappers instead of using Plotly Express directly?**
   A: Consistency — every chart gets the same font, colors, margins, and grid style. Without wrappers, each page would repeat layout code and risk visual inconsistency. Also simplifies the page code to one-liners.

2. **Q: How do you handle responsive sizing?**
   A: Charts use `use_container_width=True` in Streamlit, which makes them responsive to the page width. Height is set per chart based on content density. The margin defaults ensure labels aren't clipped.
