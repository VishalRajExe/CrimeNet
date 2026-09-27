from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import os
import sys

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)


from visualizer import dash_formatter
from visualizer.case_dashboard import (
    build_global_nav_bar,
    build_dashboard_view,
    build_top_ask_crimenet_bar,
    build_case_directory_modal,
)
from visualizer.right_intelligence_panel import build_right_side_panel
from visualizer.alerts_panel import build_alerts_panel
from visualizer.ask_crimenet_panel import build_ask_crimenet_modal
from visualizer.audit_panel import build_audit_modal
from visualizer.reports_panel import build_reports_modal
from visualizer.actions_workflow_modal import build_actions_workflow_modal
from visualizer.relationship_panel import build_edge_source_modal
from visualizer.financial_workflow_panel import build_financial_workflow_modal
from visualizer.case_timeline_panel import build_case_timeline_modal
from visualizer.svg_icons import (
    icon_nodes, icon_edges, icon_labels, icon_filter, icon_link,
    icon_expand, icon_focus, icon_fit, icon_reset, icon_more_dots,
    icon_search, icon_sparkles
)


def build_workspace_secondary_nav():
    """Hidden bridge container for secondary navigation callbacks."""
    return html.Div(
        id='workspace-secondary-nav',
        style={'display': 'none'},
        children=[
            dbc.Button(id="bottom-nav-btn-evidence"),
        ]
    )


