"""Theme configuration for dark mode."""

from typing import TypedDict


class ThemeColors(TypedDict):
    bg_darkest: str
    bg_dark: str
    bg_medium: str
    bg_light: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_primary: str
    accent_info: str
    accent_success: str
    accent_warning: str
    accent_danger: str


DARK_THEME: ThemeColors = {
    # Dark blue palette
    "bg_darkest": "#0e1b2e",  # Body background
    "bg_dark": "#364c6b",     # Cards, containers, chart backgrounds
    "bg_medium": "#3a5a7e",   # Inputs, headers
    "bg_light": "#45678e",    # Hover states
    "text_primary": "#edf2f7",
    "text_secondary": "#c8d4e3",
    "text_muted": "#9db0c9",
    "accent_primary": "#64b5f6",
    "accent_info": "#4dd0e1",
    "accent_success": "#4aba6e",
    "accent_warning": "#ffb74d",
    "accent_danger": "#ef5350",
}


CHART_THEME = {
    "paper_bgcolor": "#364c6b",
    "plot_bgcolor": "#364c6b",
    "font_color": DARK_THEME["text_primary"],
    "text_muted": DARK_THEME["text_muted"],
    "gridcolor": "rgba(255, 255, 255, 0.1)",
    "legend_bgcolor": "rgba(58, 90, 126, 0.9)",  # Based on bg_medium
    "legend_bordercolor": "rgba(255, 255, 255, 0.1)",
    # Hover tooltip styling (cannot be done via CSS)
    "hoverlabel_bgcolor": DARK_THEME["bg_medium"],
    "hoverlabel_bordercolor": DARK_THEME["bg_light"],
    "hoverlabel_font_color": DARK_THEME["text_primary"],
}
