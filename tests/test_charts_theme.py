"""Tests for chart theming functionality."""

import pytest

from tournament_visualizer.components.charts import (
    apply_dark_theme,
    create_base_figure,
    create_empty_chart_placeholder,
)
from tournament_visualizer.theme import CHART_THEME


def test_create_base_figure_uses_dark_background() -> None:
    """Verify create_base_figure uses dark theme background colors."""
    fig = create_base_figure()
    assert fig.layout.paper_bgcolor == CHART_THEME["paper_bgcolor"]
    assert fig.layout.plot_bgcolor == CHART_THEME["plot_bgcolor"]


def test_create_base_figure_uses_light_text() -> None:
    """Verify create_base_figure uses light text color."""
    fig = create_base_figure()
    assert fig.layout.font.color == CHART_THEME["font_color"]


def test_create_base_figure_has_hoverlabel_styling() -> None:
    """Verify create_base_figure includes hover tooltip styling."""
    fig = create_base_figure()
    assert fig.layout.hoverlabel.bgcolor == CHART_THEME["hoverlabel_bgcolor"]
    assert fig.layout.hoverlabel.font.color == CHART_THEME["hoverlabel_font_color"]


def test_create_base_figure_does_not_mutate_default() -> None:
    """Verify create_base_figure doesn't mutate the default layout."""
    fig1 = create_base_figure(height=300)
    fig2 = create_base_figure(height=500)
    assert fig1.layout.height == 300
    assert fig2.layout.height == 500


def test_create_empty_chart_placeholder_uses_dark_theme() -> None:
    """Verify create_empty_chart_placeholder uses dark theme."""
    fig = create_empty_chart_placeholder("Test message")
    assert fig.layout.paper_bgcolor == CHART_THEME["paper_bgcolor"]
    assert fig.layout.plot_bgcolor == CHART_THEME["plot_bgcolor"]


def test_apply_dark_theme_to_subplots() -> None:
    """Verify apply_dark_theme works on subplots."""
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1)
    # Before: default backgrounds (None or white)
    assert fig.layout.paper_bgcolor is None

    fig = apply_dark_theme(fig)
    # After: dark theme applied
    assert fig.layout.paper_bgcolor == CHART_THEME["paper_bgcolor"]
    assert fig.layout.plot_bgcolor == CHART_THEME["plot_bgcolor"]
    assert fig.layout.font.color == CHART_THEME["font_color"]
    assert fig.layout.hoverlabel.bgcolor == CHART_THEME["hoverlabel_bgcolor"]


def test_apply_dark_theme_updates_all_axes() -> None:
    """Verify apply_dark_theme updates axes for subplots."""
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1)
    fig = apply_dark_theme(fig)

    # Check first axis
    assert fig.layout.xaxis.gridcolor == CHART_THEME["gridcolor"]
    assert fig.layout.yaxis.gridcolor == CHART_THEME["gridcolor"]

    # Check second axis (created by subplot)
    assert fig.layout.xaxis2.gridcolor == CHART_THEME["gridcolor"]
    assert fig.layout.yaxis2.gridcolor == CHART_THEME["gridcolor"]