def init_layout(style, dataset_list, external_dataset_list= []):
    """
    Standard CrimeNet Investigation Workspace Cockpit Layout.
    - Single 48px Top Navigation Bar with CASE selector, Status Pill, Global Search, Ask CrimeNet, and Three-Dot Menu
    - Compact 54px Left Icon Rail with Popovers for Nodes, Edges, Labels, and Filters
    - Dominant Central Graph Canvas (>70% width) with pure white background, floating 5-action toolbar + [⋯ More], and zoom HUD
    - Right Intelligence Rail (380px) with 6 clean tabs (AI Intel, Dossier, Links, Alerts, Evidence, Timeline)
    """
    from storage.case_data_service import CaseDataService
    svc = CaseDataService()
    default_case = "case-synthetic-black-falcon-001"
    initial_elements = []
    try:
        net = svc.build_active_network_for_case(default_case)
        if net and net.elements:
            initial_elements = net.elements
    except Exception:
        pass

    workspace_content = html.Div(
        id='crimenet-workspace-cockpit',
        style={
            'display': 'flex',
            'flexDirection': 'row',
            'height': 'calc(100vh - 48px)',
            'width': '100%',
            'overflow': 'hidden',
            'backgroundColor': '#ffffff',
            'boxSizing': 'border-box',
        },
        children=[
            dcc.Store(id='inspected-edge-store', data=None),

            # ── 1. COMPACT 54PX LEFT RAIL WITH FLYOUT POPOVERS ──────────
            html.Div(
                id='sidebar',
                className='workspace-left-rail',
                style={
                    'width': '54px',
                    'minWidth': '54px',
                    'maxWidth': '54px',
                    'height': '100%',
                    'backgroundColor': '#f8fafc',
                    'borderRight': '1px solid #e2e8f0',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'alignItems': 'center',
                    'padding': '12px 0',
                    'gap': '12px',
                    'boxSizing': 'border-box',
                    'zIndex': '20',
                    'position': 'relative',
                },
                children=[
                    # 1. Nodes button + Popover
                    dbc.Button(
                        icon_nodes(color="#2563eb", size=18),
                        id="btn-rail-nodes",
                        className="btn-rail-icon",
                        style={"padding": "8px", "borderRadius": "8px", "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "boxShadow": "0 1px 2px rgba(0,0,0,0.05)"},
                    ),
                    dbc.Tooltip("Node Configuration & Types", target="btn-rail-nodes", placement="right"),
                    dbc.Popover(
                        id="popover-rail-nodes",
                        target="btn-rail-nodes",
                        trigger="legacy",
                        placement="right-start",
                        is_open=False,
                        style={"width": "340px", "maxWidth": "360px", "border": "1px solid #cbd5e1", "borderRadius": "8px", "boxShadow": "0 10px 25px rgba(0,0,0,0.12)", "backgroundColor": "#ffffff", "zIndex": 1050},
                        children=[
                            dbc.PopoverHeader("Node Types & Visibility", style={"backgroundColor": "#f8fafc", "borderBottom": "1px solid #e2e8f0", "fontWeight": "700", "fontSize": "13px", "color": "#0f172a"}),
                            dbc.PopoverBody([
                                html.Div(
                                    style={"display": "flex", "gap": "6px", "marginBottom": "10px"},
                                    children=[
                                        dbc.Button("Show All", id="show-all-button", size="sm", color="primary", style={"fontSize": "11px", "padding": "3px 8px"}),
                                        dbc.Button("Expand All", id="expand-all-button", size="sm", color="secondary", outline=True, style={"fontSize": "11px", "padding": "3px 8px"}),
                                    ]
                                ),
                                html.Div(
                                    id='node-interaction-div',
                                    className='element-interaction-div',
                                    style={"maxHeight": "240px", "overflowY": "auto"},
                                    children=[
                                        html.Table(id='node-interaction-table', className='element-interaction-table', children=[
                                            html.Tr(children=[html.Th('TYPE'), html.Th('SHOW'), html.Th('HIGHLIGHT')])
                                        ])
                                    ]
                                )
                            ])
                        ]
                    ),

                    # 2. Edges button + Popover
                    dbc.Button(
                        icon_edges(color="#2563eb", size=18),
                        id="btn-rail-edges",
                        className="btn-rail-icon",
                        style={"padding": "8px", "borderRadius": "8px", "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "boxShadow": "0 1px 2px rgba(0,0,0,0.05)"},
                    ),
                    dbc.Tooltip("Edge Configuration & Thresholds", target="btn-rail-edges", placement="right"),
                    dbc.Popover(
                        id="popover-rail-edges",
                        target="btn-rail-edges",
                        trigger="legacy",
                        placement="right-start",
                        is_open=False,
                        style={"width": "340px", "maxWidth": "360px", "border": "1px solid #cbd5e1", "borderRadius": "8px", "boxShadow": "0 10px 25px rgba(0,0,0,0.12)", "backgroundColor": "#ffffff", "zIndex": 1050},
                        children=[
                            dbc.PopoverHeader("Edge Types & Thresholds", style={"backgroundColor": "#f8fafc", "borderBottom": "1px solid #e2e8f0", "fontWeight": "700", "fontSize": "13px", "color": "#0f172a"}),
                            dbc.PopoverBody([
                                html.Div(
                                    id='edge-interaction-div',
                                    className='element-interaction-div',
                                    style={"maxHeight": "200px", "overflowY": "auto", "marginBottom": "12px"},
                                    children=[
                                        html.Table(id='edge-interaction-table', className='element-interaction-table', children=[
                                            html.Tr(children=[html.Th('TYPE'), html.Th('SHOW'), html.Th('HIGHLIGHT')])
                                        ])
                                    ]
                                ),
                                html.Div(
                                    id='edge-prop-slider-div',
                                    children=[
                                        html.P(id='edge-prop-label', children=['Set edge probability threshold:'], style={"fontSize": "11px", "fontWeight": "600", "color": "#475569", "marginBottom": "4px"}),
                                        dcc.Slider(
                                            id='edge-prob-slider', min=0, max=1, value=0.00, step=0.05,
                                            updatemode='drag',
                                            marks={0.00: '0.00', 0.25: '0.25', 0.50: '0.50', 0.75: '0.75', 1.00: '1.00'}
                                        ),
                                    ]
                                )
                            ])
                        ]
                    ),

                    # 3. Labels button + Popover
                    dbc.Button(
                        icon_labels(color="#2563eb", size=18),
                        id="btn-rail-labels",
                        className="btn-rail-icon",
                        style={"padding": "8px", "borderRadius": "8px", "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "boxShadow": "0 1px 2px rgba(0,0,0,0.05)"},
                    ),
                    dbc.Tooltip("Label Display Modes", target="btn-rail-labels", placement="right"),
                    dbc.Popover(
                        id="popover-rail-labels",
                        target="btn-rail-labels",
                        trigger="legacy",
                        placement="right-start",
                        is_open=False,
                        style={"width": "320px", "maxWidth": "340px", "border": "1px solid #cbd5e1", "borderRadius": "8px", "boxShadow": "0 10px 25px rgba(0,0,0,0.12)", "backgroundColor": "#ffffff", "zIndex": 1050},
                        children=[
                            dbc.PopoverHeader("Label Visibility", style={"backgroundColor": "#f8fafc", "borderBottom": "1px solid #e2e8f0", "fontWeight": "700", "fontSize": "13px", "color": "#0f172a"}),
                            dbc.PopoverBody([
                                html.Div(style={"marginBottom": "10px"}, children=[
                                    html.Label("Label Mode:", style={"fontSize": "11px", "fontWeight": "700", "color": "#475569", "marginBottom": "4px", "display": "block"}),
                                    dcc.RadioItems(
                                        id='ws-label-mode',
                                        options=[
                                            {'label': ' Name', 'value': 'name'},
                                            {'label': ' Name + Type', 'value': 'name_type'},
                                            {'label': ' None', 'value': 'none'}
                                        ],
                                        value='name',
                                        inline=True,
                                        style={'color': '#1e293b', 'fontSize': '12px', 'display': 'flex', 'gap': '12px'}
                                    )
                                ]),
                                html.Div(
                                    id='label-interaction-div',
                                    className='element-interaction-div',
                                    style={"maxHeight": "200px", "overflowY": "auto"},
                                    children=[
                                        html.Table(id='label-interaction-table', className='element-interaction-table', children=[
                                            html.Tr(children=[html.Th('VARIABLE', className="label-variable"), html.Th('DISPLAY')])
                                        ])
                                    ]
                                )
                            ])
                        ]
                    ),

                    # 4. Filters button + Popover
                    dbc.Button(
                        icon_filter(color="#2563eb", size=18),
                        id="btn-rail-filters",
                        className="btn-rail-icon",
                        style={"padding": "8px", "borderRadius": "8px", "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "boxShadow": "0 1px 2px rgba(0,0,0,0.05)"},
                    ),
                    dbc.Tooltip("Entity & Modality Filters", target="btn-rail-filters", placement="right"),
                    dbc.Popover(
                        id="popover-rail-filters",
                        target="btn-rail-filters",
                        trigger="legacy",
                        placement="right-start",
                        is_open=False,
                        style={"width": "320px", "maxWidth": "340px", "border": "1px solid #cbd5e1", "borderRadius": "8px", "boxShadow": "0 10px 25px rgba(0,0,0,0.12)", "backgroundColor": "#ffffff", "zIndex": 1050},
                        children=[
                            dbc.PopoverHeader("Graph Investigation Filters", style={"backgroundColor": "#f8fafc", "borderBottom": "1px solid #e2e8f0", "fontWeight": "700", "fontSize": "13px", "color": "#0f172a"}),
                            dbc.PopoverBody([
                                html.Div(style={"marginBottom": "10px"}, children=[
                                    html.Label("Entity Types:", style={"fontSize": "11px", "fontWeight": "700", "color": "#475569", "marginBottom": "4px", "display": "block"}),
                                    dcc.Dropdown(
                                        id='ws-filter-entity-type',
                                        placeholder='Filter Entity Types...',
                                        options=[
                                            {'label': 'Person', 'value': 'person'},
                                            {'label': 'Phone', 'value': 'phone'},
                                            {'label': 'Vehicle', 'value': 'vehicle'},
                                            {'label': 'Location', 'value': 'location'},
                                            {'label': 'Organization', 'value': 'organization'},
                                            {'label': 'Account', 'value': 'account'},
                                            {'label': 'Case', 'value': 'case'},
                                            {'label': 'Event', 'value': 'event'},
                                        ],
                                        multi=True,
                                        style={'fontSize': '12px'}
                                    )
                                ]),
                                html.Div(style={"marginBottom": "10px"}, children=[
                                    html.Label("Evidentiary Modality:", style={"fontSize": "11px", "fontWeight": "700", "color": "#475569", "marginBottom": "4px", "display": "block"}),
                                    dcc.Dropdown(
                                        id='ws-filter-modality',
                                        placeholder='Filter Modality...',
                                        options=[
                                            {'label': 'All Modalities', 'value': 'ALL'},
                                            {'label': 'Observed Fact (CDR/Direct)', 'value': 'OBSERVED'},
                                            {'label': 'Extracted (Document NLP)', 'value': 'EXTRACTED'},
                                            {'label': 'Predicted (AI Link)', 'value': 'PREDICTED'},
                                            {'label': 'Inferred (Reasoning/Rules)', 'value': 'INFERRED'},
                                        ],
                                        value='ALL',
                                        clearable=False,
                                        style={'fontSize': '12px'}
                                    )
                                ]),
                                html.Div(children=[
                                    html.Label("Acceptance Status:", style={"fontSize": "11px", "fontWeight": "700", "color": "#475569", "marginBottom": "4px", "display": "block"}),
                                    dcc.Dropdown(
                                        id='ws-filter-acceptance',
                                        placeholder='Acceptance Status...',
                                        options=[
                                            {'label': 'All Relationships', 'value': 'ALL'},
                                            {'label': 'Confirmed Only', 'value': 'CONFIRMED'},
                                            {'label': 'Proposed (Review)', 'value': 'PROPOSED'},
                                        ],
                                        value='ALL',
                                        clearable=False,
                                        style={'fontSize': '12px'}
                                    )
                                ])
                            ])
                        ]
                    ),

                    # 5. Documentation Icon Link at bottom
                    html.A(
                        icon_link(color="#64748b", size=18),
                        id="btn-rail-docs",
                        href="/userDocumentation",
                        target="_blank",
                        style={"marginTop": "auto", "padding": "8px", "borderRadius": "8px", "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0", "display": "flex", "alignItems": "center", "justifyContent": "center"},
                    ),
                    dbc.Tooltip("User Documentation", target="btn-rail-docs", placement="right"),

                    # Hidden Bridge for Legacy Inputs / Tables required by dash_io.py and callbacks
                    html.Div(
                        id="legacy-left-rail-bridge",
                        style={"display": "none"},
                        children=[
                            dcc.Tabs(id='tabs', value='tab-network', children=[
                                dcc.Tab(label='NETWORK', id='network-tab', value='tab-network', children=[
                                    dcc.Dropdown(id='choose-network', options=dash_formatter.dash_dataset_options(external_dataset_list, dataset_list)),
                                    dcc.Dropdown(id='choose-entities', options=[], multi=True),
                                    html.Button('Load Network', id='load-network-button'),
                                    dcc.Upload(id='upload', children=html.Button(id='upload-button'), multiple=False),
                                    html.Button('Load From File', id='load-file-button'),
                                    html.A(html.Button(id='save-network-button'), id='download-link', href='/downloadNetwork', download='network_state.json'),
                                    html.A(html.Button(id='export-network-button'), id='export-link', href='/exportNetwork', download='network_export.json'),
                                    html.Button(id='export-image-button'),
                                    html.Button(id='documentation-button'),
                                ]),
                                dcc.Tab(label='ANALYSIS', id='analysis-tab', value='tab-analysis', children=[
                                    html.Div(id="analysis-input", children=[
                                        dcc.Dropdown(id='choose-analysis', options=dash_formatter.dash_analysis_options()),
                                        dcc.Dropdown(id='analysis-algorithm', options=[]),
                                        html.Div(id='parameter-div', children=[dcc.Dropdown(id='parameter-1')]),
                                        html.Div(id='analysis-scope-div', children=[dcc.Dropdown(id='analysis-scope', value='FULL_NETWORK')]),
                                        dcc.Checklist(id='save-analysis-to-case', value=['SAVE']),
                                        html.Button(id='analysis-button'),
                                        html.Div(id='analysis-summary'),
                                        html.Div(id='hierarchical-tree-data'),
                                        html.Div(id='hierarchical-tree-view-wrapper'),
                                    ])
                                ]),
                                dcc.Tab(label='INTELLIGENCE', id='intelligence-tab', value='tab-intelligence', children=[
                                    html.Div(id='unbound-panel-wrapper', children=[html.Div(id='unbound-insights-panel')])
                                ])
                            ]),
                            html.Div(id='info-wrapper', children=[
                                html.Div(id='info-table-div', children=[html.Table(id='info-table')]),
                                html.Div(id='network-info'),
                            ]),
                            html.Div(id='element-interaction-container', hidden=True),
                            html.Div(id="original_network_button_div", hidden=True, children=[
                                dbc.Button(id='unaltered-collapse-button')
                            ]),
                            html.Div(id='warning-div'),
                            html.Div(id='search-div', hidden=True, children=[
                                dbc.Button(id='filter-button')
                            ]),
                            dbc.Tooltip(id="search-tooltip", target="filter-button"),
                            html.Div(id='interaction-div', hidden=True, children=[
                                dbc.Button(id='test-button'),
                                dbc.Button(id='open-edit-element'),
                                dbc.Button(id='open-add-element'),
                                dbc.Button(id='open-delete-element'),
                                dbc.Button(id='open-merge-element'),
                                dbc.Button(id='exclude-button'),
                                dbc.Button(id='isolate-button'),
                                dbc.Button(id='expand-button')
                            ])
                        ]
                    )
                ]
            ),

            # ── 2. CENTER STAGE: DOMINANT CYTOSCAPE CANVAS (>70% WIDTH) ────
            html.Div(
                id='main',
                className='workspace-center-stage',
                style={
                    'flex': '1 1 0%',
                    'minWidth': '480px',
                    'height': '100%',
                    'position': 'relative',
                    'backgroundColor': '#ffffff',
                    'overflow': 'hidden',
                    'boxSizing': 'border-box',
                },
                children=[
                    # Floating Graph Action Toolbar (Top Center)
                    html.Div(
                        id="graph-floating-toolbar",
                        className="graph-floating-toolbar",
                        style={
                            "position": "absolute",
                            "top": "12px",
                            "left": "50%",
                            "transform": "translateX(-50%)",
                            "zIndex": "100",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "6px",
                            "backgroundColor": "rgba(255, 255, 255, 0.96)",
                            "backdropFilter": "blur(8px)",
                            "border": "1px solid #cbd5e1",
                            "borderRadius": "8px",
                            "padding": "4px 8px",
                            "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.08)",
                        },
                        children=[
                            dbc.Button([icon_nodes(color="#2563eb", size=13), html.Span("1-Hop", style={"marginLeft": "5px", "fontSize": "11px", "fontWeight": "600"})], id="ws-btn-nhop-1", size="sm", color="light", style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}),
                            dbc.Button([icon_expand(color="#475569", size=13), html.Span("Expand", style={"marginLeft": "5px", "fontSize": "11px", "fontWeight": "600"})], id="ws-btn-expand-neighbors", size="sm", color="light", style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}),
                            dbc.Button([icon_focus(color="#475569", size=13), html.Span("Focus", style={"marginLeft": "5px", "fontSize": "11px", "fontWeight": "600"})], id="btn-cyto-center-selected", size="sm", color="light", style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}),
                            dbc.Button([icon_fit(color="#475569", size=13), html.Span("Fit", style={"marginLeft": "5px", "fontSize": "11px", "fontWeight": "600"})], id="btn-cyto-fit", size="sm", color="light", style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}),
                            dbc.Button([icon_reset(color="#64748b", size=13), html.Span("Reset", style={"marginLeft": "5px", "fontSize": "11px", "fontWeight": "600"})], id="ws-btn-reset-view", size="sm", color="light", style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}),
                            html.Span("|", style={"color": "#cbd5e1", "margin": "0 2px"}),
                            dbc.Button([html.Span("Path ➔", style={"fontSize": "11px", "fontWeight": "600", "color": "#2563eb"})], id="btn-open-path-popover", size="sm", color="light", style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}),
                            dbc.Popover(
                                id="popover-shortest-path",
                                target="btn-open-path-popover",
                                trigger="legacy",
                                placement="bottom",
                                is_open=False,
                                style={"width": "300px", "border": "1px solid #cbd5e1", "borderRadius": "8px", "boxShadow": "0 10px 25px rgba(0,0,0,0.12)", "backgroundColor": "#ffffff", "zIndex": 1050},
                                children=[
                                    dbc.PopoverHeader("Trace Shortest Evidentiary Path", style={"fontSize": "12px", "fontWeight": "700"}),
                                    dbc.PopoverBody([
                                        html.Div(style={"marginBottom": "8px"}, children=[
                                            html.Label("Source Entity:", style={"fontSize": "11px", "fontWeight": "600"}),
                                            dcc.Dropdown(id='ws-path-source', placeholder='Select Source...', options=[], style={'fontSize': '11px'})
                                        ]),
                                        html.Div(style={"marginBottom": "10px"}, children=[
                                            html.Label("Target Entity:", style={"fontSize": "11px", "fontWeight": "600"}),
                                            dcc.Dropdown(id='ws-path-target', placeholder='Select Target...', options=[], style={'fontSize': '11px'})
                                        ]),
                                        dbc.Button("Trace Connecting Path", id="ws-btn-find-path", size="sm", color="primary", style={"width": "100%", "fontSize": "11px", "fontWeight": "600"})
                                    ])
                                ]
                            ),
                            dbc.Button(
                                [html.Span("⋯ More", style={"fontSize": "11px", "fontWeight": "600"})],
                                id="ws-toolbar-more-menu-btn",
                                size="sm",
                                color="light",
                                style={"padding": "3px 8px", "border": "1px solid #e2e8f0"}
                            ),
                            dbc.Popover(
                                id="popover-toolbar-more",
                                target="ws-toolbar-more-menu-btn",
                                trigger="legacy",
                                placement="bottom-end",
                                is_open=False,
                                style={
                                    "width": "230px",
                                    "border": "1px solid #cbd5e1",
                                    "borderRadius": "8px",
                                    "boxShadow": "0 10px 25px rgba(0,0,0,0.12)",
                                    "backgroundColor": "#ffffff",
                                    "zIndex": 1050
                                },
                                children=[
                                    dbc.PopoverHeader("Advanced Graph Actions", style={"fontSize": "11px", "fontWeight": "700", "backgroundColor": "#f8fafc", "borderBottom": "1px solid #e2e8f0"}),
                                    dbc.PopoverBody(
                                        style={"padding": "6px 8px"},
                                        children=[
                                            html.Div("N-HOP EXPLORATION", style={"fontSize": "9px", "fontWeight": "700", "color": "#94a3b8", "padding": "4px 8px"}),
                                            dbc.Button("2-Hop Radius", id="ws-btn-nhop-2", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("3-Hop Perimeter", id="ws-btn-nhop-3", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            html.Hr(style={"margin": "4px 0", "borderColor": "#e2e8f0"}),
                                            html.Div("HIGHLIGHTS", style={"fontSize": "9px", "fontWeight": "700", "color": "#94a3b8", "padding": "4px 8px"}),
                                            dbc.Button("Highlight Money Flow", id="ws-btn-money-flow-toolbar", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("Highlight Key Bridges", id="ws-btn-highlight-bridges", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("Highlight AI Predictions", id="ws-btn-highlight-predicted", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("Clear Highlights", id="ws-btn-clear-highlights", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#dc2626", "textDecoration": "none"}),
                                            html.Hr(style={"margin": "4px 0", "borderColor": "#e2e8f0"}),
                                            html.Div("WORKFLOWS & LAYOUT", style={"fontSize": "9px", "fontWeight": "700", "color": "#94a3b8", "padding": "4px 8px"}),
                                            dbc.Button("Analytical Workflows", id="ws-sec-nav-actions", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("Financial Workflow", id="ws-sec-nav-financial", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("Event Timeline", id="ws-sec-nav-timeline", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#1e293b", "textDecoration": "none"}),
                                            dbc.Button("Re-execute Force Layout", id="btn-cyto-relayout", color="link", style={"width": "100%", "textAlign": "left", "padding": "4px 8px", "fontSize": "11px", "color": "#2563eb", "textDecoration": "none"}),
                                        ]
                                    )
                                ]
                            ),
                            html.Div(id="ws-toolbar-more-menu", style={"display": "none"})
                        ]
                    ),
                    dbc.Tooltip("Filter visible graph to 1-hop connections", target="ws-btn-nhop-1", placement="bottom"),
                    dbc.Tooltip("Expand direct neighbors of selected entity", target="ws-btn-expand-neighbors", placement="bottom"),
                    dbc.Tooltip("Center viewport on selected entity", target="btn-cyto-center-selected", placement="bottom"),
                    dbc.Tooltip("Fit full case network in viewport", target="btn-cyto-fit", placement="bottom"),
                    dbc.Tooltip("Reset view and clear focus isolate", target="ws-btn-reset-view", placement="bottom"),

                    # Floating Zoom Controls (Bottom Right)
                    html.Div(
                        id="graph-floating-zoom",
                        className="graph-floating-zoom",
                        style={
                            "position": "absolute",
                            "bottom": "16px",
                            "right": "16px",
                            "zIndex": "50",
                            "display": "flex",
                            "alignItems": "center",
                            "backgroundColor": "rgba(255, 255, 255, 0.96)",
                            "backdropFilter": "blur(8px)",
                            "border": "1px solid #cbd5e1",
                            "borderRadius": "20px",
                            "boxShadow": "0 2px 8px rgba(15, 23, 42, 0.08)",
                            "overflow": "hidden",
                        },
                        children=[
                            dbc.Button("−", id="btn-cyto-zoom-out", size="sm", color="light", style={"border": "none", "borderRadius": "0", "fontWeight": "700", "padding": "4px 10px", "fontSize": "13px"}),
                            html.Span("100%", id="label-zoom-indicator", style={"fontSize": "11px", "fontWeight": "700", "color": "#64748b", "padding": "0 8px"}),
                            dbc.Button("+", id="btn-cyto-zoom-in", size="sm", color="light", style={"border": "none", "borderRadius": "0", "fontWeight": "700", "padding": "4px 10px", "fontSize": "13px"}),
                        ]
                    ),

                    # Modality Legend (Bottom Left)
                    html.Div(
                        id="graph-modality-legend",
                        style={
                            "position": "absolute",
                            "bottom": "16px",
                            "left": "16px",
                            "zIndex": "50",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "12px",
                            "backgroundColor": "rgba(255, 255, 255, 0.94)",
                            "backdropFilter": "blur(8px)",
                            "border": "1px solid #e2e8f0",
                            "borderRadius": "6px",
                            "padding": "4px 10px",
                            "boxShadow": "0 1px 4px rgba(0,0,0,0.04)",
                            "fontSize": "10.5px",
                            "color": "#475569",
                            "fontWeight": "600",
                        },
                        children=[
                            html.Span([html.Span("―", style={"color": "#10b981", "fontWeight": "900", "fontSize": "14px", "marginRight": "4px"}), "Observed"]),
                            html.Span([html.Span("―", style={"color": "#8b5cf6", "fontWeight": "900", "fontSize": "14px", "marginRight": "4px"}), "Extracted"]),
                            html.Span([html.Span("- -", style={"color": "#f59e0b", "fontWeight": "900", "fontSize": "14px", "marginRight": "4px"}), "Predicted"]),
                            html.Span([html.Span("····", style={"color": "#06b6d4", "fontWeight": "900", "fontSize": "14px", "marginRight": "4px"}), "Inferred"]),
                        ]
                    ),

                    # Cytoscape Graph Elements
                    dcc.Loading(
                        id='loading-cytoscape',
                        type='dot',
                        color='#2563eb',
                        style={'width': '100%', 'height': '100%'},
                        children=[
                            cyto.Cytoscape(
                                id='cytoscape-unaltered',
                                stylesheet=style.stylesheet,
                                layout={'name': 'cose-bilkent'},
                                elements=[],
                                responsive=False,
                                style={'display': 'none'},
                            ),
                            cyto.Cytoscape(
                                className='cytoscape',
                                id='cytoscape',
                                stylesheet=style.stylesheet,
                                layout={'name': 'cose-bilkent'},
                                elements=initial_elements,
                                responsive=True,
                                minZoom=0.2,
                                maxZoom=2.5,
                                style={'width': '100%', 'height': '100%', 'backgroundColor': '#ffffff'}
                            ),
                        ]
                    ),

                    # Secondary Nav Hidden Bridge
                    build_workspace_secondary_nav(),
                ]
            ),

            # ── 3. RIGHT RAIL: DEDICATED 6-TAB INTELLIGENCE DRAWER ───────────
            html.Div(
                id='workspace-right-rail',
                style={
                    'width': '380px',
                    'minWidth': '330px',
                    'maxWidth': '420px',
                    'height': '100%',
                    'overflow': 'hidden',
                    'backgroundColor': '#ffffff',
                    'borderLeft': '1px solid #e2e8f0',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'boxSizing': 'border-box',
                },
                children=[
                    build_right_side_panel(),
                    html.Div(id='evidence-inspector-card', style={'display': 'none'})
                ]
            )
        ]
    )

    return html.Div(id='crimenet-root-app', style={'backgroundColor': '#ffffff', 'minHeight': '100vh', 'overflow': 'hidden'}, children=[
        dcc.Store(id='active-case-store', storage_type='session', data=None),
        dcc.Store(id='dossier-active-case-id-store', storage_type='session', data=None),
        # 1. Top CASE Bar
        build_global_nav_bar(),
        # 2. Top [Ask CrimeNet...] Query Bar (Hidden bridge)
        build_top_ask_crimenet_bar(),
        # 3. Main Central Investigation Cockpit
        html.Div(
            id='workspace-view',
            style={'display': 'block', 'height': 'calc(100vh - 48px)', 'overflow': 'hidden'},
            children=[workspace_content]
        ),
        # 4. Secondary Case Directory / Management (Accessed via Case Directory Modal without leaving workspace)
        html.Div(
            id='case-dashboard-view',
            style={'display': 'none'},
            children=[build_dashboard_view()]
        ),
        build_case_directory_modal(),
        # ── Forensic Alerts Panel (rendered inside workspace tabs) ──────────
        html.Div(
            id='alerts-panel-outer',
            style={'display': 'none'},
            children=[build_alerts_panel()]
        ),
        # ── Ask CrimeNet floating button + full-screen modal ─────────────
        build_ask_crimenet_modal(),
        # ── Investigation Workflows & Forensics Modals ───────────────────
        build_audit_modal(),
        build_reports_modal(),
        build_actions_workflow_modal(),
        build_edge_source_modal(),
        build_financial_workflow_modal(),
        build_case_timeline_modal(),
        html.P(id='hidden-info', children=[]),
        html.Div(id='unbound-intel-trigger', style={'display': 'none'}),
        html.Div(id='modal', className='modal',
                 children=[advanced_search, edit_element, add_element, delete_element, merge_element,
                           add_node, add_edge, export_image, confirm_load, confirm_load2,
                           confirm_file_load, confirm_file_load2])
    ])


edit_element = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Edit the selected Element"),
            html.Hr(),
            dbc.ModalBody(children=[
                html.Div(id='edit-element-container', children=[
                    dbc.Label("Element Type"),
                    dcc.Dropdown(id="edit-element-type", className='type-dropdown', value='', options=[],
                                 clearable=False)
                ]),
                html.Hr(),
                html.Div(className='add-property-div', children=[
                    dbc.Input(id="add-edit-property-label", className='add-label', value='',
                              placeholder='Property...', type='text'),
                    dbc.Input(id="add-edit-property-value", className='add-value', value='',
                              placeholder='Value...', type='text'),
                    html.Button("+", id="add-edit-property-button", className="add-property-button")
                ])
            ]),
            html.Hr(),
            dbc.ModalFooter(
                [dbc.Button("Apply", id="apply-edit-button", className="modal-button"),
                 dbc.Button("Close", id="close-dialog", className="modal-button")]), ],
        is_open=False,
        id="modal-edit",
        className='modal-content',
        centered=True
    )
])

add_element = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Add a new element"),
            dbc.ModalBody(html.Div(id='node-edge-add-buttons', children=[
                dbc.Button("Node", id="add-node-button", className="modal-button dialog-add-button"),
                dbc.Button("Edge", id="add-edge-button", className="modal-button dialog-add-button")
            ])),
            dbc.ModalFooter(
                [dbc.Button("Close", id="close-dialog", className="modal-button")]
            )
        ],
        is_open=False,
        id="modal-add",
        className='modal-content',
        centered=True
    ),
])


