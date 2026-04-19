"""Airport-themed Streamlit styling for AeroOps AI dashboard."""

# Color scheme
COLORS = {
    "navy": "#1B2A4A",
    "sky_blue": "#4A90D9",
    "safety_orange": "#FF6B35",
    "success_green": "#2ECC71",
    "warning_yellow": "#F1C40F",
    "danger_red": "#E74C3C",
    "light_gray": "#ECF0F1",
    "dark_gray": "#2C3E50",
    "white": "#FFFFFF",
}

# Status colors for traffic light indicators
STATUS_COLORS = {
    "healthy": COLORS["success_green"],
    "warning": COLORS["warning_yellow"],
    "critical": COLORS["danger_red"],
}

# Stream icons
STREAM_ICONS = {
    "flights": "✈️",
    "passengers": "👥",
    "cargo": "📦",
    "environmental": "🌡️",
    "runway": "🛬",
    "security": "🔒",
}


def apply_theme(st) -> None:
    """Apply custom CSS theme to a Streamlit app."""
    st.markdown(
        f"""
        <style>
            /* Main background */
            .stApp {{
                background-color: {COLORS["light_gray"]};
            }}
            /* Sidebar */
            [data-testid="stSidebar"] {{
                background-color: {COLORS["navy"]};
                color: {COLORS["white"]};
            }}
            [data-testid="stSidebar"] .stMarkdown {{
                color: {COLORS["white"]};
            }}
            /* Headers */
            h1, h2, h3 {{
                color: {COLORS["navy"]};
            }}
            /* Metric cards */
            .metric-card {{
                background: {COLORS["white"]};
                border-radius: 10px;
                padding: 1.2rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                text-align: center;
                border-left: 5px solid {COLORS["sky_blue"]};
            }}
            .metric-card .metric-value {{
                font-size: 2rem;
                font-weight: 700;
                color: {COLORS["navy"]};
            }}
            .metric-card .metric-label {{
                font-size: 0.85rem;
                color: {COLORS["dark_gray"]};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .metric-card .metric-delta {{
                font-size: 0.8rem;
                margin-top: 0.3rem;
            }}
            .metric-card.healthy {{ border-left-color: {COLORS["success_green"]}; }}
            .metric-card.warning {{ border-left-color: {COLORS["warning_yellow"]}; }}
            .metric-card.critical {{ border-left-color: {COLORS["danger_red"]}; }}
            /* Page header */
            .page-header {{
                background: linear-gradient(135deg, {COLORS["navy"]}, {COLORS["sky_blue"]});
                color: {COLORS["white"]};
                padding: 1.5rem 2rem;
                border-radius: 10px;
                margin-bottom: 1.5rem;
            }}
            .page-header h1 {{
                color: {COLORS["white"]};
                margin: 0;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value, delta=None, status: str = "healthy") -> str:
    """Return HTML for a styled metric card.

    Args:
        label: Display label for the metric.
        value: Current metric value.
        delta: Optional delta string (e.g. "+2.3%").
        status: One of "healthy", "warning", "critical".
    """
    color = STATUS_COLORS.get(status, COLORS["sky_blue"])
    delta_html = ""
    if delta is not None:
        delta_color = COLORS["success_green"] if str(delta).startswith("+") else COLORS["danger_red"]
        delta_html = f'<div class="metric-delta" style="color:{delta_color}">{delta}</div>'

    return f"""
    <div class="metric-card {status}" style="border-left-color:{color}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """


def status_indicator(status: str) -> str:
    """Return a colored circle emoji based on status string.

    Args:
        status: One of "healthy", "warning", "critical", or any other string.
    """
    mapping = {
        "healthy": "🟢",
        "warning": "🟡",
        "critical": "🔴",
        "no_data": "⚪",
    }
    return mapping.get(status.lower(), "⚪")


def page_header(title: str, icon: str = "✈️") -> str:
    """Return HTML for a standard page header with icon.

    Args:
        title: Page title text.
        icon: Emoji or icon string to display.
    """
    return f"""
    <div class="page-header">
        <h1>{icon} {title}</h1>
    </div>
    """
