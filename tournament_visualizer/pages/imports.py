"""Import page for uploading and processing tournament save files.

This page allows users to upload Old World save files (.zip) and process them
into the DuckDB database.
"""

import base64
import io
import logging
import traceback
from pathlib import Path
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from tournament_visualizer.config import Config
from tournament_visualizer.data.etl import TournamentETL
from tournament_visualizer.data.database import get_database

dash.register_page(__name__, path="/import", title="Import Data")

logger = logging.getLogger(__name__)

# Page layout
layout = dbc.Container(
    [
        html.H2([html.I(className="bi bi-upload me-2"), "Import Tournament Data"], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-file-earmark-zip me-2"),
                        "Upload Save Files"
                    ]),
                    dbc.CardBody([
                        # Upload component
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.Br(),
                                html.A('Select Files', style={'color': '#007bff', 'cursor': 'pointer'}),
                            ]), 
                            multiple=True,
                            accept='.zip'
                        ),
                        
                        
                        # Options
                        dbc.Row([
                            dbc.Col([
                                dbc.Checkbox(
                                    id="deduplicate-checkbox",
                                    label="Deduplicate files (recommended)",
                                    value=True,
                                ),
                            ], width=6),
                            dbc.Col([
                                dbc.Checkbox(
                                    id="skip-processed-checkbox",
                                    label="Skip already processed files",
                                    value=True,
                                ),
                            ], width=6),
                        ], className="mb-3"),
                    ])
                ], className="mb-4"),
            ], md=8),
            
            # Status panel
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-info-circle me-2"),
                        "Import Status"
                    ]),
                    dbc.CardBody([
                        html.Div(id="import-status", children=[
                            html.P("No files selected", className="text-muted mb-0")
                        ])
                    ])
                ]),
            ], md=4),
        ]),
        
        # Progress and results
        html.Div(id="processing-area", className="mt-4"),
        
        # Store for file data
        dcc.Store(id='uploaded-files-store'),
    ],
    fluid=True,
    className="py-4"
)