add_node = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Add a new Node"),
            html.Hr(),
            dbc.ModalBody(children=[
                html.Div(id='addnode-element-container', children=[
                    dbc.Label("Element Type"),
                    dcc.Dropdown(id="addnode-element-type", className='type-dropdown', value='', options=[]),
                    dbc.Label("Element Name"),
                    html.Div(className='text-field-div', children=[
                        dbc.Input(id="addnode-element-name", className='text-input', value='',
                                  placeholder='Name (Label, Descriptor) of the element ...', type='text'),
                        html.Button('-', id={
                            'type': 'remove-input-field',
                            'id': 'remove-addnode-name'
                            }, className='remove-property-button')
                        ])
                ]),
                html.Hr(),
                html.Div(className='add-property-div', children=[
                    dbc.Input(id="add-addnode-property-label", className='add-label', value='',
                              placeholder='Property...', type='text'),
                    dbc.Input(id="add-addnode-property-value", className='add-value', value='',
                              placeholder='Value...', type='text'),
                    dbc.Button("+", id="add-addnode-property-button", className="add-property-button")
                ])
            ]),
            html.Hr(),
            dbc.ModalFooter(
                [dbc.Button("Apply", id="apply-addnode-button", className="modal-button"),
                 dbc.Button("Close", id="close-dialog", className="modal-button")]), ],
        is_open=False,
        id="modal-addnode",
        className='modal-content',
        centered=True
    )
])


