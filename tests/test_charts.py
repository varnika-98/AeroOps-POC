"""Tests for utils.charts — Plotly chart builders."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from utils.charts import (
    bar_chart,
    funnel_chart,
    gauge_chart,
    heatmap_chart,
    sankey_chart,
    stacked_bar_chart,
    time_series_chart,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "x": ["A", "B", "C"],
        "y": [10, 20, 30],
        "y2": [5, 10, 15],
    })


@pytest.fixture
def heatmap_df():
    return pd.DataFrame({
        "row": ["R1", "R1", "R2", "R2"],
        "col": ["C1", "C2", "C1", "C2"],
        "val": [1.0, 2.0, 3.0, 4.0],
    })


class TestGaugeChart:
    def test_returns_figure(self):
        fig = gauge_chart(75.0, "Test Gauge")
        assert isinstance(fig, go.Figure)

    def test_custom_thresholds(self):
        fig = gauge_chart(50, "Gauge", max_val=100, thresholds={"warning": 80, "critical": 40})
        assert isinstance(fig, go.Figure)

    def test_zero_value(self):
        fig = gauge_chart(0.0, "Zero")
        assert isinstance(fig, go.Figure)


class TestTimeSeriesChart:
    def test_returns_figure(self, sample_df):
        fig = time_series_chart(sample_df, "x", "y", "Time Series")
        assert isinstance(fig, go.Figure)

    def test_custom_color(self, sample_df):
        fig = time_series_chart(sample_df, "x", "y", "TS", color="#ff0000")
        assert isinstance(fig, go.Figure)


class TestBarChart:
    def test_returns_figure(self, sample_df):
        fig = bar_chart(sample_df, "x", "y", "Bar Chart")
        assert isinstance(fig, go.Figure)

    def test_horizontal(self, sample_df):
        fig = bar_chart(sample_df, "x", "y", "Horizontal", horizontal=True)
        assert isinstance(fig, go.Figure)


class TestStackedBarChart:
    def test_returns_figure(self, sample_df):
        fig = stacked_bar_chart(sample_df, "x", ["y", "y2"], "Stacked")
        assert isinstance(fig, go.Figure)

    def test_has_multiple_traces(self, sample_df):
        fig = stacked_bar_chart(sample_df, "x", ["y", "y2"], "Stacked")
        assert len(fig.data) == 2


class TestHeatmapChart:
    def test_returns_figure(self, heatmap_df):
        fig = heatmap_chart(heatmap_df, "col", "row", "val", "Heatmap")
        assert isinstance(fig, go.Figure)


class TestFunnelChart:
    def test_returns_figure(self):
        fig = funnel_chart(["Step 1", "Step 2", "Step 3"], [100, 60, 30], "Funnel")
        assert isinstance(fig, go.Figure)


class TestSankeyChart:
    def test_returns_figure(self):
        fig = sankey_chart(
            sources=[0, 1], targets=[2, 3],
            values=[10, 20], labels=["A", "B", "C", "D"],
            title="Sankey",
        )
        assert isinstance(fig, go.Figure)
