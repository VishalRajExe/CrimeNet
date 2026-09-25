from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import os
import sys

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)


from visualizer import dash_formatter
from visualizer.case_dashboard import build_global_nav_bar, build_dashboard_view


def init_layout(style, dataset_list, external_dataset_list= []):
    """
    The whole layout needed to initialize a Dash app.
    :return:  Layout for a Dash app.
    """
    workspace_content = html.Div(children=[
        html.Div(children=[
            html.Div(className='nine columns', id='main', children=[
                html.Div(id="original_network_button_div", hidden=True, children=[
                    dbc.Button('Open Original Network',
                               id='unaltered-collapse-button',
                               className="interaction-button"
                               )
                ]),
                cyto.Cytoscape(
                    className='four coloums cytoscape-unaltered-hidden',
                    id='cytoscape-unaltered',
                    stylesheet=style.stylesheet,
                    layout={'name': 'cose-bilkent'},
                    elements=[],
                    responsive=True,
                    minZoom=0.2,
                    maxZoom=2.2,
                    # autoRefreshLayout=False
                ),
                cyto.Cytoscape(
                    className='nine columns cytoscape',
                    id='cytoscape',
                    stylesheet=style.stylesheet,
                    layout={'name': 'cose-bilkent'},
                    elements=[],
                    responsive=True,
                    minZoom=0.2,
                    maxZoom=2.2,
                    # autoRefreshLayout=False
                ),
                html.Div(id='element-interaction-container', hidden=True, children=[
                    html.Div(id='node-interaction-div', className='element-interaction-div', children=[
                        html.Div('NODES', className='element-interaction-title'),
                        html.Table(
                            id='node-interaction-table',
                            className='element-interaction-table',
                            children=[
                                html.Tr(children=[
                                    html.Th('TYPE'),
                                    html.Th('SHOW'),
                                    html.Th('HIGHLIGHT'),
                                ])
                            ])
                    ]),
                    html.Div(id='edge-interaction-div', className='element-interaction-div', children=[
                        html.Div('EDGES', className='element-interaction-title'),
                        html.Table(
                            id='edge-interaction-table',
                            className='element-interaction-table',
                            children=[
                                html.Tr(children=[
                                    html.Th('TYPE'),
                                    html.Th('SHOW'),
                                    html.Th('HIGHLIGHT'),
                                ])
                            ])
                    ]),
                    html.Div(id='label-interaction-div', className='element-interaction-div', children=[
                        html.Div('LABELS', className='element-interaction-title'),
                        html.Table(
                            id='label-interaction-table',
                            className='element-interaction-table',
                            children=[
                                html.Tr(children=[
                                    html.Th('VARIABLE', className="label-variable"),
                                    html.Th('DISPLAY')
                                ])
                            ])
                    ])
                ]),
                html.Div(id='edge-prop-slider-div', hidden=True, children=[
                    html.P(id='edge-prop-label', children=['Set edge probability threshold:']),
                    dcc.Slider(id='edge-prob-slider', min=0, max=1, value=0.00, step=0.05,
                               updatemode='drag',
                               marks={
                                   0.00: '0.00',
                                   0.25: '0.25',
                                   0.50: '0.50',
                                   0.75: '0.75',
                                   1.00: '1.00',
                               }),
                ]),
                html.Div(id='warning-div', children=[]),
                html.Div(id='search-div', children=[
                    dbc.Button('Search', className='interaction-button', id='filter-button', disabled=False)
                ]),
                dbc.Tooltip(
                    "Search and filter network elements",
                    id="search-tooltip",
                    target="filter-button"
                ),
                html.Div(id='interaction-div', children=[
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
            ]),
            html.Div(className='three columns', id='sidebar', children=[
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
                            html.Button('Export Image', className='inputs', id='export-image-button', n_clicks= 0),
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
                            html.Button('Analyze', className='inputs', id='analysis-button', n_clicks=0),
                            html.Div(id='analysis-summary', className='analysis-summary-box'),
                            html.Div(id='hierarchical-tree-data', style={'display': 'none'}),
                            html.Div(id='hierarchical-tree-view-wrapper', className='hierarchical-tree-wrapper'),
                            html.Hr()
                        ])
                    ]),
                    dcc.Tab(label='INTELLIGENCE', className='tab', id='intelligence-tab', value='tab-intelligence', children=[
                        html.Div(id='unbound-panel-wrapper', children=[
                            # --- Dynamic Intelligence Panel (rendered and maintained by unbound_panel.js) ---
                            html.Div(id='unbound-insights-panel', children=[
                                html.Div('CrimeNet AI Intelligence Initializing...',
                                         style={'padding': '20px', 'color': '#999', 'textAlign': 'center', 'fontSize': '12px'})
                            ])
                        ])
                    ])
                ]),
                html.Div(id='info-wrapper', children=[
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
                    html.Div(id='network-info'),
                ]),
                html.A(html.Button('User Documentation', className='inputs', id='documentation-button'),
                       target="_blank", rel="noopener noreferrer", href='/userDocumentation', className='inputs'),
            ])
        ]),
        html.P(id='hidden-info', children=[]),
        html.Div(id='unbound-intel-trigger', style={'display': 'none'}),
        html.Div(id='modal', className='modal',
                 children=[advanced_search, edit_element, add_element, delete_element, merge_element,
                           add_node, add_edge, export_image, confirm_load, confirm_load2,
                           confirm_file_load, confirm_file_load2])
    ])

    return html.Div(id='crimenet-root-app', children=[
        dcc.Store(id='active-case-store', storage_type='session', data=None),
        dcc.Store(id='dossier-active-case-id-store', storage_type='session', data=None),
        build_global_nav_bar(),
        html.Div(
            id='case-dashboard-view',
            style={'display': 'block'},
            children=[build_dashboard_view()]
        ),
        html.Div(
            id='workspace-view',
            style={'display': 'none'},
            children=[workspace_content]
        ),
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
