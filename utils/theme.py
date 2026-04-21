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

# Stream icons (emoji fallback)
STREAM_ICONS = {
    "flights": "✈️",
    "passengers": "👥",
    "cargo": "📦",
    "environmental": "🌡️",
    "runway": "🛬",
    "security": "🔒",
}

_N = COLORS["navy"]

# SVG icon library — reusable across all pages
SVG_ICONS = {
    # ── Stream icons (24×24, navy stroke) ──
    "flights": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M17.8 19.2L16 11l3.5-3.5C20.3 6.7 21 5.4 21 4.5c0-.6-.2-.9-.3-1'
        '-.1-.1-.4-.3-1-.3-.9 0-2.2.7-3 1.5L13 8.2 5 6.4a.5.5 0 0 0-.5.2l-1 1.3'
        'a.5.5 0 0 0 .1.6L9 12l-2 2.5H4.5a.5.5 0 0 0-.4.2l-1 1.3a.5.5 0 0 0 '
        '.1.6l3 1.5 1.5 3a.5.5 0 0 0 .6.1l1.3-1a.5.5 0 0 0 .2-.4V17.5l2.5-2 '
        '3.5 5.4a.5.5 0 0 0 .6.1l1.3-1a.5.5 0 0 0 .2-.5z"/></svg>'
    ),
    "passengers": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/>'
        '<circle cx="19" cy="7" r="3"/><path d="M22 21v-1.5a3 3 0 0 0-2.5-2.96"/></svg>'
    ),
    "cargo": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<rect x="3" y="7" width="18" height="13" rx="2"/>'
        '<path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<path d="M12 12v4"/><path d="M3 12h18"/></svg>'
    ),
    "environmental": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M12 9a4 4 0 0 0-2 7.5"/><path d="M12 3v2"/>'
        '<path d="M6.6 18.4l-1.4 1.4"/><path d="M20 12h-2"/>'
        '<path d="M6 12H4"/><path d="M12 5a7 7 0 0 1 7 7c0 3-2 5.4-4 6.5"/>'
        '<line x1="12" y1="12" x2="12" y2="21"/></svg>'
    ),
    "runway": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<rect x="4" y="3" width="16" height="18" rx="1"/>'
        '<line x1="12" y1="6" x2="12" y2="8"/><line x1="12" y1="10" x2="12" y2="12"/>'
        '<line x1="12" y1="14" x2="12" y2="16"/><line x1="12" y1="18" x2="12" y2="20"/></svg>'
    ),
    "security": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<path d="M9 12l2 2 4-4"/></svg>'
    ),
    # ── Section header icons ──
    "chart_up": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
    ),
    "bar_chart": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<rect x="3" y="12" width="4" height="9" rx="1"/>'
        '<rect x="10" y="7" width="4" height="14" rx="1"/>'
        '<rect x="17" y="3" width="4" height="18" rx="1"/></svg>'
    ),
    "target": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/></svg>'
    ),
    "wrench": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77'
        'a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91'
        'a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>'
    ),
    "calendar": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/></svg>'
    ),
    "clock": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/></svg>'
    ),
    "rocket": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91'
        'a2.18 2.18 0 0 0-2.91-.09z"/>'
        '<path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 '
        '7.5-6 11a22.35 22.35 0 0 1-4 2z"/>'
        '<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>'
        '<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>'
    ),
    "clipboard": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6'
        'a2 2 0 0 1 2-2h2"/>'
        '<rect x="8" y="2" width="8" height="4" rx="1"/></svg>'
    ),
    "link": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
        '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
    ),
    "sankey": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M2 6c4 0 4 6 8 6s4-6 8-6"/>'
        '<path d="M2 12c4 0 4 6 8 6s4-6 8-6"/>'
        '<path d="M2 18c4 0 4 6 8 6s4-6 8-6"/></svg>'
    ),
    "impact": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
    ),
    "rules": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M9 11l3 3L22 4"/>'
        '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>'
    ),
    "quarantine": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    ),
    "reverse": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<polyline points="1 4 1 10 7 10"/>'
        '<path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>'
    ),
    "tags": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59'
        'a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>'
    ),
    "stethoscope": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4'
        'a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/>'
        '<path d="M8 15v1a6 6 0 0 0 6 6 6 6 0 0 0 6-6v-4"/>'
        '<circle cx="20" cy="10" r="2"/></svg>'
    ),
    "search": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
    ),
    "lightbulb": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M9 18h6"/><path d="M10 22h4"/>'
        '<path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8'
        'c0 1 .23 2.23 1.5 3.5.76.76 1.23 1.52 1.41 2.5"/></svg>'
    ),
    "alert_circle": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    ),
    "chat": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
    ),
    "file_text": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>'
    ),
    "check": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<polyline points="20 6 9 17 4 12"/></svg>'
    ),
    "robot": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<rect x="3" y="11" width="18" height="10" rx="2"/>'
        '<circle cx="12" cy="5" r="2"/><line x1="12" y1="7" x2="12" y2="11"/>'
        '<line x1="8" y1="16" x2="8" y2="16.01"/>'
        '<line x1="16" y1="16" x2="16" y2="16.01"/></svg>'
    ),
    "gauge": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z"/>'
        '<path d="M12 6v6l4 2"/></svg>'
    ),
    "validate": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/></svg>'
    ),
    "leaf": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 '
        '0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>'
    ),
    "table": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<rect x="3" y="3" width="18" height="18" rx="2"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/>'
        '<line x1="9" y1="3" x2="9" y2="21"/></svg>'
    ),
    "freshness": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" style="vertical-align:middle">'
        '<path d="M21.5 2v6h-6"/>'
        '<path d="M2 12a10 10 0 0 1 18.8-4.3L21.5 8"/>'
        '<path d="M2.5 22v-6h6"/>'
        '<path d="M22 12a10 10 0 0 1-18.8 4.2L2.5 16"/></svg>'
    ),
    "pulse": (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:middle">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
    ),
    "trash": (
        f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:middle">'
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4'
        'a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>'
    ),
    "add_circle": (
        f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
        f'stroke="{_N}" stroke-width="1.5" stroke-linecap="round" '
        f'style="vertical-align:middle">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="8" x2="12" y2="16"/>'
        '<line x1="8" y1="12" x2="16" y2="12"/></svg>'
    ),
}

