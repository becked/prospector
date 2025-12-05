"""Tests for dark theme styling in layout components."""

from tournament_visualizer.components.layouts import create_data_table_card
from tournament_visualizer.theme import DARK_THEME


def test_data_table_card_uses_dark_cell_colors() -> None:
    """Verify DataTable cells use dark theme colors."""
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    # Extract DataTable from card structure: Card -> CardBody -> [Div, DataTable]
    card_body = card.children[0]
    data_table = card_body.children[1]

    assert data_table.style_cell["backgroundColor"] == DARK_THEME["bg_dark"]
    assert data_table.style_cell["color"] == DARK_THEME["text_primary"]


def test_data_table_card_uses_dark_header_colors() -> None:
    """Verify DataTable header uses dark theme colors."""
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    card_body = card.children[0]
    data_table = card_body.children[1]

    assert data_table.style_header["backgroundColor"] == DARK_THEME["bg_medium"]
    assert data_table.style_header["color"] == DARK_THEME["text_primary"]


def test_data_table_card_uses_dark_table_background() -> None:
    """Verify DataTable table background uses dark theme."""
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    card_body = card.children[0]
    data_table = card_body.children[1]

    assert data_table.style_table["backgroundColor"] == DARK_THEME["bg_dark"]


def test_data_table_card_uses_dark_filter_colors() -> None:
    """Verify DataTable filter uses dark theme colors."""
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    card_body = card.children[0]
    data_table = card_body.children[1]

    assert data_table.style_filter["backgroundColor"] == DARK_THEME["bg_medium"]
    assert data_table.style_filter["color"] == DARK_THEME["text_primary"]


def test_data_table_card_has_alternating_row_colors() -> None:
    """Verify DataTable has dark-themed alternating row colors."""
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    card_body = card.children[0]
    data_table = card_body.children[1]

    # Check odd row conditional styling
    odd_row_style = data_table.style_data_conditional[0]
    assert odd_row_style["if"]["row_index"] == "odd"
    assert odd_row_style["backgroundColor"] == DARK_THEME["bg_medium"]


def test_data_table_card_has_active_state_styling() -> None:
    """Verify DataTable has dark-themed active state styling."""
    card = create_data_table_card(
        title="Test",
        table_id="test-table",
        columns=[{"name": "Col", "id": "col"}],
    )
    card_body = card.children[0]
    data_table = card_body.children[1]

    # Check active state conditional styling
    active_style = data_table.style_data_conditional[1]
    assert active_style["if"]["state"] == "active"
    assert active_style["backgroundColor"] == DARK_THEME["bg_light"]
