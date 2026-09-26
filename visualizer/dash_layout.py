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


def build_workspace_secondary_nav():
    """Bottom secondary navigation: Analysis, Evidence, Reports, Audit."""
    return html.Div(
        id='workspace-secondary-nav',
        style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'backgroundColor': '#131722',
            'borderTop': '1px solid #2a3447',
            'padding': '6px 14px',
            'boxShadow': '0 -2px 6px rgba(0,0,0,0.3)',
            'flexWrap': 'wrap',
            'gap': '8px',
            'zIndex': '10',
        },
        children=[
            html.Div(
                style={'display': 'flex', 'alignItems': 'center', 'gap': '8px', 'flexWrap': 'wrap'},
                children=[
                    html.Span("INVESTIGATION CONTROLS:", style={'color': '#718096', 'fontSize': '10px', 'fontWeight': '800', 'letterSpacing': '0.5px'}),
                    # 1. Analysis
                    dbc.Button(
                        [html.Span("🔬 "), "Analysis"],
                        id="ws-sec-nav-actions",
                        size="sm",
                        color="primary",
                        outline=False,
                        style={'fontSize': '11px', 'padding': '4px 12px', 'fontWeight': '700', 'backgroundColor': '#2563eb', 'borderColor': '#2563eb'}
                    ),
                    # 2. Evidence (triggers right panel switch to Evidence tab)
                    dbc.Button(
                        [html.Span("📁 "), "Evidence"],
                        id="bottom-nav-btn-evidence",
                        size="sm",
                        color="info",
                        outline=True,
                        style={'fontSize': '11px', 'padding': '4px 12px', 'fontWeight': '700', 'borderColor': '#38bdf8', 'color': '#38bdf8'}
                    ),
                    # 3. Reports
                    dbc.Button(
                        [html.Span("📋 "), "Reports"],
                        id="ws-sec-nav-reports",
                        size="sm",
                        color="secondary",
                        outline=True,
                        style={'fontSize': '11px', 'padding': '4px 12px', 'fontWeight': '600', 'borderColor': '#4a5568', 'color': '#cbd5e0'}
                    ),
                    # 4. Audit
                    dbc.Button(
                        [html.Span("🛡️ "), "Audit"],
                        id="ws-sec-nav-audit",
                        size="sm",
                        color="secondary",
                        outline=True,
                        style={'fontSize': '11px', 'padding': '4px 12px', 'fontWeight': '600', 'borderColor': '#4a5568', 'color': '#cbd5e0'}
                    ),
                    html.Span("|", style={'color': '#2a3447', 'margin': '0 4px'}),
                    # Supplementary quick actions
                    dbc.Button(
                        "💸 Money Flow",
                        id="ws-sec-nav-financial",
                        size="sm",
                        color="success",
                        outline=True,
                        style={'fontSize': '10.5px', 'padding': '3px 9px', 'fontWeight': '600'}
                    ),
                    dbc.Button(
                        "📅 Timeline",
                        id="ws-sec-nav-timeline",
                        size="sm",
                        color="warning",
                        outline=True,
                        style={'fontSize': '10.5px', 'padding': '3px 9px', 'fontWeight': '600'}
                    ),
                    dbc.Tooltip("Launch analytical workflows, community detection & GNN inference", target="ws-sec-nav-actions", placement="top"),
                    dbc.Tooltip("Open evidentiary exhibits & source documents in right rail", target="bottom-nav-btn-evidence", placement="top"),
                    dbc.Tooltip("Generate court-ready non-repudiable case dossier reports", target="ws-sec-nav-reports", placement="top"),
                    dbc.Tooltip("Inspect tamper-evident SHA-256 chain of custody audit log", target="ws-sec-nav-audit", placement="top"),
                    dbc.Tooltip("Analyze financial transactions and Hawala structuring", target="ws-sec-nav-financial", placement="top"),
                    dbc.Tooltip("View chronological timeline of case events and telecommunications", target="ws-sec-nav-timeline", placement="top"),
                ]
            ),
            html.Div(
                style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'},
                children=[
                    html.Span("🔒 Non-repudiation audit trail active", style={'color': '#718096', 'fontSize': '10px', 'fontStyle': 'italic'}),
                ]
            )
        ]
    )


