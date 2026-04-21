# theme.py

> File: `utils/theme.py`

## Overview

Centralized airport-themed styling for the entire Streamlit dashboard. Defines color palettes, SVG icons, status indicators, and reusable UI component functions (metric cards, page headers, section headers). Every page imports from this module.

## Data Dependencies

None — pure constants and rendering functions.

## Key Constants

### COLORS
```python
COLORS = {
    "navy": "#1B2A4A",           # Primary text, headers
    "sky_blue": "#4A90D9",       # Accent, links, highlights
    "safety_orange": "#FF6B35",  # Safety-related elements
    "success_green": "#2ECC71",  # Healthy status
    "warning_yellow": "#F1C40F", # Warning status
    "danger_red": "#E74C3C",     # Critical status
    "light_gray": "#ECF0F1",     # Backgrounds, borders
    "dark_gray": "#2C3E50",      # Secondary text
    "white": "#FFFFFF",          # Card backgrounds
}
```

### SVG_ICONS
24×24 navy-stroke SVG icons for page headers and section headers:
- **Stream icons:** flights, passengers, cargo, environmental, runway, security
- **Chart icons:** chart_up, bar_chart, target
- **UI icons:** wrench, calendar, clock, rocket, clipboard, link, sankey, impact, rules, quarantine, reverse, tags, stethoscope, search, lightbulb, alert_circle, chat, robot, pulse, trash, add_circle

### Status SVGs (16×16, colored)
- `healthy` — green checkmark circle
- `warning` — yellow triangle exclamation
- `critical` — red X circle

## Key Functions

### `apply_theme(st) → None`
Injects full CSS stylesheet into the Streamlit page. Covers:
- Page background, sidebar, headers, metric cards
- Chat input styling (transparent bottom container, white input)
- Expander, button, dataframe styling

### `page_header(title, svg_icon) → str`
Returns HTML for a page title with SVG icon and styled heading.

### `section_header(title, icon_key) → str`
Returns HTML for a section divider with icon.

### `metric_card(label, value, status="neutral") → str`
Returns HTML for a KPI card with status-colored left border (green/yellow/red/neutral).

### `page_loader() → str`
Returns HTML for a loading spinner animation.

## Used By

All 7 dashboard pages, `utils/charts.py` (reads COLORS)

## Interview Questions

1. **Q: Why centralize theming instead of inline styles?**
   A: Single source of truth — changing a color updates every page. Also enables consistent status communication (green=healthy everywhere). Streamlit's native theming is limited, so we inject custom CSS.

2. **Q: Why SVG icons instead of emoji or icon libraries?**
   A: SVGs scale perfectly, match our color scheme (navy stroke), and load instantly without external dependencies. Emoji rendering varies across OS/browsers. Icon libraries (Font Awesome) add bundle size.
