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
                background: linear-gradient(180deg, #4682B4 0%, #2a4d7a 100%);
                color: {COLORS["white"]};
            }}
            [data-testid="stSidebar"] .stMarkdown {{
                color: {COLORS["white"]};
            }}
            /* Sidebar nav page links */
            [data-testid="stSidebarNav"] {{
                background: transparent;
            }}
            /* Logo area at top of sidebar */
            [data-testid="stSidebarHeader"] {{
                background: transparent;
                padding: 1rem 1rem 0.5rem 1rem;
            }}
            [data-testid="stSidebarHeader"] img {{
                max-height: 80px !important;
                height: 80px !important;
                width: auto !important;
            }}
            [data-testid="stSidebarNav"] a,
            [data-testid="stSidebarNav"] a span,
            [data-testid="stSidebarNavLink"],
            [data-testid="stSidebarNavLink"] span {{
                color: {COLORS["white"]} !important;
            }}
            [data-testid="stSidebarNavLink"]:hover {{
                background-color: rgba(255, 255, 255, 0.12) !important;
            }}
            [data-testid="stSidebarNavLink"][aria-selected="true"] {{
                background-color: rgba(255, 255, 255, 0.2) !important;
            }}
            /* All text elements inside sidebar */
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] div {{
                color: {COLORS["white"]};
            }}
            [data-testid="stSidebar"] .stCheckbox span {{
                color: {COLORS["white"]} !important;
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
                background: linear-gradient(135deg, #2a4d7a, #4682B4);
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


def page_loader(duration: float = 0.5) -> str:
    """Return HTML/CSS for a radar-style page loader overlay.

    Uses pure CSS animation to auto-dismiss. Only shows once per browser
    session (uses sessionStorage to track). Covers the entire viewport
    including topbar and sidebar.

    Args:
        duration: Seconds to display the loader before fade-out.
    """
    dur_ms = int(duration * 1000)
    return f"""
<style>
@keyframes radar-ping {{
    0% {{ transform: scale(0.3); opacity: 1; }}
    100% {{ transform: scale(2.5); opacity: 0; }}
}}
@keyframes loader-dismiss {{
    0% {{ opacity: 1; }}
    100% {{ opacity: 0; visibility: hidden; pointer-events: none; }}
}}
#aeroops-loader {{
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: #1a1a2e; z-index: 9999999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    animation: loader-dismiss 0.4s ease {duration}s forwards;
}}
#aeroops-loader.loader-hidden {{ display: none !important; }}
#aeroops-loader .radar-container {{
    position: relative; width: 120px; height: 120px; margin-bottom: 2rem;
}}
#aeroops-loader .radar-ring {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    border: 2px solid #4682B4; border-radius: 50%;
    animation: radar-ping 2s ease-out infinite;
}}
#aeroops-loader .radar-ring:nth-child(2) {{ animation-delay: 0.5s; }}
#aeroops-loader .radar-ring:nth-child(3) {{ animation-delay: 1.0s; }}
#aeroops-loader .radar-dot {{
    position: absolute; top: 50%; left: 50%; width: 14px; height: 14px;
    background: #4682B4; border-radius: 50%; transform: translate(-50%, -50%);
    box-shadow: 0 0 20px #4682B4;
}}
#aeroops-loader .loader-title {{ color: #fff; font-size: 2rem; font-weight: 700; }}
#aeroops-loader .loader-sub {{ color: rgba(255,255,255,0.5); font-size: 0.9rem; margin-top: 0.5rem; }}
</style>
<div id="aeroops-loader">
    <div class="radar-container">
        <div class="radar-ring"></div>
        <div class="radar-ring"></div>
        <div class="radar-ring"></div>
        <div class="radar-dot"></div>
    </div>
    <div class="loader-title">✈ AeroOps AI</div>
    <div class="loader-sub">Scanning Airport Systems...</div>
</div>
<script>
(function() {{
    var loader = document.getElementById('aeroops-loader');
    if (!loader) return;
    var key = 'aeroops_loaded';
    if (sessionStorage.getItem(key)) {{
        loader.classList.add('loader-hidden');
        return;
    }}
    sessionStorage.setItem(key, '1');
    setTimeout(function() {{ loader.classList.add('loader-hidden'); }}, {dur_ms + 500});
}})();
</script>
"""