add_edge = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Add a new edge"),
            html.Hr(),
            dbc.ModalBody(children=[
                html.Div(id='addedge-element-container', children=[
                    dbc.Label("Element Type"),
                    dcc.Dropdown(id="addedge-element-type", className='type-dropdown', value='', options=[]),
                    dbc.Label("Element Name"),
                    html.Div(className='text-field-div', children=[
                        dbc.Input(id="addedge-element-name", className='text-input', value='',
                                  placeholder='Name (Label, Descriptor) of the element ...', type='text'),
                        html.Button('-', id={
                            'type': 'remove-input-field',
                            'id': 'remove-addedge-name'
                            }, className='remove-property-button')
                    ])
                ]),
                html.Hr(),
                html.Div(className='add-property-div', children=[
                    dbc.Input(id="add-addedge-property-label", className='add-label', value='',
                              placeholder='Property...', type='text'),
                    dbc.Input(id="add-addedge-property-value", className='add-value', value='',
                              placeholder='Value...', type='text'),
                    dbc.Button("+", id="add-addedge-property-button", className="add-property-button")
                ]),
                html.Hr(),
                html.Div(className='add-edge-div', children=[
                    dbc.Label("Source Node"),
                    dcc.Dropdown(id="addedge-source-node", className='type-dropdown', value='', options=[]),
                    dbc.Label("Target Node"),
                    dcc.Dropdown(id="addedge-target-node", className='type-dropdown', value='', options=[]),
                ]),
            ]),
            html.Hr(),
            dbc.ModalFooter(
                [dbc.Button("Apply", id="apply-addedge-button", className="modal-button"),
                 dbc.Button("Close", id="close-dialog", className="modal-button")]), ],
        is_open=False,
        id="modal-addedge",
        className='modal-content',
        centered=True
    )
])

