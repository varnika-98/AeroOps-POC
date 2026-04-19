"""Reusable Plotly chart builders for AeroOps AI dashboard."""

import plotly.express as px
import plotly.graph_objects as go

from utils.theme import COLORS

# Consistent layout defaults
_LAYOUT_DEFAULTS = dict(
    font_family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    plot_bgcolor=COLORS["white"],
    paper_bgcolor=COLORS["white"],
    title_font_size=16,
    title_font_color=COLORS["navy"],
    margin=dict(l=40, r=40, t=50, b=40),
)


def _apply_layout(fig: go.Figure, title: str) -> go.Figure:
    """Apply consistent styling to a figure."""
    fig.update_layout(title=title, **_LAYOUT_DEFAULTS)
    return fig


def gauge_chart(
    value: float,
    title: str,
    max_val: float = 100,
    thresholds: dict | None = None,
) -> go.Figure:
    """Plotly gauge/indicator chart.

    Args:
        value: Current value to display.
        title: Chart title.
        max_val: Maximum value on the gauge.
        thresholds: Optional dict with "warning" and "critical" cutoff values.
    """
    if thresholds is None:
        thresholds = {"warning": max_val * 0.7, "critical": max_val * 0.4}

    steps = [
        {"range": [0, thresholds["critical"]], "color": COLORS["danger_red"]},
        {"range": [thresholds["critical"], thresholds["warning"]], "color": COLORS["warning_yellow"]},
        {"range": [thresholds["warning"], max_val], "color": COLORS["success_green"]},
    ]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title, "font": {"size": 16, "color": COLORS["navy"]}},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar": {"color": COLORS["navy"]},
                "steps": steps,
                "threshold": {
                    "line": {"color": COLORS["dark_gray"], "width": 2},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor=COLORS["white"],
        font_family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        margin=dict(l=30, r=30, t=60, b=30),
        height=250,
    )
    return fig


def time_series_chart(df, x_col: str, y_col: str, title: str, color: str | None = None) -> go.Figure:
    """Line chart with styled layout."""
    line_color = color or COLORS["sky_blue"]
    fig = go.Figure(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="lines+markers",
            line=dict(color=line_color, width=2),
            marker=dict(size=4),
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["light_gray"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["light_gray"])
    return _apply_layout(fig, title)


def bar_chart(
    df, x_col: str, y_col: str, title: str, color: str | None = None, horizontal: bool = False,
) -> go.Figure:
    """Bar chart."""
    bar_color = color or COLORS["sky_blue"]
    if horizontal:
        fig = go.Figure(go.Bar(x=df[y_col], y=df[x_col], orientation="h", marker_color=bar_color))
    else:
        fig = go.Figure(go.Bar(x=df[x_col], y=df[y_col], marker_color=bar_color))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["light_gray"])
    return _apply_layout(fig, title)


def stacked_bar_chart(
    df, x_col: str, y_cols: list[str], title: str, colors: list[str] | None = None,
) -> go.Figure:
    """Stacked bar chart."""
    palette = colors or [
        COLORS["sky_blue"], COLORS["success_green"], COLORS["safety_orange"],
        COLORS["warning_yellow"], COLORS["danger_red"], COLORS["navy"],
    ]
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            x=df[x_col], y=df[col], name=col,
            marker_color=palette[i % len(palette)],
        ))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["light_gray"])
    return _apply_layout(fig, title)


def heatmap_chart(df, x_col: str, y_col: str, z_col: str, title: str) -> go.Figure:
    """Heatmap chart."""
    pivot = df.pivot_table(index=y_col, columns=x_col, values=z_col, aggfunc="mean")
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[
                [0, COLORS["success_green"]],
                [0.5, COLORS["warning_yellow"]],
                [1, COLORS["danger_red"]],
            ],
        )
    )
    return _apply_layout(fig, title)


def funnel_chart(labels: list[str], values: list[float], title: str) -> go.Figure:
    """Funnel chart (e.g. for baggage processing stages)."""
    fig = go.Figure(
        go.Funnel(
            y=labels,
            x=values,
            marker=dict(
                color=[
                    COLORS["sky_blue"], COLORS["navy"], COLORS["success_green"],
                    COLORS["safety_orange"], COLORS["warning_yellow"], COLORS["danger_red"],
                ][:len(labels)]
            ),
        )
    )
    return _apply_layout(fig, title)


def sankey_chart(
    sources: list[int],
    targets: list[int],
    values: list[float],
    labels: list[str],
    title: str,
) -> go.Figure:
    """Sankey diagram (e.g. for data lineage B→S→G flow)."""
    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=20,
                thickness=20,
                label=labels,
                color=[COLORS["sky_blue"]] * len(labels),
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=[COLORS["light_gray"]] * len(sources),
            ),
        )
    )
    return _apply_layout(fig, title)


def gantt_chart(df, start_col: str, end_col: str, label_col: str, title: str) -> go.Figure:
    """Gantt/timeline chart for pipeline runs or scheduled operations."""
    fig = go.Figure()
    palette = [
        COLORS["sky_blue"], COLORS["success_green"], COLORS["safety_orange"],
        COLORS["navy"], COLORS["warning_yellow"], COLORS["danger_red"],
    ]
    for i, (_, row) in enumerate(df.iterrows()):
        fig.add_trace(go.Bar(
            x=[row[end_col] - row[start_col]] if hasattr(row[end_col], '__sub__') else [1],
            y=[row[label_col]],
            base=[row[start_col]],
            orientation="h",
            marker_color=palette[i % len(palette)],
            name=str(row[label_col]),
            showlegend=False,
        ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["light_gray"])
    return _apply_layout(fig, title)