# Small colored status SVGs (16×16, for inline use in markdown)
_SVG_STATUS = {
    "healthy": f'<svg width="16" height="16" viewBox="0 0 24 24" fill="{COLORS["success_green"]}" stroke="{COLORS["success_green"]}" stroke-width="2" style="vertical-align:middle"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "warning": f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{COLORS["warning_yellow"]}" stroke-width="2" style="vertical-align:middle"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "critical": f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{COLORS["danger_red"]}" stroke-width="2" style="vertical-align:middle"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    "high": f'<svg width="16" height="16" viewBox="0 0 24 24" fill="{COLORS["danger_red"]}" stroke="none" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/></svg>',
    "medium": f'<svg width="16" height="16" viewBox="0 0 24 24" fill="{COLORS["warning_yellow"]}" stroke="none" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/></svg>',
    "low": f'<svg width="16" height="16" viewBox="0 0 24 24" fill="{COLORS["success_green"]}" stroke="none" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/></svg>',
}


def inline_svg(icon_key: str, size: int = 18) -> str:
    """Return an SVG icon resized for inline use in markdown text.

    Args:
        icon_key: Key into SVG_ICONS dict.
        size: Pixel size (width & height).
    """
    svg = SVG_ICONS.get(icon_key, "")
    if svg:
        svg = svg.replace('width="24"', f'width="{size}"', 1)
        svg = svg.replace('height="24"', f'height="{size}"', 1)
    return svg


def status_svg(level: str) -> str:
    """Return a small colored SVG for status/severity levels.

    Args:
        level: One of 'healthy', 'warning', 'critical', 'high', 'medium', 'low'.
    """
    return _SVG_STATUS.get(level, "")


def stream_svg(stream: str, size: int = 18) -> str:
    """Return an inline SVG for a stream name.

    Falls back to the emoji STREAM_ICONS if no SVG exists.

    Args:
        stream: Stream name (e.g. 'flights', 'passengers').
        size: Pixel size.
    """
    if stream in SVG_ICONS:
        return inline_svg(stream, size)
    return STREAM_ICONS.get(stream, "📊")