delete_element = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Delete selected Element(s)?"),
            dbc.ModalBody("Element(s) are permanently deleted. If you want to hide elements "
                          "from the visualization only, use the 'Hide Element(s) instead."),
            dbc.ModalFooter(
                [dbc.Button("Delete", id="delete-button", className="modal-button"),
                 dbc.Button("Close", id="close-dialog", className="modal-button")]
            )
        ],
        is_open=False,
        id="modal-delete",
        className='modal-content',
        centered=True
    ),
])

merge_element = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Merge selected elements"),
            html.Hr(),
            dbc.ModalBody(children=[
                html.Div(id='merge-element-container', children=[
                    dbc.Label("Element Type"),
                    dcc.Dropdown(id="merge-elements-type", className='type-dropdown', value='', options=[])
                ]),
                html.Hr(),
                html.Div(className='add-property-div', children=[
                    dbc.Input(id="add-merge-property-label", className='add-label', value='',
                              placeholder='Property...', type='text'),
                    dbc.Input(id="add-merge-property-value", className='add-value', value='',
                              placeholder='Value...', type='text'),
                    dbc.Button("+", id="add-merge-property-button", className="add-property-button")
                ])
            ]),
            html.Hr(),
            dbc.ModalFooter(
                [dbc.Button("Apply", id="apply-merge-button", className="modal-button"),
                 dbc.Button("Close", id="close-dialog", className="modal-button")]), ],
        is_open=False,
        id="modal-merge",
        className='modal-content',
        centered=True
    ),
])