@callback(
    Output('uploaded-files-store', 'data'),
    Output('import-status', 'children'),
    Output('processing-area', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('deduplicate-checkbox', 'value'),
    State('skip-processed-checkbox', 'value'),
    prevent_initial_call=True
)
def process_uploaded_files(contents: Optional[List[str]], filenames: Optional[List[str]], deduplicate: bool, skip_processed: bool):
    """Process uploaded files immediately upon selection.
    
    Args:
        contents: List of base64-encoded file contents
        filenames: List of filenames
        deduplicate: Whether to deduplicate files
        skip_processed: Whether to skip already processed files
        
    Returns:
        Tuple of (stored_files, status_display, processing_results)
    """
    if not contents or not filenames:
        raise PreventUpdate
    
    # Validate all files are .zip
    invalid_files = [f for f in filenames if not f.endswith('.zip')]
    if invalid_files:
        error_display = dbc.Alert([
            html.H5("Invalid Files", className="alert-heading"),
            html.P(f"Only .zip files are supported. Found: {', '.join(invalid_files)}")
        ], color="danger")
        return None, error_display, None
    
    # Store file data and show initial status
    files_data = []
    total_size = 0
    
    for content, filename in zip(contents, filenames):
        # Get file size from base64 string
        content_string = content.split(',')[1]
        file_size = len(base64.b64decode(content_string))
        total_size += file_size
        
        files_data.append({
            'filename': filename,
            'content': content,
            'size': file_size
        })
    
    # Format size
    size_mb = total_size / (1024 * 1024)
    
    # Show processing status
    status_display = [
        html.H6(f"Processing {len(filenames)} files...", className="mb-2"),
        html.P([
            html.Strong("Total size: "),
            f"{size_mb:.2f} MB"
        ], className="mb-2"),
        dbc.Spinner(color="primary", size="sm")
    ]
    
    # Process the files
    logger.info(f"Processing {len(files_data)} uploaded files")
        
    # Initialize ETL
    db = get_database(read_only = False)
    etl = TournamentETL(db)
    
    results = []
    successful = 0
    failed = 0
    skipped = 0
    
    # Create temporary directory for processing
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save uploaded files to temp directory
        temp_files = []
        for file_data in files_data:
            content_string = file_data['content'].split(',')[1]
            decoded = base64.b64decode(content_string)
            
            temp_path = Path(temp_dir) / file_data['filename']
            with open(temp_path, 'wb') as f:
                f.write(decoded)
            
            temp_files.append(str(temp_path))
        
        # Check for already processed files
        if skip_processed:
            files_to_process = []
            for temp_path in temp_files:
                if etl.is_file_processed(temp_path):
                    filename = Path(temp_path).name
                    results.append({
                        'filename': filename,
                        'status': 'skipped',
                        'message': 'Already processed'
                    })
                    skipped += 1
                else:
                    files_to_process.append(temp_path)
        else:
            files_to_process = temp_files
        
        # Deduplicate if requested
        if deduplicate and len(files_to_process) > 1:
            files_to_process, skipped_dupes = etl.find_duplicates(
                [Path(f) for f in files_to_process],
                deduplicate=True
            )
            
            for skipped_file in skipped_dupes:
                results.append({
                    'filename': Path(skipped_file['file_path']).name,
                    'status': 'skipped',
                    'message': f"Duplicate: {skipped_file['reason']}"
                })
                skipped += 1
        
        # Process files
        for file_path in files_to_process:
            filename = Path(file_path).name
            
            try:
                # Extract Challonge match ID from filename
                challonge_match_id = etl.extract_challonge_match_id(file_path)
                
                # Process the file
                success = etl.process_tournament_file(file_path, challonge_match_id)
                
                if success:
                    results.append({
                        'filename': filename,
                        'status': 'success',
                        'message': f'Processed successfully' + (f' (Match ID: {challonge_match_id})' if challonge_match_id else '')
                    })
                    successful += 1
                else:
                    results.append({
                        'filename': filename,
                        'status': 'error',
                        'message': 'Processing failed (check logs)'
                    })
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                logger.error(traceback.format_exc())
                results.append({
                    'filename': filename,
                    'status': 'error',
                    'message': str(e)
                })
                failed += 1
        
        # Get summary
        summary = etl.get_processing_summary()
        
    finally:
        # Cleanup temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Could not remove temp directory: {e}")
    
    # Update status display
    final_status = [
        html.H6(f"Completed", className="mb-2 text-success"),
        html.P([
            html.Strong("Successful: "), f"{successful} | ",
            html.Strong("Failed: "), f"{failed} | ",
            html.Strong("Skipped: "), f"{skipped}"
        ], className="mb-0 small")
    ]
    
    # Build results display
    processing_results = build_results_display(results, successful, failed, skipped, summary)
    
    return files_data, final_status, processing_results





def build_results_display(results, successful, failed, skipped, summary):
    """Build the results display component.
    
    Args:
        results: List of result dictionaries
        successful: Count of successful imports
        failed: Count of failed imports
        skipped: Count of skipped files
        summary: Database summary statistics
        
    Returns:
        Dash component tree
    """
    # Summary cards
    summary_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(successful, className="text-success mb-0"),
                    html.P("Successful", className="mb-0 text-muted")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(failed, className="text-danger mb-0"),
                    html.P("Failed", className="mb-0 text-muted")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(skipped, className="text-warning mb-0"),
                    html.P("Skipped", className="mb-0 text-muted")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H3(summary.get('total_matches', 0), className="text-primary mb-0"),
                    html.P("Total Matches", className="mb-0 text-muted")
                ])
            ])
        ], width=3),
    ], className="mb-4")
    
    # Results table
    if results:
        result_rows = []
        for r in results:
            icon_class = {
                'success': 'bi-check-circle-fill text-success',
                'error': 'bi-x-circle-fill text-danger',
                'skipped': 'bi-dash-circle-fill text-warning'
            }.get(r['status'], 'bi-question-circle')
            
            result_rows.append(
                html.Tr([
                    html.Td(html.I(className=icon_class)),
                    html.Td(r['filename']),
                    html.Td(r['message'], className="small text-muted")
                ])
            )
        
        results_table = dbc.Card([
            dbc.CardHeader("Processing Details"),
            dbc.CardBody([
                dbc.Table([
                    html.Tbody(result_rows)
                ], bordered=True, hover=True, size="sm")
            ], style={'maxHeight': '400px', 'overflowY': 'auto'})
        ])
    else:
        results_table = None
    
    # Database summary
    db_summary = dbc.Card([
        dbc.CardHeader("Database Summary"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.Strong("Total Matches: "),
                        summary.get('total_matches', 0)
                    ]),
                    html.P([
                        html.Strong("Total Players: "),
                        summary.get('total_players', 0)
                    ]),
                    html.P([
                        html.Strong("Unique Players: "),
                        summary.get('unique_players', 0)
                    ]),
                ], width=6),
                dbc.Col([
                    html.P([
                        html.Strong("Events: "),
                        summary.get('total_events', 0)
                    ]),
                    html.P([
                        html.Strong("Territory Records: "),
                        summary.get('total_territories', 0)
                    ]),
                    html.P([
                        html.Strong("Yield Records: "),
                        summary.get('total_resources', 0)
                    ]),
                ], width=6),
            ])
        ])
    ], className="mt-3")
    
    return html.Div([
        summary_cards,
        results_table,
        db_summary
    ])