def section_header(title: str, icon_key: str) -> str:
    """Return HTML for a styled section header with SVG icon.

    Args:
        title: Section title text.
        icon_key: Key into SVG_ICONS dict.
    """
    svg = SVG_ICONS.get(icon_key, "")
    return (
        f'{svg} &nbsp; <span style="font-size:1.3rem;font-weight:700;'
        f'color:{COLORS["navy"]}">{title}</span>'
    )


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
            /* ── Chat input bottom container ── */
            [data-testid="stBottom"] {{
                background: linear-gradient(to bottom,
                    rgba(232, 238, 244, 0) 0%,
                    rgba(232, 238, 244, 1) 15%,
                    rgba(232, 238, 244, 1) 100%) !important;
                border: none !important;
                box-shadow: none !important;
            }}
            [data-testid="stBottom"] > div {{
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }}
            /* Add padding so content doesn't hide behind fixed chat input */
            [data-testid="stMain"] > div:first-child {{
                padding-bottom: 100px !important;
            }}
            /* ── Chat input ── */
            [data-testid="stChatInput"],
            [data-testid="stChatInput"] * {{
                background-color: {COLORS["white"]} !important;
            }}
            [data-testid="stChatInput"] {{
                border-radius: 24px !important;
                overflow: hidden;
                border: 2px solid #4682B4 !important;
                box-shadow: 0 2px 8px rgba(70, 130, 180, 0.15) !important;
            }}
            [data-testid="stChatInput"] textarea,
            [data-testid="stChatInput"] input {{
                color: {COLORS["dark_gray"]} !important;
                background-color: {COLORS["white"]} !important;
                font-size: 0.95rem !important;
                caret-color: {COLORS["navy"]} !important;
            }}
            [data-testid="stChatInput"] textarea::placeholder,
            [data-testid="stChatInput"] input::placeholder {{
                color: #888 !important;
            }}
            [data-testid="stChatInput"] button {{
                background-color: transparent !important;
            }}
            /* Chat message bubbles */
            [data-testid="stChatMessage"] {{
                border-radius: 12px !important;
                margin-bottom: 0.5rem !important;
                background: {COLORS["white"]} !important;
                border: 1px solid rgba(70, 130, 180, 0.12) !important;
            }}
            /* ── Expander headers ── */
            .stExpander > details > summary {{
                color: {COLORS["navy"]} !important;
                font-weight: 600 !important;
            }}
            /* ── Selectbox / dropdown / multiselect inputs ── */
            [data-testid="stSelectbox"] > div > div,
            [data-testid="stMultiSelect"] > div > div {{
                border: 1.5px solid #4682B4 !important;
                border-radius: 8px !important;
                background: {COLORS["white"]} !important;
                color: {COLORS["dark_gray"]} !important;
            }}
            [data-testid="stSelectbox"] [data-testid="stMarkdownContainer"],
            [data-testid="stMultiSelect"] [data-testid="stMarkdownContainer"] {{
                color: {COLORS["navy"]} !important;
                font-weight: 600 !important;
            }}
            /* ── Dataframe / table containers ── */
            [data-testid="stDataFrame"] {{
                border: 1px solid rgba(70, 130, 180, 0.15) !important;
                border-radius: 8px !important;
                overflow: hidden;
            }}
            /* ── Buttons (non-sidebar) ── */
            .stButton > button {{
                border-radius: 8px !important;
                border: 1.5px solid #4682B4 !important;
                color: {COLORS["navy"]} !important;
                font-weight: 600 !important;
                transition: all 0.2s ease !important;
            }}
            .stButton > button:hover {{
                background: linear-gradient(135deg, #4682B4, #2a4d7a) !important;
                color: {COLORS["white"]} !important;
            }}
            /* ── Tabs ── */
            .stTabs [data-baseweb="tab"] {{
                color: {COLORS["navy"]} !important;
                font-weight: 600 !important;
            }}
            .stTabs [aria-selected="true"] {{
                border-bottom-color: #4682B4 !important;
            }}
            /* ── Divider ── */
            [data-testid="stHorizontalBlock"] hr,
            .stDivider > hr {{
                border-color: rgba(70, 130, 180, 0.15) !important;
            }}
            /* ── Subheader styling ── */
            .stMarkdown h2, .stMarkdown h3 {{
                color: {COLORS["navy"]} !important;
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