export_image = html.Div([
    dbc.Modal([
        dbc.ModalHeader("Export Image"),
        dbc.ModalBody(children= [
            dbc.Label("Select image format:"),
            dcc.Dropdown(className='inputs',
                         id='export-dropdown',
                         placeholder="Select file type ...",
                         multi=False,
                         options=dash_formatter.dash_type_options(['svg', 'png', 'jpeg'])
                         )
        ]),
        dbc.ModalFooter(
            [dbc.Button("Download", id="apply-export-image-button", className="modal-button"),
             dbc.Button("Close", id="close-dialog", className="modal-button")]
        )],
        is_open=False,
        id="modal-export-image",
        className='modal-content',
        centered=True
        )
])

confirm_load = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Load a new network?"),
            dbc.ModalBody("Unsaved progress will be lost and not restoreable.", className="centered-modal-body"),
            dbc.ModalFooter(
                [dbc.Button("Continue", id="confirm-load-button", className="modal-button"),
                 dbc.Button("Cancel", id="close-dialog", className="modal-button")]
            )
        ],
        is_open=False,
        id="modal-confirm-load",
        className='modal-content',
        centered=True
    ),
])

confirm_load2 = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Loading new network ...", id='confirm-load2-header'),
            dbc.ModalBody("Loading big networks may take some time.", className="centered-modal-body"),
            dbc.ModalFooter(
                [dbc.Button("Continue", id="confirm-load-button2", className="single-modal-button")]
            )
        ],
        is_open=False,
        id="modal-load-done",
        className='modal-content',
        centered=True
    ),
])