def build_case_workspace_toolbar():
    """Case-Specific Investigation Workspace interactive toolbar."""
    return html.Div(
        id='case-workspace-toolbar',
        style={
            'backgroundColor': '#1a202c',
            'border': '1px solid #2d3748',
            'borderRadius': '6px',
            'padding': '10px 14px',
            'marginBottom': '10px',
            'display': 'flex',
            'flexDirection': 'column',
            'gap': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.25)'
        },
        children=[
            # Top row: Quick Entity Search & Filters
            html.Div(
                style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'flexWrap': 'wrap'},
                children=[
                    html.Div(
                        style={'flex': '1.3', 'minWidth': '220px'},
                        children=[
                            dcc.Dropdown(
                                id='ws-search-entity-dropdown',
                                placeholder='🔍 Search & select entity in case...',
                                options=[],
                                clearable=True,
                                style={'color': '#1a202c', 'fontSize': '12px'}
                            )
                        ]
                    ),
                    html.Div(
                        style={'flex': '1', 'minWidth': '180px'},
                        children=[
                            dcc.Dropdown(
                                id='ws-filter-entity-type',
                                placeholder='Filter Entity Types...',
                                options=[
                                    {'label': '👤 Person', 'value': 'person'},
                                    {'label': '📱 Phone', 'value': 'phone'},
                                    {'label': '🚗 Vehicle', 'value': 'vehicle'},
                                    {'label': '📍 Location', 'value': 'location'},
                                    {'label': '🏢 Organization', 'value': 'organization'},
                                    {'label': '💳 Account', 'value': 'account'},
                                    {'label': '💼 Case', 'value': 'case'},
                                    {'label': '📅 Event', 'value': 'event'},
                                ],
                                multi=True,
                                style={'color': '#1a202c', 'fontSize': '12px'}
                            )
                        ]
                    ),
                    html.Div(
                        style={'flex': '1.1', 'minWidth': '190px'},
                        children=[
                            dcc.Dropdown(
                                id='ws-filter-modality',
                                placeholder='Filter Modality...',
                                options=[
                                    {'label': 'All Modalities', 'value': 'ALL'},
                                    {'label': '🟢 Observed Fact (CDR/Direct)', 'value': 'OBSERVED'},
                                    {'label': '🟣 Extracted (Document NLP)', 'value': 'EXTRACTED'},
                                    {'label': '🟡 Predicted (AI Link)', 'value': 'PREDICTED'},
                                    {'label': '🔵 Inferred (Reasoning/Rules)', 'value': 'INFERRED'},
                                ],
                                value='ALL',
                                clearable=False,
                                style={'color': '#1a202c', 'fontSize': '12px'}
                            )
                        ]
                    ),
                    html.Div(
                        style={'flex': '0.9', 'minWidth': '160px'},
                        children=[
                            dcc.Dropdown(
                                id='ws-filter-acceptance',
                                placeholder='Acceptance Status...',
                                options=[
                                    {'label': 'All Relationships', 'value': 'ALL'},
                                    {'label': '✅ Confirmed Only', 'value': 'CONFIRMED'},
                                    {'label': '⏳ Proposed (Review)', 'value': 'PROPOSED'},
                                ],
                                value='ALL',
                                clearable=False,
                                style={'color': '#1a202c', 'fontSize': '12px'}
                            )
                        ]
                    ),
                ]
            ),
            # Middle row: Graph Exploration Tools: N-Hop, Shortest Path, Neighbors, Labels, Highlights
            html.Div(
                style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'flexWrap': 'wrap', 'justifyContent': 'space-between'},
                children=[
                    # N-Hop exploration
                    html.Div(
                        style={'display': 'flex', 'alignItems': 'center', 'gap': '6px'},
                        children=[
                            html.Span("N-Hop:", style={'color': '#a0aec0', 'fontSize': '11px', 'fontWeight': '700'}),
                            dbc.ButtonGroup(size='sm', children=[
                                dbc.Button("1-Hop", id="ws-btn-nhop-1", outline=True, color="primary", style={'fontSize': '11px', 'padding': '2px 8px'}),
                                dbc.Button("2-Hop", id="ws-btn-nhop-2", outline=True, color="primary", style={'fontSize': '11px', 'padding': '2px 8px'}),
                                dbc.Button("3-Hop", id="ws-btn-nhop-3", outline=True, color="primary", style={'fontSize': '11px', 'padding': '2px 8px'}),
                            ]),
                            dbc.Button("Expand Neighbors", id="ws-btn-expand-neighbors", size="sm", color="secondary", outline=True, style={'fontSize': '11px', 'padding': '2px 8px'}),
                            dbc.Button("Restore View", id="ws-btn-reset-view", size="sm", color="secondary", outline=True, style={'fontSize': '11px', 'padding': '2px 8px'}),
                        ]
                    ),
                    # Shortest Path controls
                    html.Div(
                        style={'display': 'flex', 'alignItems': 'center', 'gap': '6px'},
                        children=[
                            html.Span("Shortest Path:", style={'color': '#a0aec0', 'fontSize': '11px', 'fontWeight': '700'}),
                            dcc.Dropdown(
                                id='ws-path-source',
                                placeholder='Source...',
                                options=[],
                                style={'minWidth': '130px', 'color': '#1a202c', 'fontSize': '11px'}
                            ),
                            html.Span("➔", style={'color': '#718096', 'fontSize': '12px'}),
                            dcc.Dropdown(
                                id='ws-path-target',
                                placeholder='Target...',
                                options=[],
                                style={'minWidth': '130px', 'color': '#1a202c', 'fontSize': '11px'}
                            ),
                            dbc.Button("Trace Path", id="ws-btn-find-path", size="sm", color="info", style={'fontSize': '11px', 'padding': '2px 8px', 'fontWeight': '600'}),
                        ]
                    ),
                    # Label controls
                    html.Div(
                        style={'display': 'flex', 'alignItems': 'center', 'gap': '6px'},
                        children=[
                            html.Span("Labels:", style={'color': '#a0aec0', 'fontSize': '11px', 'fontWeight': '700'}),
                            dcc.RadioItems(
                                id='ws-label-mode',
                                options=[
                                    {'label': ' Name', 'value': 'name'},
                                    {'label': ' Name+Type', 'value': 'name_type'},
                                    {'label': ' None', 'value': 'none'}
                                ],
                                value='name',
                                inline=True,
                                style={'color': '#cbd5e0', 'fontSize': '11px', 'display': 'flex', 'gap': '6px'}
                            )
                        ]
                    ),
                    # Analysis highlights
                    html.Div(
                        style={'display': 'flex', 'alignItems': 'center', 'gap': '6px'},
                        children=[
                            dbc.Button("💸 Money Flow", id="ws-btn-money-flow-toolbar", size="sm", color="success", outline=True, style={'fontSize': '11px', 'padding': '2px 8px', 'fontWeight': '700'}),
                            dbc.Button("Highlight Bridges", id="ws-btn-highlight-bridges", size="sm", color="warning", outline=True, style={'fontSize': '11px', 'padding': '2px 8px'}),
                            dbc.Button("Highlight Predicted", id="ws-btn-highlight-predicted", size="sm", color="warning", outline=True, style={'fontSize': '11px', 'padding': '2px 8px'}),
                            dbc.Button("Clear Highlight", id="ws-btn-clear-highlights", size="sm", color="light", outline=True, style={'fontSize': '11px', 'padding': '2px 8px'}),
                        ]
                    ),
                ]
            ),
            # Bottom row: Modality Legend Bar
            html.Div(
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'gap': '14px',
                    'fontSize': '11px',
                    'color': '#cbd5e0',
                    'borderTop': '1px solid #2d3748',
                    'paddingTop': '6px',
                    'flexWrap': 'wrap'
                },
                children=[
                    html.B("EVIDENTIARY MODALITY:", style={'fontSize': '10px', 'color': '#a0aec0', 'letterSpacing': '0.5px'}),
                    html.Span([html.Span("―", style={'color': '#10b981', 'fontWeight': '900', 'fontSize': '14px', 'marginRight': '4px'}), "Observed Fact (CDR/Direct)"], style={'display': 'flex', 'alignItems': 'center'}),
                    html.Span([html.Span("―", style={'color': '#8b5cf6', 'fontWeight': '900', 'fontSize': '14px', 'marginRight': '4px'}), "Extracted (FIR / Document NLP)"], style={'display': 'flex', 'alignItems': 'center'}),
                    html.Span([html.Span("- -", style={'color': '#f59e0b', 'fontWeight': '900', 'fontSize': '14px', 'marginRight': '4px'}), "Predicted (AI Link Prediction)"], style={'display': 'flex', 'alignItems': 'center'}),
                    html.Span([html.Span("·····", style={'color': '#06b6d4', 'fontWeight': '900', 'fontSize': '14px', 'marginRight': '4px'}), "Inferred (Reasoning / Rules)"], style={'display': 'flex', 'alignItems': 'center'}),
                    html.Span("🔒 Unaccepted AI edges are PROPOSED and never sent to Neo4j until investigator validates.", style={'marginLeft': 'auto', 'color': '#718096', 'fontSize': '10px', 'fontStyle': 'italic'}),
                ]
            ),
            # Tooltips for toolbar controls
            dbc.Tooltip("Search entities by name, phone number, vehicle plate, or account ID", target="ws-search-entity-dropdown", placement="top"),
            dbc.Tooltip("Filter visible nodes by entity category (Person, Phone, Vehicle...)", target="ws-filter-entity-type", placement="top"),
            dbc.Tooltip("Filter visible links by evidentiary modality standard", target="ws-filter-modality", placement="top"),
            dbc.Tooltip("Filter relationships by human investigator validation state", target="ws-filter-acceptance", placement="top"),
            dbc.Tooltip("Filter network to immediate 1-hop connections of active entity", target="ws-btn-nhop-1", placement="bottom"),
            dbc.Tooltip("Expand to 2-hop radius to discover secondary intermediaries", target="ws-btn-nhop-2", placement="bottom"),
            dbc.Tooltip("Expand to 3-hop radius to reveal broader syndicate perimeter", target="ws-btn-nhop-3", placement="bottom"),
            dbc.Tooltip("Expand all direct neighbors of currently selected entity", target="ws-btn-expand-neighbors", placement="bottom"),
            dbc.Tooltip("Restore full case network and clear visual focus isolate", target="ws-btn-reset-view", placement="bottom"),
            dbc.Tooltip("Calculate shortest forensic path between selected source and target", target="ws-btn-find-path", placement="bottom"),
            dbc.Tooltip("Analyze and trace illicit financial money flows", target="ws-btn-money-flow-toolbar", placement="bottom"),
            dbc.Tooltip("Highlight critical broker nodes and structural cut-vertices", target="ws-btn-highlight-bridges", placement="bottom"),
            dbc.Tooltip("Highlight proposed AI link prediction hypotheses", target="ws-btn-highlight-predicted", placement="bottom"),
            dbc.Tooltip("Clear all active highlight overlays", target="ws-btn-clear-highlights", placement="bottom"),
        ]
    )


