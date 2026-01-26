"""Page layout components for the tournament visualizer.

This module provides reusable layout components including cards, grids,
and common page structures for the dashboard.
"""

from typing import Any, Dict, List, Optional, Union

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..config import LAYOUT_CONSTANTS, MODEBAR_CONFIG
from ..theme import DARK_THEME


# Tournament Round Formatting Helpers


def format_round_display(round_num: Optional[int]) -> str:
    """Convert tournament round number to human-readable format.

    Args:
        round_num: Round number (positive=Winners, negative=Losers, None=Unknown)

    Returns:
        Formatted string like "Winners Round 1" or "Unknown"

    Examples:
        >>> format_round_display(1)
        'Winners Round 1'
        >>> format_round_display(-2)
        'Losers Round 2'
        >>> format_round_display(None)
        'Unknown'
    """
    if round_num is None:
        return "Unknown"
    elif round_num > 0:
        return f"Winners Round {round_num}"
    elif round_num < 0:
        return f"Losers Round {abs(round_num)}"
    else:
        return "Unknown"


def get_round_badge_color(round_num: Optional[int]) -> str:
    """Get Bootstrap color class for round badge.

    Args:
        round_num: Round number

    Returns:
        Bootstrap color class name

    Examples:
        >>> get_round_badge_color(1)
        'success'
        >>> get_round_badge_color(-1)
        'warning'
        >>> get_round_badge_color(None)
        'secondary'
    """
    if round_num is None:
        return "secondary"  # Gray for unknown
    elif round_num > 0:
        return "success"  # Green for winners
    else:
        return "warning"  # Yellow for losers


def create_round_badge(round_num: Optional[int]) -> html.Span:
    """Create a Bootstrap badge showing tournament round.

    Args:
        round_num: Round number

    Returns:
        Dash HTML component for badge

    Example:
        badge = create_round_badge(1)
        # Returns: <span class="badge bg-success">Winners Round 1</span>
    """
    return html.Span(
        format_round_display(round_num),
        className=f"badge bg-{get_round_badge_color(round_num)}",
        style={"marginLeft": "8px", "fontSize": "0.9em"},
    )


# Card Creation Functions