confirm_file_load = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("LOAD NETWORK FROM FILE"),
            dbc.ModalBody("Select a network data file from you local drive.", className="centered-modal-body"),
            dbc.ModalFooter([
                dcc.Upload(dbc.Button("Load File", id="confirm-file-load-button", className="modal-button"), id='upload-modal'),
                dbc.Button("Cancel", id="close-dialog", className="modal-button")
            ])
        ],
        is_open=False,
        id="modal-confirm-file-load",
        className='modal-content',
        centered=True
    ),
])

confirm_file_load2 = html.Div([
    dbc.Modal(
        [
            dbc.ModalHeader("Loading new network from file...", id='confirm-file-load2-header'),
            dbc.ModalBody("Loading big networks may take some time.", className="centered-modal-body"),
            dbc.ModalFooter(
                [dbc.Button("Continue", id="confirm-file-load-button2", className="single-modal-button")]
            )
        ],
        is_open=False,
        id="modal-file-load-done",
        className='modal-content',
        centered=True
    ),
])


advanced_search = html.Div([
    dbc.Modal(
        is_open=False,
        id="modal-search",
        className='modal-content',
        centered=True,
        children=[
            dbc.ModalHeader("Search & Filter Network"),
            html.Div(
                style={'padding': '15px 20px 5px 20px'},
                children=[
                    html.Label("Quick Search (Name, ID, or Keyword):", style={'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Input(
                        id="search-quick-input",
                        type="text",
                        placeholder="Type name, ID, or keyword to search...",
                        style={'width': '100%', 'padding': '8px 12px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'fontSize': '13px', 'boxSizing': 'border-box'}
                    ),
                    html.Div(style={'fontSize': '11px', 'color': '#777', 'marginTop': '4px'}, children="Leave blank to use property-specific filters below.")
                ]
            ),
            html.Hr(style={'margin': '10px 0'}),
            html.Div(
                style={'padding': '0 20px'},
                children=[
                    html.Label("Property Filters:", style={'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                ]
            ),
            dbc.ModalBody(id='filter-container', children=dash_formatter.init_filters([])),
            html.Hr(style={'margin': '10px 0'}),
            html.Div(id='addsearch-criteria-div',
                     children=[
                         html.Button("+ Add Filter Property",
                                     id="add-search-property-button",
                                     className="add-property-button",
                                     style={'width': '100%', 'padding': '6px'})
                     ]
            ),
            html.Hr(style={'margin': '10px 0'}),
            dbc.ModalFooter([
                dbc.Button("Reset", id="reset-filter-button", className="modal-button", style={'marginRight': 'auto'}),
                dbc.Button("Apply", id="apply-filter-button", className="modal-button"),
                dbc.Button("Close", id="close-dialog", className="modal-button")
            ])
        ],

    )
])