def init_layout(style, dataset_list, external_dataset_list= []):
    """
    The whole layout needed to initialize a Dash app.
    Unified Cockpit:
      • Pinned Top Area: CASE selector + [Ask CrimeNet...] query bar
      • Left Rail (300px): [NETWORK] [ANALYSIS] [INTELLIGENCE]
      • Central Stage (Flex-1): Cytoscape Graph + Secondary Navigation (Analysis, Evidence, Reports, Audit)
      • Right Rail (380px): Dedicated 6-Tab Intelligence Panel (AI Intel, Dossier, Hidden Links, Alerts, Evidence, Timeline)
    :return: Layout for Dash app.
    """
    workspace_content = html.Div(
        id='crimenet-workspace-cockpit',
        style={
            'display': 'flex',
            'flexDirection': 'row',
            'height': 'calc(100vh - 110px)',
            'width': '100%',
            'overflow': 'hidden',
            'backgroundColor': '#0c0f17',
            'boxSizing': 'border-box',
        },
        children=[
            dcc.Store(id='inspected-edge-store', data=None),

            # ── 1. LEFT RAIL: NETWORK, ANALYSIS, INTELLIGENCE TABS ──────────
            html.Div(
                id='sidebar',
                className='workspace-left-rail',
                style={
                    'width': '290px',
                    'minWidth': '270px',
                    'maxWidth': '320px',
                    'height': '100%',
                    'overflowY': 'auto',
                    'backgroundColor': '#131722',
                    'borderRight': '1px solid #2a3447',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'boxSizing': 'border-box',
                    'padding': '8px 10px',
                },
                children=[
                    dcc.Tabs(
                        id='tabs',
                        value='tab-network',
                        parent_className='crimenet-tabs-parent',
                        className='crimenet-tabs-bar',
                        content_className='crimenet-tabs-content',
                        children=[
                            dcc.Tab(label='NETWORK', className='tab', id='network-tab', value='tab-network', children=[
                                html.Div(className='input-div', children=[
                                    dcc.Dropdown(id='choose-network', className='inputs',
                                                 options=dash_formatter.dash_dataset_options(external_dataset_list, dataset_list),
                                                 placeholder='Select network ...'),
                                    dcc.Dropdown(className='inputs', id='choose-entities',
                                                 options=[],
                                                 placeholder="Select entities ...",
                                                 multi=True),
                                    html.Button('Load Network', className='inputs', id='load-network-button', n_clicks=0),
                                    dcc.Upload(
                                        id='upload',
                                        className='inputs crimenet-upload-wrapper',
                                        children=html.Button('Upload CSV / File', className='inputs', id='upload-button'),
                                        multiple=False
                                    ),
                                    html.Button('Load From File', className='inputs',
                                                id='load-file-button', n_clicks=0),
                                    html.Hr(),
                                    html.A(html.Button('Save Network State', id='save-network-button', className='inputs'),
                                           id='download-link', href='/downloadNetwork', download='network_state.json', className='inputs'),
                                    html.A(html.Button('Export Network', id='export-network-button', className='inputs'),
                                           id='export-link', href='/exportNetwork', download='network_export.json', className='inputs'),
                                    html.Hr(),
                                    html.Button('Export Image', className='inputs', id='export-image-button', n_clicks=0),
                                    html.Hr()
                                ])
                            ]),
                            dcc.Tab(label='ANALYSIS', className='tab', id='analysis-tab', value='tab-analysis', children=[
                                html.Div(className='input-div', id="analysis-input", children=[
                                    dcc.Dropdown(className='inputs',
                                                 id='choose-analysis',
                                                 placeholder='Choose analysis function...',
                                                 options=dash_formatter.dash_analysis_options(),
                                                 multi=False),
                                    dcc.Dropdown(className='inputs',
                                                 id='analysis-algorithm',
                                                 placeholder='Choose algorithm...',
                                                 options=[],
                                                 multi=False),
                                    html.Div(className='inputs', id='parameter-div', children=[
                                        html.Div(id='parameter-title', children='PARAMETER'),
                                        dcc.Dropdown(className='parameter',
                                                     id='parameter-1',
                                                     placeholder='Select algorithm first ...',
                                                     options=[],
                                                     value=None,
                                                     multi=False,
                                                     disabled=True)
                                    ]),
                                    html.Div(className='inputs', id='analysis-scope-div', children=[
                                        html.Div('EXECUTION SCOPE', id='analysis-scope-title', style={'fontSize': '10px', 'fontWeight': 'bold', 'color': '#a0aec0', 'letterSpacing': '0.5px', 'marginBottom': '4px'}),
                                        dcc.Dropdown(
                                            id='analysis-scope',
                                            className='parameter',
                                            placeholder='Select scope...',
                                            options=[
                                                {'label': '🌐 Full Network', 'value': 'FULL_NETWORK'},
                                                {'label': '🎯 Selected Entity', 'value': 'SELECTED_ENTITY'},
                                                {'label': '🕸️ Selected Subgraph', 'value': 'SELECTED_SUBGRAPH'},
                                                {'label': '🔗 Selected Pair', 'value': 'SELECTED_PAIR'},
                                            ],
                                            value='FULL_NETWORK',
                                            clearable=False,
                                            multi=False
                                        ),
                                    ]),
                                    html.Div(style={'marginTop': '8px', 'marginBottom': '8px', 'padding': '6px 10px', 'backgroundColor': '#1e293b', 'borderRadius': '4px', 'border': '1px solid #334155'}, children=[
                                        dcc.Checklist(
                                            id='save-analysis-to-case',
                                            options=[{'label': ' 💾 Save Run to Case Record', 'value': 'SAVE'}],
                                            value=['SAVE'],
                                            style={'fontSize': '11px', 'color': '#cbd5e0', 'fontWeight': '500', 'cursor': 'pointer'}
                                        )
                                    ]),
                                    html.Button('Analyze', className='inputs', id='analysis-button', n_clicks=0),
                                    html.Div(id='analysis-summary', className='analysis-summary-box'),
                                    html.Div(id='hierarchical-tree-data', style={'display': 'none'}),
                                    html.Div(id='hierarchical-tree-view-wrapper', className='hierarchical-tree-wrapper'),
                                    html.Hr()
                                ])
                            ]),
                            dcc.Tab(label='INTELLIGENCE', className='tab', id='intelligence-tab', value='tab-intelligence', children=[
                                html.Div(id='unbound-panel-wrapper', children=[
                                    html.Div(id='unbound-insights-panel', children=[
                                        html.Div('CrimeNet AI Intelligence Initializing...',
                                                 style={'padding': '20px', 'color': '#999', 'textAlign': 'center', 'fontSize': '12px'})
                                    ])
                                ])
                            ])
                        ]
                    ),
                    html.Div(id='info-wrapper', style={'marginTop': '10px'}, children=[
                        html.Div(id='info-table-div', className='element-interaction-div', children=[
                            html.Table(
                                id='info-table',
                                className='element-interaction-table',
                                children=[
                                    html.Tr(children=[
                                        html.Th('VARIABLE'),
                                        html.Th('VALUE'),
                                        html.Th('SHOW'),
                                    ])
                            ])
                        ]),
                        html.Div(id='evidence-inspector-card', style={'marginTop': '10px'}),
                        html.Div(id='network-info'),
                    ]),
                    html.A(html.Button('User Documentation', className='inputs', id='documentation-button', style={'marginTop': 'auto'}),
                           target="_blank", rel="noopener noreferrer", href='/userDocumentation', className='inputs'),
                ]
            ),

            # ── 2. CENTER STAGE: CENTRAL CYTOSCAPE GRAPH & TOOLBARS ──────────
            html.Div(
                id='main',
                className='workspace-center-stage',
                style={
                    'flex': '1 1 0%',
                    'minWidth': '420px',
                    'height': '100%',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'backgroundColor': '#0a0d14',
                    'overflow': 'hidden',
                    'position': 'relative',
                    'boxSizing': 'border-box',
                },
                children=[
                    # Workspace Investigation Toolbar
                    build_case_workspace_toolbar(),

                    # Central Graph Canvas
                    html.Div(
                        id='cytoscape-stage-wrapper',
                        style={'flex': '1 1 0%', 'width': '100%', 'position': 'relative', 'overflow': 'hidden'},
                        children=[
                            # Floating Graph Viewport Controls
                            html.Div(
                                className='graph-viewport-controls',
                                children=[
                                    html.Button("⛶ Fit", id="btn-cyto-fit", className="graph-viewport-btn"),
                                    html.Button("➕", id="btn-cyto-zoom-in", className="graph-viewport-btn"),
                                    html.Button("➖", id="btn-cyto-zoom-out", className="graph-viewport-btn"),
                                    html.Button("🎯 Center", id="btn-cyto-center-selected", className="graph-viewport-btn"),
                                    html.Button("🔄 Re-layout", id="btn-cyto-relayout", className="graph-viewport-btn"),
                                ]
                            ),
                            dbc.Tooltip("Fit full syndicate graph into active viewport", target="btn-cyto-fit", placement="bottom"),
                            dbc.Tooltip("Zoom in network view", target="btn-cyto-zoom-in", placement="bottom"),
                            dbc.Tooltip("Zoom out network view", target="btn-cyto-zoom-out", placement="bottom"),
                            dbc.Tooltip("Center viewport on selected focal entity", target="btn-cyto-center-selected", placement="bottom"),
                            dbc.Tooltip("Re-execute force-directed physics layout", target="btn-cyto-relayout", placement="bottom"),

                            dcc.Loading(
                                id='loading-cytoscape',
                                type='dot',
                                color='#38bdf8',
                                children=[
                                    cyto.Cytoscape(
                                        className='four coloums cytoscape-unaltered-hidden',
                                        id='cytoscape-unaltered',
                                        stylesheet=style.stylesheet,
                                        layout={'name': 'cose-bilkent'},
                                        elements=[],
                                        responsive=True,
                                        minZoom=0.2,
                                        maxZoom=2.2,
                                    ),
                                    cyto.Cytoscape(
                                        className='cytoscape',
                                        id='cytoscape',
                                        stylesheet=style.stylesheet,
                                        layout={'name': 'cose-bilkent'},
                                        elements=[],
                                        responsive=True,
                                        minZoom=0.2,
                                        maxZoom=2.2,
                                        style={'width': '100%', 'height': '100%', 'backgroundColor': '#0a0d14'}
                                    ),
                                ]
                            )
                        ]
                    ),

                    # Bottom secondary navigation: [Analysis] [Evidence] [Reports] [Audit]
                    build_workspace_secondary_nav(),

                    # Hidden elements for callback support
                    html.Div(id="original_network_button_div", hidden=True, children=[
                        dbc.Button('Open Original Network', id='unaltered-collapse-button', className="interaction-button")
                    ]),
                    html.Div(id='element-interaction-container', hidden=True, children=[
                        html.Div(id='node-interaction-div', className='element-interaction-div', children=[
                            html.Div('NODES', className='element-interaction-title'),
                            html.Table(id='node-interaction-table', className='element-interaction-table', children=[
                                html.Tr(children=[html.Th('TYPE'), html.Th('SHOW'), html.Th('HIGHLIGHT')])
                            ])
                        ]),
                        html.Div(id='edge-interaction-div', className='element-interaction-div', children=[
                            html.Div('EDGES', className='element-interaction-title'),
                            html.Table(id='edge-interaction-table', className='element-interaction-table', children=[
                                html.Tr(children=[html.Th('TYPE'), html.Th('SHOW'), html.Th('HIGHLIGHT')])
                            ])
                        ]),
                        html.Div(id='label-interaction-div', className='element-interaction-div', children=[
                            html.Div('LABELS', className='element-interaction-title'),
                            html.Table(id='label-interaction-table', className='element-interaction-table', children=[
                                html.Tr(children=[html.Th('VARIABLE', className="label-variable"), html.Th('DISPLAY')])
                            ])
                        ])
                    ]),
                    html.Div(id='edge-prop-slider-div', hidden=True, children=[
                        html.P(id='edge-prop-label', children=['Set edge probability threshold:']),
                        dcc.Slider(id='edge-prob-slider', min=0, max=1, value=0.00, step=0.05,
                                   updatemode='drag',
                                   marks={0.00: '0.00', 0.25: '0.25', 0.50: '0.50', 0.75: '0.75', 1.00: '1.00'}),
                    ]),
                    html.Div(id='warning-div', children=[]),
                    html.Div(id='search-div', hidden=True, children=[
                        dbc.Button('Search', className='interaction-button', id='filter-button', disabled=False)
                    ]),
                    dbc.Tooltip("Search and filter network elements", id="search-tooltip", target="filter-button"),
                    html.Div(id='interaction-div', hidden=True, children=[
                        dbc.Button('Test Button', className='interaction-button', id='test-button', style={'display': 'none'}),
                        dbc.Button('Edit Element', className='interaction-button', id='open-edit-element'),
                        dbc.Button('Add Element', className='interaction-button', id='open-add-element'),
                        dbc.Button('Delete Elements', className='interaction-button', id='open-delete-element'),
                        dbc.Button('Merge Elements', className='interaction-button', id='open-merge-element'),
                        dbc.Button('Exclude Elements', className='interaction-button', id='exclude-button'),
                        dbc.Button('Clear View', className='interaction-button', id='isolate-button'),
                        dbc.Button('Show All Nodes', className='interaction-button', id='show-all-button'),
                        dbc.Button('Expand All Nodes', className='interaction-button', id='expand-all-button'),
                        dbc.Button('Expand Node(s)', className='node-buttons', id='expand-button')
                    ])
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
                    'backgroundColor': '#131722',
                    'borderLeft': '1px solid #2a3447',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'boxSizing': 'border-box',
                },
                children=[
                    build_right_side_panel()
                ]
            )
        ]
    )

    return html.Div(id='crimenet-root-app', style={'backgroundColor': '#0c0f17', 'minHeight': '100vh', 'overflow': 'hidden'}, children=[
        dcc.Store(id='active-case-store', storage_type='session', data=None),
        dcc.Store(id='dossier-active-case-id-store', storage_type='session', data=None),
        # 1. Top CASE Bar
        build_global_nav_bar(),
        # 2. Top [Ask CrimeNet...] Query Bar
        build_top_ask_crimenet_bar(),
        # 3. Main Central Investigation Cockpit
        html.Div(
            id='workspace-view',
            style={'display': 'block', 'height': 'calc(100vh - 105px)', 'overflow': 'hidden'},
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
                            'id': 'remove-element-name'
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
                            'id': 'remove-element-name'
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
            dbc.ModalHeader("Loading new network from file...", id='confirm-load2-header'),
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