def create_metric_card(
    title: str,
    value: Union[str, int, float],
    icon: str = "bi-bar-chart",
    color: str = "primary",
    subtitle: str = None,
) -> dbc.Card:
    """Create a metric display card.

    Args:
        title: Card title
        value: Main metric value
        icon: Bootstrap icon class
        color: Bootstrap color theme
        subtitle: Optional subtitle text

    Returns:
        Card component with metric display
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.I(className=f"{icon} fs-1 text-{color}"),
                                ],
                                className="col-auto",
                            ),
                            html.Div(
                                [
                                    html.H3(str(value), className="mb-0"),
                                    html.P(title, className="text-muted mb-0"),
                                    (
                                        html.Small(subtitle, className="text-muted")
                                        if subtitle
                                        else html.Div()
                                    ),
                                ],
                                className="col",
                            ),
                        ],
                        className="row align-items-center",
                    )
                ]
            )
        ],
        className="h-100",
    )


def create_chart_card(
    title: str,
    chart_id: str,
    height: str = "400px",
    loading: bool = False,  # Disabled by default to avoid spinner flashes during tab caching
    controls: List = None,
    info_text: str = None,
) -> dbc.Card:
    """Create a card containing a chart.

    Args:
        title: Card title
        chart_id: ID for the chart component
        height: Chart height
        loading: Whether to show loading spinner (disabled by default)
        controls: Optional list of control components
        info_text: Optional explanatory text shown below title

    Returns:
        Card component with chart
    """
    chart_component = dcc.Graph(
        id=chart_id,
        style={"height": height},
        config=MODEBAR_CONFIG,
    )

    if loading:
        chart_component = dcc.Loading(chart_component, type="default")

    card_body = [html.H5(title, className="card-title")]

    if info_text:
        card_body.append(
            html.P(
                info_text,
                className="text-muted small mb-2",
                style={"fontSize": "0.8rem"},
            )
        )

    if controls:
        card_body.extend([html.Div(controls, className="mb-3"), html.Hr()])

    card_body.append(chart_component)

    return dbc.Card([dbc.CardBody(card_body)], className="h-100")


def create_data_table_card(
    title: str, table_id: str, columns: List[Dict[str, str]], export_button: bool = True
) -> dbc.Card:
    """Create a card containing a data table.

    Args:
        title: Card title
        table_id: ID for the table component
        columns: Table column definitions
        export_button: Whether to include export button

    Returns:
        Card component with data table
    """
    from dash import dash_table

    header_controls = [html.H5(title, className="card-title mb-0")]

    if export_button:
        header_controls.append(
            dbc.Button(
                [html.I(className="bi bi-download me-2"), "Export"],
                id=f"{table_id}-export",
                color="outline-primary",
                size="sm",
            )
        )

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        header_controls,
                        className="d-flex justify-content-between align-items-center mb-3",
                    ),
                    dash_table.DataTable(
                        id=table_id,
                        columns=columns,
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        filter_options={"case": "insensitive"},
                        page_action="native",
                        page_size=LAYOUT_CONSTANTS["TABLE_PAGE_SIZE"],
                        style_table={
                            "backgroundColor": DARK_THEME["bg_dark"],
                        },
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "fontFamily": "inherit",
                            "backgroundColor": DARK_THEME["bg_dark"],
                            "color": DARK_THEME["text_primary"],
                            "border": f"1px solid {DARK_THEME['bg_light']}",
                        },
                        style_header={
                            "backgroundColor": "#3b4c69",
                            "fontWeight": "bold",
                            "color": DARK_THEME["text_primary"],
                            "border": f"1px solid {DARK_THEME['bg_light']}",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": DARK_THEME["bg_medium"],
                            },
                            {
                                "if": {"state": "active"},
                                "backgroundColor": DARK_THEME["bg_light"],
                                "border": f"1px solid {DARK_THEME['accent_primary']}",
                            },
                        ],
                        style_filter={
                            "backgroundColor": "#41597b",
                            "color": DARK_THEME["text_primary"],
                        },
                    ),
                ]
            )
        ],
        className="h-100",
    )


def create_filter_card(title: str, filters: List, collapsible: bool = True) -> dbc.Card:
    """Create a card containing filter controls.

    Args:
        title: Card title
        filters: List of filter components
        collapsible: Whether the card is collapsible

    Returns:
        Card component with filters
    """
    if collapsible:
        return dbc.Card(
            [
                dbc.CardHeader(
                    [
                        dbc.Button(
                            [html.I(className="bi bi-funnel me-2"), title],
                            id=f"collapse-{title.lower().replace(' ', '-')}-button",
                            color="link",
                            className="text-decoration-none p-0",
                        )
                    ]
                ),
                dbc.Collapse(
                    [dbc.CardBody(filters)],
                    id=f"collapse-{title.lower().replace(' ', '-')}",
                    is_open=True,
                ),
            ],
            className="mb-3",
        )
    else:
        return dbc.Card(
            [
                dbc.CardHeader([html.I(className="bi bi-funnel me-2"), title]),
                dbc.CardBody(filters),
            ],
            className="mb-3",
        )


def create_page_header(
    title: str, description: str = "", icon: str = "", actions: List = None
) -> html.Div:
    """Create a page header with title and optional actions.

    Args:
        title: Page title
        description: Page description
        icon: Bootstrap icon class
        actions: Optional list of action buttons

    Returns:
        Page header component
    """
    header_content = []

    # Title and icon
    title_content = []
    if icon:
        title_content.append(html.I(className=f"{icon} me-2"))
    title_content.append(title)

    header_content.append(
        html.Div(
            [
                html.H1(title_content, className="mb-2"),
                (
                    html.P(description, className="text-muted")
                    if description
                    else html.Div()
                ),
            ],
            className="col",
        )
    )

    # Actions
    if actions:
        header_content.append(html.Div(actions, className="col-auto d-flex gap-2"))

    return html.Div(
        [html.Div(header_content, className="row align-items-center"), html.Hr()],
        className="mb-4",
    )


def create_two_column_layout(
    left_content: List, right_content: List, left_width: int = 8, right_width: int = 4
) -> dbc.Row:
    """Create a two-column layout.

    Args:
        left_content: Components for left column
        right_content: Components for right column
        left_width: Bootstrap column width for left side
        right_width: Bootstrap column width for right side

    Returns:
        Row component with two columns
    """
    return dbc.Row(
        [
            dbc.Col(left_content, width=left_width),
            dbc.Col(right_content, width=right_width),
        ]
    )


def create_three_column_layout(
    left_content: List,
    center_content: List,
    right_content: List,
    widths: List[int] = [4, 4, 4],
) -> dbc.Row:
    """Create a three-column layout.

    Args:
        left_content: Components for left column
        center_content: Components for center column
        right_content: Components for right column
        widths: List of column widths

    Returns:
        Row component with three columns
    """
    return dbc.Row(
        [
            dbc.Col(left_content, width=widths[0]),
            dbc.Col(center_content, width=widths[1]),
            dbc.Col(right_content, width=widths[2]),
        ]
    )


def create_metric_grid(metrics: List[Dict[str, Any]]) -> dbc.Row:
    """Create a grid of metric cards.

    Args:
        metrics: List of metric configurations

    Returns:
        Row component with metric cards
    """
    cards = []

    for metric in metrics:
        card = create_metric_card(
            title=metric.get("title", ""),
            value=metric.get("value", ""),
            icon=metric.get("icon", "bi-bar-chart"),
            color=metric.get("color", "primary"),
            subtitle=metric.get("subtitle"),
        )

        col_width = 12 // min(len(metrics), 4)  # Max 4 columns
        cards.append(dbc.Col(card, width=col_width, className="mb-3"))

    return dbc.Row(cards)


def create_chart_grid(charts: List[Dict[str, Any]], columns: int = 2) -> List[dbc.Row]:
    """Create a grid of chart cards.

    Args:
        charts: List of chart configurations
        columns: Number of columns per row

    Returns:
        List of row components with chart cards
    """
    rows = []
    col_width = 12 // columns

    for i in range(0, len(charts), columns):
        row_charts = charts[i : i + columns]
        cols = []

        for chart in row_charts:
            card = create_chart_card(
                title=chart.get("title", ""),
                chart_id=chart.get("chart_id", ""),
                height=chart.get("height", "400px"),
                controls=chart.get("controls"),
            )
            cols.append(dbc.Col(card, width=col_width, className="mb-3"))

        rows.append(dbc.Row(cols))

    return rows


def create_tab_layout(
    tabs: List[Dict[str, Any]],
    active_tab: str = None,
    tabs_id: str = None,
) -> dbc.Tabs:
    """Create a tabbed layout.

    Args:
        tabs: List of tab configurations with 'label', 'tab_id', and 'content'
        active_tab: ID of initially active tab
        tabs_id: ID for the Tabs component (needed for lazy loading callbacks)

    Returns:
        Tabs component
    """
    tab_components = []

    for tab in tabs:
        tab_components.append(
            dbc.Tab(
                label=tab.get("label", ""),
                tab_id=tab.get("tab_id", ""),
                children=tab.get("content", []),
            )
        )

    # Build kwargs, only including id if tabs_id is provided
    tabs_kwargs = {
        "active_tab": active_tab or (tabs[0].get("tab_id") if tabs else None),
    }
    if tabs_id:
        tabs_kwargs["id"] = tabs_id

    return dbc.Tabs(tab_components, **tabs_kwargs)


def create_loading_placeholder(text: str = "Loading...") -> html.Div:
    """Create a loading placeholder.

    Args:
        text: Loading text to display

    Returns:
        Loading placeholder component
    """
    return html.Div(
        [
            dbc.Spinner(color="primary", size="lg"),
            html.P(text, className="mt-2 text-muted"),
        ],
        className="text-center py-5",
    )


def create_error_alert(
    message: str, title: str = "Error", dismissible: bool = True
) -> dbc.Alert:
    """Create an error alert.

    Args:
        message: Error message
        title: Alert title
        dismissible: Whether alert can be dismissed

    Returns:
        Alert component
    """
    return dbc.Alert(
        [html.H4(title, className="alert-heading"), html.P(message)],
        color="danger",
        dismissable=dismissible,
    )


def create_info_alert(
    message: str, title: str = "Information", dismissible: bool = True
) -> dbc.Alert:
    """Create an info alert.

    Args:
        message: Info message
        title: Alert title
        dismissible: Whether alert can be dismissed

    Returns:
        Alert component
    """
    return dbc.Alert(
        [html.H4(title, className="alert-heading"), html.P(message)],
        color="info",
        dismissable=dismissible,
    )


def create_empty_state(
    title: str = "No Data Available",
    message: str = "There is no data to display with the current filters.",
    icon: str = "bi-inbox",
    action_button: Dict[str, Any] = None,
) -> html.Div:
    """Create an empty state placeholder.

    Args:
        title: Empty state title
        message: Empty state message
        icon: Bootstrap icon class
        action_button: Optional action button configuration

    Returns:
        Empty state component
    """
    content = [
        html.I(className=f"{icon} display-1 text-muted mb-3"),
        html.H3(title, className="text-muted"),
        html.P(message, className="text-muted"),
    ]

    if action_button:
        content.append(
            dbc.Button(
                action_button.get("text", "Action"),
                id=action_button.get("id", ""),
                color=action_button.get("color", "primary"),
                className="mt-3",
            )
        )

    return html.Div(content, className="text-center py-5")


def create_breadcrumb(items: List[Dict[str, str]]) -> dbc.Breadcrumb:
    """Create a breadcrumb navigation.

    Args:
        items: List of breadcrumb items with 'label' and optional 'href'

    Returns:
        Breadcrumb component
    """
    breadcrumb_items = []

    for i, item in enumerate(items):
        is_active = i == len(items) - 1

        breadcrumb_items.append(
            {
                "label": item.get("label", ""),
                "href": item.get("href") if not is_active else None,
                "active": is_active,
            }
        )

    return dbc.Breadcrumb(items=breadcrumb_items)


def create_sidebar_layout(
    sidebar_content: List, main_content: List, sidebar_width: int = 3
) -> dbc.Row:
    """Create a layout with sidebar and main content.

    Args:
        sidebar_content: Components for sidebar
        main_content: Components for main content area
        sidebar_width: Bootstrap column width for sidebar

    Returns:
        Row component with sidebar layout
    """
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        sidebar_content, className="sticky-top", style={"top": "20px"}
                    )
                ],
                width=sidebar_width,
            ),
            dbc.Col(main_content, width=12 - sidebar_width),
        ]
    )


def create_modal_dialog(
    modal_id: str,
    title: str,
    body_content: List,
    footer_content: List = None,
    size: str = "lg",
) -> dbc.Modal:
    """Create a modal dialog.

    Args:
        modal_id: Modal component ID
        title: Modal title
        body_content: Modal body content
        footer_content: Optional modal footer content
        size: Modal size ('sm', 'lg', 'xl')

    Returns:
        Modal component
    """
    modal_content = [
        dbc.ModalHeader(dbc.ModalTitle(title)),
        dbc.ModalBody(body_content),
    ]

    if footer_content:
        modal_content.append(dbc.ModalFooter(footer_content))

    return dbc.Modal(modal_content, id=modal_id, size=size, is_open=False)
