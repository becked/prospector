"""Tests for overview page filter connections.

Verifies that all charts on the overview page are properly connected
to all filter inputs using Dash's runtime callback registry.

This catches issues like:
- Charts without callbacks (would show empty/stale)
- Charts missing filter inputs (wouldn't respond to filter changes)
- Typos in component IDs (callback wouldn't connect)
"""

import re
from pathlib import Path
from typing import Optional

import pytest


# Required filter inputs that every overview chart should receive
REQUIRED_FILTER_INPUTS = [
    "overview-round-filter-dropdown",
    "overview-turn-length-slider",
    "overview-map-size-dropdown",
    "overview-map-class-dropdown",
    "overview-map-aspect-dropdown",
    "overview-nations-dropdown",
    "overview-players-dropdown",
    "overview-result-dropdown",
]


@pytest.fixture(scope="module")
def registered_callbacks() -> list[dict]:
    """Import pages to register callbacks and return the callback list."""
    # Must import app first - it creates the Dash instance that pages register with
    from tournament_visualizer.app import app  # noqa: F401

    # Import triggers callback registration with Dash's global registry
    from tournament_visualizer.pages import overview  # noqa: F401
    from dash._callback import GLOBAL_CALLBACK_LIST

    return list(GLOBAL_CALLBACK_LIST)


@pytest.fixture(scope="module")
def overview_chart_ids() -> set[str]:
    """Extract all chart IDs defined in the overview page layout."""
    overview_path = (
        Path(__file__).parent.parent
        / "tournament_visualizer"
        / "pages"
        / "overview.py"
    )

    content = overview_path.read_text()

    # Find static chart_id="overview-..." patterns
    chart_ids = set(re.findall(r'chart_id="(overview-[^"]+)"', content))

    # Find dynamically generated yield chart IDs from YIELD_CHARTS constant
    yield_match = re.search(r"YIELD_CHARTS\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if yield_match:
        yield_types = re.findall(r'"(YIELD_\w+)"', yield_match.group(1))
        for yield_type in yield_types:
            # Convert YIELD_SCIENCE -> overview-yield-science
            chart_id = f"overview-yield-{yield_type.lower().replace('yield_', '')}"
            chart_ids.add(chart_id)

    return chart_ids


def find_callback_for_output(
    callbacks: list[dict], output_id: str
) -> Optional[dict]:
    """Find the callback that targets a specific output ID."""
    for cb in callbacks:
        output = cb.get("output", "")
        if isinstance(output, str):
            # Output format is "component-id.property"
            cb_output_id = output.split(".")[0]
            if cb_output_id == output_id:
                return cb
    return None


def get_callback_input_ids(callback: dict) -> list[str]:
    """Extract input component IDs from a callback."""
    return [inp["id"] for inp in callback.get("inputs", [])]


class TestOverviewFilterConnections:
    """Test that all overview charts are connected to filters."""

    def test_all_charts_have_callbacks(
        self,
        registered_callbacks: list[dict],
        overview_chart_ids: set[str],
    ) -> None:
        """Every chart in the layout should have a callback."""
        missing_callbacks = []

        for chart_id in overview_chart_ids:
            callback = find_callback_for_output(registered_callbacks, chart_id)
            if callback is None:
                missing_callbacks.append(chart_id)

        assert not missing_callbacks, (
            f"Charts without callbacks: {missing_callbacks}\n"
            "These charts will show empty/stale data."
        )

    def test_all_charts_receive_all_filters(
        self,
        registered_callbacks: list[dict],
        overview_chart_ids: set[str],
    ) -> None:
        """Every chart callback should receive all filter inputs."""
        incomplete_charts = []

        for chart_id in overview_chart_ids:
            callback = find_callback_for_output(registered_callbacks, chart_id)
            if callback is None:
                continue  # Covered by test_all_charts_have_callbacks

            input_ids = get_callback_input_ids(callback)
            missing_filters = [
                f for f in REQUIRED_FILTER_INPUTS if f not in input_ids
            ]

            if missing_filters:
                incomplete_charts.append((chart_id, missing_filters))

        assert not incomplete_charts, (
            f"Charts with missing filter inputs:\n"
            + "\n".join(
                f"  {chart}: missing {filters}"
                for chart, filters in incomplete_charts
            )
            + "\nThese charts won't respond to filter changes."
        )

    def test_filter_input_ids_are_valid(
        self,
        registered_callbacks: list[dict],
    ) -> None:
        """Verify the expected filter IDs actually exist as callback outputs."""
        # Find callbacks that populate the filter dropdowns
        filter_population_callbacks = [
            "overview-round-filter-dropdown",
            "overview-map-size-dropdown",
            "overview-map-class-dropdown",
            "overview-map-aspect-dropdown",
            "overview-nations-dropdown",
            "overview-players-dropdown",
        ]

        missing_filter_callbacks = []
        for filter_id in filter_population_callbacks:
            callback = find_callback_for_output(registered_callbacks, filter_id)
            if callback is None:
                missing_filter_callbacks.append(filter_id)

        assert not missing_filter_callbacks, (
            f"Filter dropdowns without population callbacks: {missing_filter_callbacks}\n"
            "These filters will have no options."
        )

    def test_chart_count_sanity_check(
        self,
        overview_chart_ids: set[str],
    ) -> None:
        """Sanity check that we found a reasonable number of charts."""
        # If this fails, the regex extraction may be broken
        assert len(overview_chart_ids) >= 20, (
            f"Only found {len(overview_chart_ids)} charts. "
            "Expected at least 20. Check chart ID extraction logic."
        )

    @pytest.mark.parametrize("filter_id", REQUIRED_FILTER_INPUTS)
    def test_each_filter_is_used_by_charts(
        self,
        registered_callbacks: list[dict],
        overview_chart_ids: set[str],
        filter_id: str,
    ) -> None:
        """Each filter should be used by at least one chart."""
        charts_using_filter = []

        for chart_id in overview_chart_ids:
            callback = find_callback_for_output(registered_callbacks, chart_id)
            if callback:
                input_ids = get_callback_input_ids(callback)
                if filter_id in input_ids:
                    charts_using_filter.append(chart_id)

        assert charts_using_filter, (
            f"Filter '{filter_id}' is not used by any chart. "
            "It may be dead code or incorrectly named."
        )
