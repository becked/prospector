"""Chat page for natural language tournament data queries.

Users type questions in plain English and get tabular results,
powered by Groq's free tier LLM translating to DuckDB SQL.
"""

import logging
from typing import Any, Optional

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dash_table, dcc, html

from tournament_visualizer.components.layouts import create_empty_state
from tournament_visualizer.config import get_config
from tournament_visualizer.theme import DARK_THEME

logger = logging.getLogger(__name__)

dash.register_page(__name__, path="/chat", name="Chat")

_EXAMPLE_QUESTIONS = [
    "What is Carthage's win rate?",
    "Who built the most wonders?",
    "Which players researched both Scholarship and Jurisprudence?",
    "What are the most popular civilizations?",
    "Who had the highest science yield at turn 50?",
    "Which matches had the biggest drop in military power?",
]

layout = html.Div(
    [
        # Page header
        html.Div(
            [
                html.H2("Chat", className="mb-3"),
            ],
            className="px-4 pt-4",
        ),
        # Input area
        html.Div(
            [
                dbc.InputGroup(
                    [
                        dbc.Input(
                            id="chat-input",
                            type="text",
                            placeholder="e.g., What is Carthage's win rate?",
                            autoFocus=True,
                        ),
                        dbc.Button(
                            "Ask",
                            id="chat-submit",
                            color="primary",
                            n_clicks=0,
                        ),
                    ],
                    className="mb-3",
                    size="lg",
                ),
                # Example questions
                html.Div(
                    [
                        html.Small("Try: ", className="text-muted me-2"),
                    ]
                    + [
                        html.A(
                            q,
                            id={"type": "chat-example", "index": i},
                            href="#",
                            className="text-muted me-3",
                            style={
                                "fontSize": "0.85em",
                                "textDecoration": "underline",
                                "cursor": "pointer",
                            },
                        )
                        for i, q in enumerate(_EXAMPLE_QUESTIONS[:3])
                    ],
                    className="mb-4",
                ),
            ],
            className="px-4",
        ),
        # Results area with loading spinner
        html.Div(
            [
                dcc.Loading(
                    id="chat-loading",
                    type="default",
                    children=html.Div(id="chat-results"),
                ),
            ],
            className="px-4 pb-4",
        ),
        # Hidden store to trigger query when example is clicked
        dcc.Store(id="chat-example-trigger"),
    ]
)


@callback(
    Output("chat-input", "value"),
    Output("chat-example-trigger", "data"),
    Input({"type": "chat-example", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def fill_example_question(n_clicks: list[Optional[int]]) -> tuple[Any, Any]:
    """Populate the input and trigger the query when an example is clicked."""
    if not ctx.triggered_id or not any(n_clicks):
        return dash.no_update, dash.no_update
    index = ctx.triggered_id["index"]
    question = _EXAMPLE_QUESTIONS[index]
    return question, question


@callback(
    Output("chat-results", "children"),
    Input("chat-submit", "n_clicks"),
    Input("chat-input", "n_submit"),
    Input("chat-example-trigger", "data"),
    State("chat-input", "value"),
    prevent_initial_call=True,
)
def handle_chat_query(
    n_clicks: int,
    n_submit: Optional[int],
    example_trigger: Optional[str],
    question: Optional[str],
) -> Any:
    """Handle natural language query submission."""
    if not question or not question.strip():
        return html.Div()

    from tournament_visualizer.data.nl_query import get_nl_query_service

    service = get_nl_query_service()
    result = service.ask(question.strip())

    children: list[Any] = [
        html.Div(
            [html.I(className="bi bi-chat-left-text me-2"), question.strip()],
            className="text-muted mb-3",
            style={"fontSize": "0.95em"},
        ),
    ]

    # Error or info message
    if result.error_message:
        color = "warning" if result.is_rate_limited else "danger"
        if result.success:
            # Truncation warning
            color = "info"
        icon = (
            "bi-hourglass-split"
            if result.is_rate_limited
            else "bi-exclamation-triangle"
        )
        if result.success:
            icon = "bi-info-circle"
        children.append(
            dbc.Alert(
                [html.I(className=f"bi {icon} me-2"), result.error_message],
                color=color,
                className="mb-3",
            )
        )

    # Results table
    if result.success and not result.df.empty:
        columns = [{"name": str(col), "id": str(col)} for col in result.df.columns]
        children.append(
            dash_table.DataTable(
                id="chat-results-table",
                columns=columns,
                data=result.df.to_dict("records"),
                sort_action="native",
                page_action="native",
                page_size=20,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "8px 12px",
                    "fontFamily": "inherit",
                    "backgroundColor": DARK_THEME["bg_dark"],
                    "color": DARK_THEME["text_primary"],
                    "border": f"1px solid {DARK_THEME['bg_light']}",
                    "maxWidth": "300px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_header={
                    "backgroundColor": DARK_THEME["bg_medium"],
                    "fontWeight": "bold",
                    "color": DARK_THEME["text_primary"],
                    "border": f"1px solid {DARK_THEME['bg_light']}",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": DARK_THEME["bg_medium"],
                    },
                ],
            )
        )
    elif result.success and result.df.empty:
        children.append(
            create_empty_state(
                title="No Results",
                message="The query returned no data. Try rephrasing your question.",
                icon="bi-inbox",
            )
        )

    # Collapsible SQL display (dev only)
    if result.sql and get_config().DEBUG_MODE:
        children.append(
            html.Details(
                [
                    html.Summary(
                        "Generated SQL",
                        style={"cursor": "pointer", "color": DARK_THEME["text_muted"]},
                        className="mt-3 mb-2",
                    ),
                    html.Pre(
                        result.sql,
                        style={
                            "backgroundColor": DARK_THEME["bg_darkest"],
                            "color": DARK_THEME["text_secondary"],
                            "padding": "12px",
                            "borderRadius": "4px",
                            "fontSize": "0.85em",
                            "whiteSpace": "pre-wrap",
                            "overflowX": "auto",
                        },
                    ),
                ],
                className="mt-2",
            )
        )

    return html.Div(children)
