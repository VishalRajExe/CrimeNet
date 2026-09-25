#!/usr/bin/env python

import argparse
import os
import sys
import json
import flask
import dash
from dash import html, dcc
import dash_cytoscape as cyto
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

# APPEND PATH TO ROOT TO ENSURE INTERNAL IMPORTS
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

from visualizer.dash_style import Style
from visualizer.dash_layout import init_layout
from storage.builtin_datasets import ActiveNetwork, BuiltinDatasetsManager
from visualizer import dash_formatter, io_utils
from visualizer import dash_io
from visualizer.dash_io import output


# ------------------------------------------------------------------------------------------------- #

# GET LOCATION FOR PATH FINDING
LOCATION = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


# SET UP ARGUMENT PARSER
parser = argparse.ArgumentParser()
parser.add_argument('--data', required=False, help='Path to a folder containing datasets in the visualizers json format.')
parser.add_argument('--debug', required=False, action='store_true', help='Start dash in debug mode.')
parser.add_argument('--host', required=False, help='Set the host adress. Defaults to 0.0.0.0')
args, _ = parser.parse_known_args()


# LOAD EXTERNAL DATASET
EXTERNAL_DATASETS = []
if args.data:
    EXTERNAL_DATASETS = io_utils.get_external_data(args.data)


# INTERNAL DATASETS
DATASETS = [
    {'id': '911_hijackers', 'name': '911 Hijackers', 'path': '{}/datasets/preprocessed/911_hijackers.json'.format(path2root)},
    {'id': 'israel_lea_case1', 'name': 'Isreal Lea Case 1', 'path': '{}/datasets/preprocessed/israel_lea_case1_speakers.json'.format(path2root)},
    {'id': 'israel_lea_case2', 'name': 'Isreal Lea Case 2', 'path': '{}/datasets/preprocessed/israel_lea_case2_speakers.json'.format(path2root)},
    {'id': 'baseball_steroid_use', 'name': 'Baseball Steorid Use', 'path': '{}/datasets/preprocessed/baseball_steroid_use.json'.format(path2root)},
    {'id': 'bbc_islam_groups', 'name': 'BBC Islam Groups', 'path': '{}/datasets/preprocessed/bbc_islam_groups.json'.format(path2root)},
    {'id': 'csi_s01e07', 'name': 'CSI (s01e07)', 'path': '{}/datasets/preprocessed/csi_indiap_s01e07.json'.format(path2root)},
    {'id': 'csi_s01e08', 'name': 'CSI (s01e08)', 'path': '{}/datasets/preprocessed/csi_indiap_s01e08.json'.format(path2root)},
    {'id': 'madoff', 'name': 'Madoff Frauds', 'path': '{}/datasets/preprocessed/madoff.json'.format(path2root)},
    {'id': 'montreal_gangs', 'name': 'Montreal Street Gangs', 'path': '{}/datasets/preprocessed/montreal_gangs.json'.format(path2root)},
    {'id': 'moreno_crime', 'name': 'Moreno Crime Network', 'path': '{}/datasets/preprocessed/moreno_crime.json'.format(path2root)},
    {'id': 'nist_c1', 'name': 'NIST C1', 'path': '{}/datasets/preprocessed/nist_c1.json'.format(path2root)},
    {'id': 'nist_c2', 'name': 'NIST C2', 'path': '{}/datasets/preprocessed/nist_c2.json'.format(path2root)},
    {'id': 'noordintop', 'name': 'Noordin Top', 'path': '{}/datasets/preprocessed/noordintop.json'.format(path2root)},
    {'id': 'rhodes_bombing', 'name': 'Rhodes Bombing', 'path': '{}/datasets/preprocessed/rhodes_bombing.json'.format(path2root)},
    {'id': 'unbound_case_2026', 'name': 'UNBOUND — Indian Criminal Network 2026', 'path': '{}/datasets/preprocessed/unbound_case_2026.json'.format(path2root)}
]


# DATA INFO USED FOR NETWORK SELECTION DROPDOWN
DATA_INFO = {d['id']: {'path': d['path'], 'name': d['name']} for d in DATASETS + EXTERNAL_DATASETS}


# ADD DATASETS TO DATASET MANAGER
# Technically not all datasets need to be loaded -
# Maybe just load the one set needed for retrieving entities when network is chosen.
builtin_datasets = BuiltinDatasetsManager(connector=None, params=None)
for ds in DATASETS:
    builtin_datasets.add_dataset(ds['id'], ds['name'], ds['path'])
for ds in EXTERNAL_DATASETS:
    builtin_datasets.add_dataset(ds['id'], ds['name'], ds['path'])


# LAYOUT USED FOR CYTOSCAPE VISUALIZATION
# Used cola before - cola has problems with positioning after resizing the frame
ACTIVE_LAYOUT = {'name': 'cose-bilkent',
                 'randomize': 'false',
                 'refresh': 3,
                 'maxSimulationTime': 5000, # Default: 400s
                 }


# DISABLED ANALYSIS METHODS
DISABLED_ANALYSIS_METHODS = ['authority', 'count_number_soundarajan_hopcroft',
                             'resource_allocation_index_soundarajan_hopcroft',
                             'within_inter_cluster']


# INITIALIZE DASH/CYTOSCAPE
style = Style(file=os.path.join(LOCATION, 'assets/cyto_style.json'))
cyto.load_extra_layouts()
active_network = None
visualizer_app = dash.Dash(__name__, suppress_callback_exceptions=True, title='CrimeNet')
layout = init_layout(style=style, dataset_list=DATASETS, external_dataset_list=EXTERNAL_DATASETS)


# GLOBAL VARIABLES
network_properties = {}
labels = []


def resolve_selected_entities(entities):
    """
    Returns None if entities is empty or contains a select-all sentinel value,
    indicating the complete network should be loaded.
    """
    if not entities:
        return None
    if any(e in ('__all__', 'all', 'select_all', 'all_entities') for e in entities):
        return None
    return entities


# ------------------------------------------------------------------------------------------------- #


# MAIN CALLBACK CONTAINING MOST INTERACTIONS WITH THE APP
# Can not have several callbacks to the same output. Thus, one big callback function
# is needed so that different inputs can change the same objects (eg. the elements).
@visualizer_app.callback(
    # Located all outputs, inputs and states in dash_io module to keep main file cleaner
    dash_io.outputs,
    dash_io.inputs,
    dash_io.states
)
def main_callback(*args):

    # Use code below instead of input_names to automatically use component names.
    # Would be the cleanest approach but requires changing all input names used in this file accordingly.

    # input_names = [item.component_id for item in in_out_utils.inputs + in_out_utils.states]
    # cleaned_input_names = []
    # for name in input_names:
    #     if isinstance(name, dict):
    #         cleaned_input_names.append(name['type'])
    #     else:
    #         cleaned_input_names.append(name)


    # Map callback arguments to input names
    callback_kwargs = dict(zip(dash_io.input_names, args))


    # Context contains component ID and component value at context.triggered[0]['prop_id']
    # in this form: 'component_id.component_value'.  Context can be used to run specific
    # code only for specific input events.
    context = dash.callback_context

    # GLOBAL VARIABLES
    global active_network
    global style
    global network_properties
    global labels


    #####################
    ## CYTOSCAPE FRAME ##
    #####################

    if context.triggered[0]['prop_id'].split('.')[0] == 'unaltered-collapse-button':
        try:
            if not callback_kwargs['unaltered_collapse_button_clicks']:
                return output()
            elif callback_kwargs['unaltered_collapse_button_clicks'] % 2 == 1:  # open
                text = "Opened original network frame."
                visualizer_app.logger.info(text)
                message = dash_formatter.dash_message(text, success=True)
                return output(cytoscape_class='five columns cytoscape-small', collapse_button_text="Close Original Network",
                              hide_interaction_checkboxes=True, hide_prob_slider=True, message=message)
            else:  # close
                hide_prob_slider = True
                for e in active_network.edges:
                    if e:
                        if 'probability' in e['properties']:
                            hide_prob_slider = False
                text = "Closed original network frame."
                visualizer_app.logger.info(text)
                message = dash_formatter.dash_message(text, success=True)
                return output(cytoscape_class='six columns cytoscape', collapse_button_text="Open Original Network",
                             hide_interaction_checkboxes=False, hide_prob_slider=hide_prob_slider, message=message)
        except Exception:
            text = "An error occurred while trying to open original network frame."
            visualizer_app.logger.exception(text)
            message = dash_formatter.dash_message(text, success=False)
            return output(message=message)


    ### NODE CLICKED ###
    # When node is clicked: Highlight the node and its neighbors.
    if context.triggered[0]['prop_id'].split('.')[1] == 'tapNodeData':
        try:
            clicked_node = callback_kwargs['clicked_node']
            if not clicked_node:
                raise PreventUpdate

            status = active_network.toggle_node_selection(clicked_node['id'])

            if status == "selected":
                text = "Selected node: {}.".format(clicked_node['id'])
                visualizer_app.logger.info(text)
                message = dash_formatter.dash_message(text, success=True)
            elif status == "unselected":
                text = "Unselected node: {}.".format(clicked_node['id'])
                visualizer_app.logger.info(text)
                message = dash_formatter.dash_message(text, success=True)
            else:
                raise Exception("Unexpected selection status of edge occured")
            return output(elements=active_network.elements, message=message)
        except Exception:
            text = "An error occurred while trying to select following node: {}.".format(clicked_node['id'])
            visualizer_app.logger.exception(text)
            message = dash_formatter.dash_message(text, success=False)
            return output(message=message)


    ### EDGE CLICKED ###
    # When edge is clicked: Highlight the edge and its neighbors.
    elif context.triggered[0]['prop_id'].split('.')[1] == 'tapEdgeData':
        try:
            clicked_edge = callback_kwargs['clicked_edge']
            if clicked_edge['type'] == 'predicted':
                return output()
            if not clicked_edge:
                raise PreventUpdate
            status = active_network.toggle_edge_selection(clicked_edge['id'])

            if status == "selected":
                text = "Selected edge with edge ID {}.".format(clicked_edge['id'])
                visualizer_app.logger.info(text)
                message = dash_formatter.dash_message(text, success=True)
            elif status == "unselected":
                text = "Unselected edge with edge ID {}.".format(clicked_edge['id'])
                visualizer_app.logger.info(text)
                message = dash_formatter.dash_message(text, success=True)
            else:
                raise Exception("Unexpected selection status of edge occured")
            return output(elements=active_network.elements, message=message)
        except Exception:
            text = "An error occurred while trying to select edge with ID {}.".format(clicked_edge['id'])
            visualizer_app.logger.exception(text)
            message = dash_formatter.dash_message(text, success=False)
            return output(message=message)


    ## EDGE PROBABILITY SLIDER ##
    elif context.triggered[0]['prop_id'].split('.')[0] == 'edge-prob-slider':
        try:
            style.set_edge_prob(callback_kwargs['edge_prob_slider_value'])
            text = "Set edge probability treshold to {}".format(callback_kwargs['edge_prob_slider_value'])
            visualizer_app.logger.info(text)
            message = dash_formatter.dash_message(text, success=True)
            return output(stylesheet=style.stylesheet, message=message)
        except Exception:
            text = "An error occured while setting the edge probability threshold"
            visualizer_app.logger.info(text)
            message = dash_formatter.dash_message(text, success=False)
            return output(stylesheet=style.stylesheet, message=message)


    ####################
    ## SIDEBAR INPUTS ##
    ####################

    ##
    ## NETWORK TAB ##
    ##

    ### ADVANCED SEARCH BUTTON ### #
    # When 'Advanced Search' button is pressed: Open Advanced Search Modal.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'filter-button':
        if not active_network or not active_network.elements:
            if not callback_kwargs.get('network_selection'):
                return output(
                    message=dash_formatter.dash_message("Please load a network first to search and filter.", success=False)
                )

        network_properties = {}
        # Collect properties from active_network
        if active_network and getattr(active_network, 'nodes', None):
            for node_id, props in active_network.nodes.items():
                if isinstance(props, dict):
                    for key, val in props.items():
                        if key not in network_properties:
                            network_properties[key] = set()
                        if val is not None and str(val).strip():
                            network_properties[key].add(str(val))
        if active_network and active_network.elements:
            for e in active_network.elements:
                if e.get('group') == 'nodes':
                    info = e.get('data', {}).get('info', {})
                    if isinstance(info, dict):
                        for key, val in info.items():
                            if key not in network_properties:
                                network_properties[key] = set()
                            if val is not None and str(val).strip():
                                network_properties[key].add(str(val))
                    for k in ['id', 'label', 'type']:
                        v = e.get('data', {}).get(k)
                        if v and str(v).strip():
                            if k not in network_properties:
                                network_properties[k] = set()
                            network_properties[k].add(str(v))
        elif callback_kwargs.get('network_selection'):
            nodes = builtin_datasets.search_nodes(node_ids=None, network=callback_kwargs['network_selection'])['found']
            for node in nodes:
                for key in node.get('properties', {}):
                    if key not in network_properties:
                        network_properties[key] = set()
                    val = node['properties'][key]
                    if val is not None and str(val).strip():
                        network_properties[key].add(str(val))

        if not network_properties:
            return output(
                message=dash_formatter.dash_message("No searchable properties found in the current network.", success=False)
            )

        property_options = dash_formatter.dash_type_options(sorted(list(network_properties.keys())))
        filter_container = dash_formatter.init_filters(property_options)
        return output(filter_container=filter_container,
                      search_quick_input="",
                      show_search_dialog=True, grey_background=True)


    ### LOAD NETWORK BUTTON ###
    # When 'Load Network' button is pressed: Load network and initialize drop down menus.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'load-network-button':
        if not callback_kwargs.get('network_selection'):
            message = dash_formatter.dash_message('Please choose a network from the dropdown first.', success=False)
            return output(message=message)
        if not active_network.elements:
            try:
                selected_entities = resolve_selected_entities(callback_kwargs['entities'])
                active_network = ActiveNetwork(path_2_data=DATA_INFO[callback_kwargs['network_selection']]['path'],
                                               initialize=True, selected_nodes=selected_entities,
                                               params={'network_name': DATA_INFO[callback_kwargs['network_selection']]['name']})

                node_table, edge_table, label_table = get_interaction_tables(active_network)
                network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())

                hide_prob_slider = True
                for e in active_network.edges:
                    if 'probability' in e['properties']:
                        hide_prob_slider = False

                style.reset()
                types = active_network.get_active_node_types()
                style.set_type_styles(types)

                if selected_entities:
                    text = "Network {} loaded with following entities: {}.".format(callback_kwargs['network_selection'],
                                                                                   ", ".join(str(e) for e in selected_entities)
                                                                                   )
                else:
                    text = "The complete {} Network was loaded".format(callback_kwargs['network_selection'])
                message = dash_formatter.dash_message(text, success=True)
                visualizer_app.logger.info(text)

                return output(elements=active_network.elements, stylesheet=style.stylesheet,
                              layout=ACTIVE_LAYOUT, elements_unaltered=active_network.elements,
                              stylesheet_unaltered=style.stylesheet, layout_unaltered=ACTIVE_LAYOUT,
                              hide_prob_slider=hide_prob_slider, hide_interaction_checkboxes=False,
                              node_interaction_table=node_table,
                              edge_interaction_table=edge_table,
                              label_interaction_table=label_table, network_info=network_info,
                              analysis_algorithms=[], analysis_parameter=dash_formatter.dash_default_parameter(),
                              analysis_summary="", hierarchical_tree_data="",
                              hide_original_network_button=False, message=message, show_confirm_load=False)

            except Exception:
                if selected_entities:
                    text = "Error loading Network {} with following entities: {}.".format(callback_kwargs['network_selection'],
                                                                                          ", ".join(str(e) for e in selected_entities)
                                                                                          )
                else:
                    text = "Error loading Network {}.".format(callback_kwargs['network_selection'])
                message = dash_formatter.dash_message(text, success=False)
                visualizer_app.logger.exception(text)
                return output(message=message)


        return output(show_confirm_load=True, grey_background=True)


    ### LOAD FROM FILE BUTTON ###
    # When 'Load From File' button is pressed:
    elif context.triggered[0]['prop_id'].split('.')[0] == 'load-file-button':
        return output(elements=[], grey_background=True, show_confirm_file_load=True)



    ### WHEN NETWORK SELECTED ###
    # When network is chosen: Reset current state and load entities of this network
    elif context.triggered[0]['prop_id'].split('.')[0] == 'choose-network':
        try:
            nodes = builtin_datasets.search_nodes(node_ids=None, network=callback_kwargs['network_selection'])['found']
            # Use subset of very big datasets until better/optimised solution for searching entities is implemented.
            if len(nodes) > 14000:
                nodes = nodes[0:14000]
            entity_options = dash_formatter.dash_entity_options(nodes)

            text = "Selected inbuilt network '{}'".format(callback_kwargs['network_selection'])
            message = dash_formatter.dash_message(text, True)
            visualizer_app.logger.info(text)

            return output(entity_options=entity_options, entity_values=[], message=message)
        except Exception:
            text = "An error occured when trying to select inbuilt network '{}'".format(callback_kwargs['network_selection'])
            message = dash_formatter.dash_message(text, False)
            visualizer_app.logger.exception(text)
            return output(message=message)


    ##
    ## ANALYSIS TAB ##
    ##

    ### WHEN ANALYSIS IS CHOOSEN ###
    # When Analysis function is chosen: Load algorithm options for this function.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'choose-analysis':
        if not callback_kwargs['analysis_function']:
            raise PreventUpdate
        else:
            try:
                method_options = dash_formatter.dash_analysis_method_options(callback_kwargs['analysis_function'], DISABLED_ANALYSIS_METHODS)

                text = "Selected following analysis function: '{}'".format(callback_kwargs['analysis_function'])
                message = dash_formatter.dash_message(text, True)
                visualizer_app.logger.info(text)

                return output(analysis_algorithms=method_options, message=message, analysis_summary="", hierarchical_tree_data="")
            except Exception:
                text = "Error occurred selecting following analysis function: '{}'".format(callback_kwargs['analysis_function'])
                message = dash_formatter.dash_message(text, False)
                visualizer_app.logger.exception(text)
                return output(message=message)


    ### ANALYSIS ALGORITHM CHOSEN ###
    # When Analysis algorithm is chosen : Load parameter.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'analysis-algorithm':
        try:
            if callback_kwargs['analysis_algorithm']:
                parameter = dash_formatter.dash_analysis_parameter(callback_kwargs['analysis_function'], callback_kwargs['analysis_algorithm'])
            else:
                parameter = dash_formatter.dash_default_parameter()
            text = "Selected 'following analysis algorithm: {}".format(callback_kwargs['analysis_algorithm'])
            message = dash_formatter.dash_message(text, True)
            visualizer_app.logger.info(text)
            return output(analysis_parameter=parameter, message=message)
        except Exception:
            text = "Error occurred selecting following analysis algorithm: '{}'".format(callback_kwargs['analysis_function'])
            message = dash_formatter.dash_message(text, False)
            visualizer_app.logger.exception(text)
            return output(message=message)



    ### ANALYZE BUTTON ###
    # When 'Analyze' button is pressed: Do and visualize analysis.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'analysis-button':
        try:
            if not callback_kwargs['analysis_function']:
                text = "Could not apply analysis. Please select a analysis function."
                message = dash_formatter.dash_message(text, False)
                visualizer_app.logger.warning(text)
                return output(message=message)
            if not callback_kwargs['analysis_algorithm']:
                text = "Could not apply analysis. Please select a analysis algorithm."
                message = dash_formatter.dash_message(text, False)
                visualizer_app.logger.warning(text)
                return output(message=message)

            fn = callback_kwargs['analysis_function']
            algo = callback_kwargs['analysis_algorithm']
            param1 = callback_kwargs.get('parameter_1')

            analysis_summary_component = None
            hierarchical_tree_json = ""

            if fn == 'link_prediction':
                if not active_network.selected_nodes:
                    text = "Could not apply link prediction. Please select atleast one node to predict links for."
                    message = dash_formatter.dash_message(text, False)
                    visualizer_app.logger.warning(text)
                    return output(message=message)
                active_network.apply_analysis(fn, algo, params={
                    "sources": [], 'community_detection_method': param1})
                text = "Applied link prediction using {}. " \
                       "The 3 most probable links from the selected node(s) are displayed".format(algo)
                analysis_summary_component = ""
                hierarchical_tree_json = ""

            elif fn == 'community_detection':
                params = {}
                if param1:
                    try:
                        params["K"] = int(param1)
                    except (ValueError, TypeError):
                        pass

                active_network.apply_analysis(fn, algo, params=params)
                if getattr(active_network, 'last_analysis_message', None):
                    err_msg = active_network.last_analysis_message
                    message = dash_formatter.dash_message(err_msg, success=False)
                    return output(message=message, analysis_summary="", hierarchical_tree_data="")

                res = getattr(active_network, 'last_community_result', None)
                if not res or res.get('success') == 0:
                    err_msg = "Community detection requires at least 2 connected nodes."
                    message = dash_formatter.dash_message(err_msg, success=False)
                    return output(message=message, analysis_summary="", hierarchical_tree_data="")

                if algo == 'louvain':
                    num_comms = res.get('num_communities', len(res.get('communities', []))) if res else len(set(e.get('data', {}).get('community') for e in active_network.elements if e.get('group') == 'nodes' and e.get('data', {}).get('community') is not None))
                    num_nodes = res.get('nodes_analyzed', len(active_network.active_nodes)) if res else len(active_network.active_nodes)
                    text = f"Communities Detected: {num_comms} | Nodes Analyzed: {num_nodes}"
                    analysis_summary_component = html.Div(className='community-summary-card', children=[
                        html.Div(className='summary-title', children="Community Detection — Louvain"),
                        html.Div(className='summary-grid', children=[
                            html.Div(className='summary-item', children=[
                                html.Span('Communities Detected:', className='summary-label'),
                                html.Span(str(num_comms), className='summary-value')
                            ]),
                            html.Div(className='summary-item', children=[
                                html.Span('Nodes Analyzed:', className='summary-label'),
                                html.Span(str(num_nodes), className='summary-value')
                            ])
                        ])
                    ])
                    hierarchical_tree_json = ""

                elif algo == 'hierarchical':
                    tree = res.get('tree') if res else None
                    stats = res.get('stats', {}) if res else {}
                    total_entities = stats.get('total_entities', len(active_network.active_nodes))
                    total_clusters = stats.get('total_clusters', len(res.get('communities', [])) if res else 0)
                    hierarchy_depth = stats.get('hierarchy_depth', 0)
                    text = f"Hierarchical Clustering Applied — Total Entities: {total_entities} | Total Clusters: {total_clusters} | Hierarchy Depth: {hierarchy_depth}"
                    analysis_summary_component = html.Div(className='community-summary-card', children=[
                        html.Div(className='summary-title', children="Hierarchical Clustering Structure"),
                        html.Div(className='summary-grid', children=[
                            html.Div(className='summary-item', children=[
                                html.Span('Total Entities:', className='summary-label'),
                                html.Span(str(total_entities), className='summary-value')
                            ]),
                            html.Div(className='summary-item', children=[
                                html.Span('Total Clusters:', className='summary-label'),
                                html.Span(str(total_clusters), className='summary-value')
                            ]),
                            html.Div(className='summary-item', children=[
                                html.Span('Hierarchy Depth:', className='summary-label'),
                                html.Span(str(hierarchy_depth), className='summary-value')
                            ])
                        ])
                    ])
                    hierarchical_tree_json = json.dumps(tree) if tree else ""

                else:
                    # Modularity, Label Propagation, etc.
                    num_comms = res.get('num_communities', len(res.get('communities', []))) if res else len(set(e.get('data', {}).get('community') for e in active_network.elements if e.get('group') == 'nodes' and e.get('data', {}).get('community') is not None))
                    num_nodes = res.get('nodes_analyzed', len(active_network.active_nodes)) if res else len(active_network.active_nodes)
                    text = f"Communities Detected: {num_comms} | Nodes Analyzed: {num_nodes}"
                    analysis_summary_component = html.Div(className='community-summary-card', children=[
                        html.Div(className='summary-title', children=f"Community Detection — {algo.replace('_', ' ').title()}"),
                        html.Div(className='summary-grid', children=[
                            html.Div(className='summary-item', children=[
                                html.Span('Communities Detected:', className='summary-label'),
                                html.Span(str(num_comms), className='summary-value')
                            ]),
                            html.Div(className='summary-item', children=[
                                html.Span('Nodes Analyzed:', className='summary-label'),
                                html.Span(str(num_nodes), className='summary-value')
                            ])
                        ])
                    ])
                    hierarchical_tree_json = ""

            else:
                # social_influence_analysis, etc.
                if param1:
                    active_network.apply_analysis(fn, algo, params={"K": int(param1)})
                    text = "Applied {} using {} with the following parameter: K: {}".format(fn, algo, param1)
                else:
                    active_network.apply_analysis(fn, algo, params={})
                    text = "Applied {} using {}.".format(fn, algo)
                analysis_summary_component = ""
                hierarchical_tree_json = ""

            message = dash_formatter.dash_message(text, True)
            visualizer_app.logger.info(text)
            return output(elements=active_network.elements,
                          message=message,
                          analysis_summary=analysis_summary_component,
                          hierarchical_tree_data=hierarchical_tree_json)
        except Exception:
            text = "An error occurred while trying to apply network analysis. Please select a analysis function and algorithm "
            message = dash_formatter.dash_message(text, False)
            visualizer_app.logger.exception(text)
            return output(message=message)


    ##
    ## ELEMENT INTERACTION
    ##

    # TODO: LOGGING
    ### OPEN EDIT ELEMENT ###
    # When 'Edit Element' button is clicked: Open the according dialog.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'open-edit-element':
        selected_nodes = active_network.get_selected_nodes()
        selected_edges = active_network.get_selected_edges()
        all_selected = selected_edges + selected_nodes
        if len(all_selected) != 1:
            message = dash_formatter.dash_message(
                'Editing can only be applied to one element at once. Select exactly one element please.',
                success=False)
            return output(message=message)

        edit_element_container = callback_kwargs['edit_element_container'][:2]

        if selected_nodes:
            ele_index = active_network.active_nodes[selected_nodes[0]]['element_index']
            edit_element_container[1]['props']['options'] = \
                dash_formatter.dash_type_options(active_network.get_active_node_types())
        elif selected_edges:
            ele_index = active_network.active_edges[selected_edges[0]]['element_index']
            edit_element_container[1]['props']['options'] = \
                dash_formatter.dash_type_options(active_network.get_active_edge_types())
        else:
            message = dash_formatter.dash_message(
                'An unexpected error occured ...',
                success=False)
            return output(message=message)

        edit_element_container[1]['props']['value'] = active_network.elements[ele_index]['data']['type']

        ele_info = active_network.elements[ele_index]['data']['info']
        for info_field in ele_info:
            if info_field.lower() != 'type':
                edit_element_container.append(dash_formatter.get_label(info_field))
                edit_element_container.append(
                    dash_formatter.get_text_field(info_field, str(ele_info[info_field]), 'edit'))

        return output(grey_background=True, show_edit_dialog=True,
                      edit_element_container=edit_element_container)


    ### OPEN ADD ELEMENT ###
    # When 'Add Element' button is clicked: Open the according dialog.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'open-add-element':
        # message = dash_formatter.dash_message('Adding elements not available at the moment ...', success=False)
        # return output(message=message)
        visualizer_app.logger.info("Opened Add Element Dialog.")
        return output(grey_background=True, show_add_dialog=True)


    ### OPEN DELETE ELEMENT ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'open-delete-element':
        visualizer_app.logger.info("Opened Delete Element Dialog.")
        return output(grey_background=True, show_delete_dialog=True)

    # TODO: LOGGING
    ### OPEN MERGE ELEMENT ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'open-merge-element':
        selected_nodes = active_network.get_selected_nodes()
        selected_edges= active_network.get_selected_edges()
        if selected_nodes and selected_edges:
            message = dash_formatter.dash_message(
                'Nodes and edges cannot be merged together. Please select only one element type (node/edge).',
                success=False)
            return output(message=message)
        if selected_nodes:
            if len(selected_nodes) < 2:
                message = dash_formatter.dash_message(
                    'Merging can only be applied when at least two elements are selected. '
                    'Only elements of the same type (nodes/edges) can be merged..',
                    success=False)
                return output(message=message)

            ele_index = active_network.active_nodes[selected_nodes[0]]['element_index']

            merge_element_container = callback_kwargs['merge_element_container'][:2]
            merge_element_container[1]['props']['value'] = active_network.elements[ele_index]['data']['type']
            merge_element_container[1]['props']['options'] = \
                dash_formatter.dash_type_options(active_network.get_active_node_types())
            ele_info = active_network.elements[ele_index]['data']['info']
            for info_field in ele_info:
                if info_field.lower() == 'name':
                    name = ''
                    for node in selected_nodes:
                        name += node + '_'
                    name += '_merged'
                    merge_element_container.append(dash_formatter.get_label(info_field))
                    merge_element_container.append(
                        dash_formatter.get_text_field(info_field, name, 'merge'))
                elif info_field.lower() != 'type':
                    merge_element_container.append(dash_formatter.get_label(info_field))
                    merge_element_container.append(
                        dash_formatter.get_text_field(info_field, str(ele_info[info_field]), 'merge'))

            return output(grey_background=True, show_merge_dialog=True,
                          merge_element_container=merge_element_container)
        if selected_edges:
            message = dash_formatter.dash_message(
                'Merging Edges is not possible at the current state.',
                success=False)
            return output(message=message)


    ### EXCLUDE ELEMENTS BUTTON ###
    # When 'Exclude Elements' button is clicked: Hide selected element.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'exclude-button':
        try:
            selected_nodes = active_network.get_selected_nodes()
            selected_edges = active_network.get_selected_edges()
            if not selected_nodes and not selected_edges:
                text = "Could not exclude elements. Please select elements to hide first by clicking them."
                message = dash_formatter.dash_message(text, success=False)
                visualizer_app.logger.warning(text)
                return output(message=message, grey_background=False, show_delete_dialog=False)
            if selected_nodes:
                active_network.deactivate_nodes(selected_nodes)
            if selected_edges:
                active_network.deactivate_edges(selected_edges)
            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())

            text = 'Selected elements are excluded from the network visualization. They can be re-expanded at any time.'
            message = dash_formatter.dash_message(text, success=True)
            visualizer_app.logger.info(text)
            return output(elements=active_network.elements, message=message,
                          grey_background=False, show_delete_dialog=False,
                          network_info=network_info,
                          analysis_summary="", hierarchical_tree_data="")
        except Exception:
            text = "An unexpected error occurred while trying to exclude elements."
            message = dash_formatter.dash_message(text, False)
            visualizer_app.logger.exception(text)
            return output(message=message)


    ### ISOLATE SELECTED BUTTON (CLEAR VIEW) ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'isolate-button':
        try:
            if not active_network or not active_network.elements:
                message = dash_formatter.dash_message("Please load a network first.", success=False)
                return output(message=message)

            selected_nodes = active_network.get_selected_nodes()
            if not selected_nodes:
                message = dash_formatter.dash_message(
                    "Please select one or more nodes first by clicking them to get a clear view.",
                    success=False
                )
                return output(message=message)

            num_nodes, num_edges = active_network.isolate_nodes(selected_nodes)
            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
            node_interaction_table = dash_formatter.get_node_interaction_table()
            edge_interaction_table = dash_formatter.get_edge_interaction_table()
            for node_type in active_network.get_active_node_types():
                node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
            for edge_type in active_network.get_active_edge_types():
                edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))

            num_selected = len(selected_nodes)
            num_linked = num_nodes - num_selected
            if num_linked > 0:
                text = f"Clear view enabled: showing {num_selected} selected node(s), {num_linked} linked node(s), and {num_edges} connection(s). Click 'Show All Nodes' to restore."
            else:
                text = f"Clear view enabled: showing {num_nodes} node(s) and {num_edges} connection(s). Click 'Show All Nodes' to restore."
            message = dash_formatter.dash_message(text, success=True)
            visualizer_app.logger.info(text)
            return output(elements=active_network.elements, network_info=network_info, message=message,
                          node_interaction_table=node_interaction_table, edge_interaction_table=edge_interaction_table,
                          analysis_summary="", hierarchical_tree_data="",
                          layout=ACTIVE_LAYOUT)
        except Exception:
            text = "An unexpected error occurred while trying to isolate selected nodes."
            visualizer_app.logger.exception(text)
            message = dash_formatter.dash_message(text, False)
            return output(message=message)


    ### SHOW ALL NODES BUTTON (RESTORE VIEW) ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'show-all-button':
        try:
            if not active_network or not getattr(active_network, 'nodes', None):
                message = dash_formatter.dash_message("Please load a network first.", success=False)
                return output(message=message)

            num_nodes, num_edges = active_network.restore_full_network()
            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
            node_table, edge_table, label_table = get_interaction_tables(active_network)
            style.reset()
            style.set_type_styles(active_network.get_active_node_types())

            text = f"Restored full network view ({num_nodes} nodes, {num_edges} edges)."
            message = dash_formatter.dash_message(text, success=True)
            visualizer_app.logger.info(text)
            return output(elements=active_network.elements, stylesheet=style.stylesheet,
                          layout=ACTIVE_LAYOUT, network_info=network_info,
                          node_interaction_table=node_table, edge_interaction_table=edge_table,
                          label_interaction_table=label_table,
                          analysis_summary="", hierarchical_tree_data="",
                          message=message)
        except Exception:
            text = "An unexpected error occurred while restoring full network view."
            visualizer_app.logger.exception(text)
            message = dash_formatter.dash_message(text, False)
            return output(message=message)


    ### EXPAND ALL BUTTON ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'expand-all-button':
        try:
            nodes_to_expand = []
            for node in active_network.active_nodes:
                if active_network.active_nodes[node]['expandable']:
                    nodes_to_expand.append(node)
            if nodes_to_expand:
                active_network.expand_nodes(nodes_to_expand)
                network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())

                ## update interaction tables
                node_interaction_table = dash_formatter.get_node_interaction_table()
                edge_interaction_table = dash_formatter.get_edge_interaction_table()
                for node_type in active_network.get_active_node_types():
                    node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
                for edge_type in active_network.get_active_edge_types():
                    edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))

                text = "All expandable nodes were expanded successfully."
                message = dash_formatter.dash_message(text, success=True)
                visualizer_app.logger.info(text)

                return output(elements=active_network.elements, network_info=network_info, message=message,
                              node_interaction_table=node_interaction_table, edge_interaction_table=edge_interaction_table,
                              analysis_summary="", hierarchical_tree_data="")
            else:
                text = "No nodes were expanded. There are no expandable nodes in the network."
                message = dash_formatter.dash_message(text, success=False)
                visualizer_app.logger.warning(text)
                return output(message=message)
        except Exception:
            text = "An unexpected error occurred while trying to expand all expandable nodes."
            message = dash_formatter.dash_message(text, False)
            visualizer_app.logger.exception(text)
            return output(message=message)


    ### EXPAND BUTTON ###
    # When 'Expand Nodes' button in clicked: Expand the currently selected nodes.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'expand-button':
        message = dash_formatter.dash_message('Select nodes to expand ...', success=False)
        selected_nodes = active_network.get_selected_nodes()
        if selected_nodes:
            success, message = active_network.expand_nodes(selected_nodes)
            if success:
                message = dash_formatter.dash_message('Node(s) succesfully expanded.', success=True)
                network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())

                ## update interaction tables
                node_interaction_table = dash_formatter.get_node_interaction_table()
                edge_interaction_table = dash_formatter.get_edge_interaction_table()
                for node_type in active_network.get_active_node_types():
                    node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
                for edge_type in active_network.get_active_edge_types():
                    edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))

                return output(elements=active_network.elements, network_info=network_info, message=message,
                              node_interaction_table=node_interaction_table, edge_interaction_table=edge_interaction_table,
                              analysis_summary="", hierarchical_tree_data="")
            else:
                message = dash_formatter.dash_message('Could not expand node(s)', success=False)
        return output(message=message)


    #####################
    ### DIALOG INPUTS ###
    #####################

    ### CLOSE DIALOG BUTTON ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'close-dialog':
        return output(grey_background=False, show_search_dialog=False,
                      show_edit_dialog=False, show_add_dialog=False, show_delete_dialog=False,
                      show_merge_dialog=False, show_add_node_dialog=False, show_add_edge_dialog=False,
                      show_export_image_dialog=False, show_confirm_load=False,
                      show_confirm_load2=False, show_confirm_file_load=False, show_confirm_file_load2=False,
                      add_edit_property_label='', add_edit_property_value='',
                      add_merge_property_label='', add_merge_property_value='',
                      add_addnode_property_label='', add_addnode_property_value='',
                      add_addedge_property_label='', add_addedge_property_value='')

    ########### CONFIRM LOAD DIALOG #######
    elif context.triggered[0]['prop_id'].split('.')[0] == 'confirm-load-button':
            return output(elements=[], show_confirm_load=False, grey_background=True, show_confirm_load2=True)

    ########### CONFIRM FILE LOAD DIALOG #######
    elif context.triggered[0]['prop_id'].split('.')[0] == 'upload':
        try:
            active_network = ActiveNetwork(path_2_data=None, from_file=False)
            active_network.deserialize_network(callback_kwargs['uploaded_file'])
            if not active_network.elements:
                text = "Uploaded file contains no valid entities or links."
                message = dash_formatter.dash_message(text, success=False)
                return output(message=message, grey_background=False, show_confirm_file_load=False)

            node_interaction_table = dash_formatter.get_node_interaction_table()
            edge_interaction_table = dash_formatter.get_edge_interaction_table()
            for node_type in active_network.get_active_node_types():
                node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
            for edge_type in active_network.get_active_edge_types():
                edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))
            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
            node_infos = []
            first_node_info = active_network.elements[0]['data'].get('info', {}) if active_network.elements else {}
            if active_network.node_label_field not in first_node_info:
                active_network.node_label_field = 'id'
            labels = [active_network.node_label_field]
            for e in active_network.elements:
                if e.get('group') == 'nodes':
                    info_dict = e['data'].get('info', {})
                    for info in info_dict:
                        if info not in node_infos:
                            node_infos.append(info)
            label_interaction_table = dash_formatter.get_label_table()
            for info in node_infos:
                if info == active_network.node_label_field:
                    label_interaction_table.append(dash_formatter.get_label_table_row(info, True))
                else:
                    label_interaction_table.append(dash_formatter.get_label_table_row(info, False))

            hide_prob_slider = True
            for e in active_network.edges:
                if 'probability' in e.get('properties', {}):
                    hide_prob_slider = False

            style.reset()
            style.set_type_styles(active_network.get_active_node_types())

            fname = callback_kwargs.get('uploaded_filename') or 'network'
            text = f"Network file '{fname}' successfully loaded ({len(active_network.nodes)} entities, {len(active_network.edges)} connections)."
            message = dash_formatter.dash_message(text, success=True)
            visualizer_app.logger.info(text)

            return output(elements=active_network.elements, stylesheet=style.stylesheet,
                          layout=ACTIVE_LAYOUT, elements_unaltered=active_network.elements,
                          stylesheet_unaltered=style.stylesheet, layout_unaltered=ACTIVE_LAYOUT,
                          hide_prob_slider=hide_prob_slider, hide_interaction_checkboxes=False,
                          node_interaction_table=node_interaction_table,
                          edge_interaction_table=edge_interaction_table,
                          label_interaction_table=label_interaction_table, entity_options=[],
                          entity_values=[], network_info=network_info, analysis_algorithms=[],
                          analysis_parameter=dash_formatter.dash_default_parameter(),
                          analysis_summary="", hierarchical_tree_data="",
                          hide_original_network_button=False, message=message,
                          show_confirm_file_load=False, grey_background=False)

        except UnicodeDecodeError:
            network_info = []
            text = "File couldn't be loaded due to a decoding error. Please make sure file has the right format."
            message = dash_formatter.dash_message(text, success=False)
            visualizer_app.logger.exception(text)
            return output(message=message, grey_background=False, show_confirm_file_load=False)
        except Exception as ex:
            text = f"File couldn't be loaded: {str(ex)}"
            message = dash_formatter.dash_message(text, success=False)
            visualizer_app.logger.exception(text)
            return output(message=message, grey_background=False, show_confirm_file_load=False)


    ########## LOAD DONE ##################

    elif context.triggered[0]['prop_id'].split('.')[0] == 'confirm-load-button2':
        try:
            selected_entities = resolve_selected_entities(callback_kwargs['entities'])
            active_network = ActiveNetwork(path_2_data=DATA_INFO[callback_kwargs['network_selection']]['path'],
                                           initialize=True, selected_nodes=selected_entities,
                                           params={'network_name': DATA_INFO[callback_kwargs['network_selection']]['name']})

            node_interaction_table = dash_formatter.get_node_interaction_table()
            edge_interaction_table = dash_formatter.get_edge_interaction_table()
            for node_type in active_network.get_active_node_types():
                node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
            for edge_type in active_network.get_active_edge_types():
                edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))
            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
            node_infos = []
            if active_network.node_label_field not in active_network.elements[0]['data']['info']:
                active_network.node_label_field = 'id'
            labels = [active_network.node_label_field]
            for e in active_network.elements:
                if e['group'] == 'nodes':
                    for info in e['data']['info']:
                        if not info in node_infos:
                            node_infos.append(info)
            label_interaction_table = dash_formatter.get_label_table()
            for info in node_infos:
                if info == active_network.node_label_field:
                    label_interaction_table.append(dash_formatter.get_label_table_row(info, True))
                else:
                    label_interaction_table.append(dash_formatter.get_label_table_row(info, False))

            hide_prob_slider = True
            for e in active_network.edges:
                if 'probability' in e['properties']:
                    hide_prob_slider = False

            style.reset()
            types = active_network.get_active_node_types()
            style.set_type_styles(types)
            message = dash_formatter.dash_message("Network successfully loaded.", success=True)

        except Exception as e:
            print(e)
            return output()

        return output(show_confirm_load2=False, elements=active_network.elements, stylesheet=style.stylesheet,
                      layout=ACTIVE_LAYOUT, elements_unaltered=active_network.elements,
                      stylesheet_unaltered=style.stylesheet, layout_unaltered=ACTIVE_LAYOUT,
                      hide_prob_slider=hide_prob_slider, hide_interaction_checkboxes=False,
                      node_interaction_table=node_interaction_table, edge_interaction_table=edge_interaction_table,
                      label_interaction_table=label_interaction_table, network_info=network_info,
                      analysis_algorithms=[], analysis_parameter=dash_formatter.dash_default_parameter(),
                      hide_original_network_button=False, message=message)


    ########## FILE LOAD DONE ##################

    elif context.triggered[0]['prop_id'].split('.')[0] == 'confirm-file-load-button2':
        try:
            active_network = ActiveNetwork(path_2_data=None, from_file=False)
            active_network.deserialize_network(callback_kwargs['uploaded_file'])
            node_interaction_table = dash_formatter.get_node_interaction_table()
            edge_interaction_table = dash_formatter.get_node_interaction_table()
            for node_type in active_network.get_active_node_types():
                node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
            for edge_type in active_network.get_active_edge_types():
                edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))
            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
            node_infos = []
            if active_network.node_label_field not in active_network.elements[0]['data']['info']:
                active_network.node_label_field = 'id'
            labels = [active_network.node_label_field]
            for e in active_network.elements:
                if e['group'] == 'nodes':
                    for info in e['data']['info']:
                        if not info in node_infos:
                            node_infos.append(info)
            label_interaction_table = dash_formatter.get_label_table()
            for info in node_infos:
                if info == active_network.node_label_field:
                    label_interaction_table.append(dash_formatter.get_label_table_row(info, True))
                else:
                    label_interaction_table.append(dash_formatter.get_label_table_row(info, False))

            hide_prob_slider = True
            for e in active_network.edges:
                if 'probability' in e['properties']:
                    hide_prob_slider = False

            style.reset()
            style.set_type_styles(active_network.get_active_node_types())
            message = dash_formatter.dash_message('Network file successfully loaded.', success=True)

        except UnicodeDecodeError:
            network_info = []
            message = dash_formatter.dash_message(
                "File couldn't be loaded. Please make sure file has the right format.",
                success=False)
        return output(show_confirm_file_load2=False, elements=active_network.elements, stylesheet=style.stylesheet,
                      layout=ACTIVE_LAYOUT, elements_unaltered=active_network.elements,
                      stylesheet_unaltered=style.stylesheet, layout_unaltered=ACTIVE_LAYOUT,
                      hide_prob_slider=hide_prob_slider, hide_interaction_checkboxes=False,
                      node_interaction_table=node_interaction_table, edge_interaction_table=edge_interaction_table,
                      label_interaction_table=label_interaction_table, entity_options=[],
                      entity_values=[], network_info=network_info, analysis_algorithms=[],
                      analysis_parameter=dash_formatter.dash_default_parameter(),
                      hide_original_network_button=False, message=message)

    ########### SEARCH DIALOG ##############

    ## ADD SEARCH CRITERIA ##
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-search-property-button':
        filter_container = callback_kwargs.get('filter_container')
        if filter_container:
            for idx, f in enumerate(filter_container):
                if f.get('props', {}).get('hidden'):
                    filter_container[idx]['props']['hidden'] = False
                    local_kwargs = {
                        'filter_container': filter_container,
                        'hide_filter_' + str(idx): False,
                        'grey_background': True,
                    }
                    return output(**local_kwargs)
        return output(message=dash_formatter.dash_message('Reached maximal number of filters (10).', success=False),
                      grey_background=True)

    ## APPLY FILTER ##
    elif context.triggered[0]['prop_id'].split('.')[0] == 'apply-filter-button':
        if not active_network or not active_network.elements:
            message = dash_formatter.dash_message('Please load a network first to filter.', success=False)
            return output(message=message, show_search_dialog=False, grey_background=False)

        quick_search = (callback_kwargs.get('search_quick_input') or '').strip().lower()
        search_props = callback_kwargs.get('search_property_dropdown_input') or []
        and_or_radios = callback_kwargs.get('and_or_radios') or ['AND'] * 10

        criteria = []
        for idx in range(10):
            prop = search_props[idx] if idx < len(search_props) else None
            val = callback_kwargs.get(f'search_value_{idx}')
            op = and_or_radios[idx] if idx < len(and_or_radios) else 'AND'
            if prop and val:
                val_list = [str(v).strip().lower() for v in (val if isinstance(val, list) else [val]) if str(v).strip()]
                if val_list:
                    criteria.append({
                        'prop': prop,
                        'values': val_list,
                        'op': op
                    })

        if not quick_search and not criteria:
            message = dash_formatter.dash_message('Please enter a search keyword or select a filter property and value.', success=False)
            return output(message=message, grey_background=True)

        matched_node_ids = set()
        for e in active_network.elements:
            if e.get('group') != 'nodes':
                continue
            data = e.get('data', {})
            node_id = str(data.get('id', ''))
            node_label = str(data.get('label', ''))
            node_type = str(data.get('type', ''))
            node_info = data.get('info', {}) if isinstance(data.get('info'), dict) else {}

            all_props = {}
            if getattr(active_network, 'nodes', None) and node_id in active_network.nodes:
                if isinstance(active_network.nodes[node_id], dict):
                    all_props.update(active_network.nodes[node_id])
            all_props.update(node_info)
            all_props['id'] = node_id
            all_props['label'] = node_label
            all_props['type'] = node_type

            # Quick search match
            quick_match = True
            if quick_search:
                quick_match = any(quick_search in str(v).lower() for v in all_props.values())

            # Criteria match
            crit_match = True
            if criteria:
                crit_results = []
                for c in criteria:
                    target_prop = c['prop']
                    target_vals = c['values']
                    actual_val = str(all_props.get(target_prop, '')).strip().lower()
                    matched_this = any(tv == actual_val or tv in actual_val for tv in target_vals)
                    crit_results.append((matched_this, c['op']))

                accum = crit_results[0][0]
                for i in range(1, len(crit_results)):
                    op = crit_results[i-1][1]
                    if op == 'OR':
                        accum = accum or crit_results[i][0]
                    else:
                        accum = accum and crit_results[i][0]
                crit_match = accum

            if quick_search and criteria:
                if quick_match and crit_match:
                    matched_node_ids.add(node_id)
            elif quick_search:
                if quick_match:
                    matched_node_ids.add(node_id)
            elif criteria:
                if crit_match:
                    matched_node_ids.add(node_id)

        if not matched_node_ids:
            message = dash_formatter.dash_message('No entities found matching the search criteria.', success=False)
            return output(message=message, grey_background=True)

        active_network.selected_nodes = set(matched_node_ids)
        active_network.selected_edges.clear()

        for e in active_network.elements:
            if e.get('group') == 'nodes':
                is_sel = e['data']['id'] in matched_node_ids
                e['data']['selected'] = is_sel
                e['data']['highlighted'] = is_sel
                e['data']['incoming_neighbor_selected'] = False
            elif e.get('group') == 'edges':
                s_sel = e['data']['source'] in matched_node_ids
                t_sel = e['data']['target'] in matched_node_ids
                e['data']['source_selected'] = s_sel
                e['data']['target_selected'] = t_sel
                e['data']['highlighted'] = s_sel and t_sel

        node_table, edge_table, label_table = get_interaction_tables(active_network)
        preview_names = list(matched_node_ids)[:4]
        preview_str = ', '.join(preview_names)
        if len(matched_node_ids) > 4:
            preview_str += f' (+{len(matched_node_ids)-4} more)'
        msg = f"Search matched {len(matched_node_ids)} node(s): {preview_str}. Matched nodes highlighted."
        message = dash_formatter.dash_message(msg, success=True)
        visualizer_app.logger.info(msg)

        return output(elements=active_network.elements, show_search_dialog=False,
                      grey_background=False, message=message,
                      node_interaction_table=node_table, edge_interaction_table=edge_table,
                      label_interaction_table=label_table)

    ## RESET FILTER ##
    elif context.triggered[0]['prop_id'].split('.')[0] == 'reset-filter-button':
        if active_network and active_network.elements:
            active_network.selected_nodes.clear()
            active_network.selected_edges.clear()
            for e in active_network.elements:
                if e.get('group') == 'nodes':
                    e['data']['selected'] = False
                    e['data']['highlighted'] = False
                    e['data']['incoming_neighbor_selected'] = False
                elif e.get('group') == 'edges':
                    e['data']['source_selected'] = False
                    e['data']['target_selected'] = False
                    e['data']['highlighted'] = False
            node_table, edge_table, label_table = get_interaction_tables(active_network)
        else:
            node_table, edge_table, label_table = [], [], []

        message = dash_formatter.dash_message("Search filters and selections reset.", success=True)
        return output(elements=active_network.elements if active_network else dash.no_update,
                      show_search_dialog=False, grey_background=False,
                      search_quick_input="", message=message,
                      node_interaction_table=node_table, edge_interaction_table=edge_table,
                      label_interaction_table=label_table)



    ############ EDITING DIALOG ############

    ### APPLY EDITING ###
    # When Apply in edit element dialog is clicked: Apply changes to selected element.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'apply-edit-button':
        input_fields = []
        for state in context.states_list:
            if state and isinstance(state, list):
                if state[0]['id']['type'] == 'edit-input-field':
                    input_fields = state
        properties = {'type': callback_kwargs['edit_element_type']}
        for field in input_fields:
            property_name = field['id']['id']
            value = field['value']
            if not value:
                properties[property_name] = ''
            else:
                properties[property_name] = value

        selected_nodes = active_network.get_selected_nodes()
        selected_edges = active_network.get_selected_edges()

        node_table, edge_table, label_table = get_interaction_tables(active_network)

        if selected_nodes:
            active_network.update_an_active_node(selected_nodes[0], properties)
            style.set_type_styles(active_network.get_active_node_types())
        elif selected_edges:
            active_network.update_an_active_edge(selected_edges[0], properties)
        return output(elements=active_network.elements, stylesheet=style.stylesheet,
                      grey_background=False, show_edit_dialog=False, add_edit_property_label='',
                      add_edit_property_value='',
                      node_interaction_table=node_table,
                      edge_interaction_table=edge_table,
                      label_interaction_table=label_table
                      )


    ### ADD EDIT PROPERTY ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-edit-property-button':
        if not callback_kwargs['add_edit_property_label']:
            message = dash_formatter.dash_message('Please insert a property.', False)
            return output(message=message, grey_background=True)
        duplicate = False
        if callback_kwargs['add_edit_property_label'].lower() == 'element type':
            duplicate = True
        else:
            for element in callback_kwargs['edit_element_container'][2:]:
                if len(element['props']) > 1:
                    if callback_kwargs['add_edit_property_label'].lower() == element['props']['children'][0]['props']['id']['id'].lower():
                        duplicate = True
        if not duplicate:
            edit_element_container = callback_kwargs['edit_element_container']
            edit_element_container.append(dash_formatter.get_label(callback_kwargs['add_edit_property_label']))
            edit_element_container.append(dash_formatter.get_text_field(callback_kwargs['add_edit_property_label'],
                                                                        callback_kwargs['add_edit_property_value'],
                                                                        'edit'))

            return output(grey_background=True, edit_element_container=edit_element_container,
                          add_edit_property_label='', add_edit_property_value='')
        else:
            message = dash_formatter.dash_message('Property already exists.', False)
            return output(message=message, grey_background=True)


    ########### ADD NODE DIALOG ############

    ### OPEN ADD NODE DIALOG ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-node-button':
        node_container = callback_kwargs['addnode_element_container']
        node_container[1]['props']['options'] = \
            dash_formatter.dash_type_options(active_network.get_active_node_types())
        return output(addnode_element_container=node_container, grey_background=True, show_add_node_dialog=True, show_add_dialog=False)


    ### ADD ADDNODE PROPERTY ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-addnode-property-button':
        if not callback_kwargs['add_addnode_property_label']:
            message = dash_formatter.dash_message('Please insert a property.', False)
            return output(message=message, grey_background=True)
        duplicate = False
        if callback_kwargs['add_addnode_property_label'].lower() == 'element type' \
                or callback_kwargs['add_addnode_property_label'].lower() == 'element name':
            duplicate = True
        else:
            for element in callback_kwargs['addnode_element_container'][4:]:
                if len(element['props']) > 1:
                    if callback_kwargs['add_addnode_property_label'].lower() == element['props']['children'][0]['props']['id']['id'].lower():
                        duplicate = True
        if not duplicate:
            node_container = callback_kwargs['addnode_element_container']
            node_container.append(dash_formatter.get_label(callback_kwargs['add_addnode_property_label']))
            node_container.append(dash_formatter.get_text_field(callback_kwargs['add_addnode_property_label'],
                                                                callback_kwargs['add_addnode_property_value'],
                                                                'addnode'))
            return output(grey_background=True, addnode_element_container=node_container,
                          add_addnode_property_label='', add_addnode_property_value='')
        else:
            message = dash_formatter.dash_message('Property already exists.', False)
            return output(message=message, grey_background=True)


    ### APPLY ADD NODE ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'apply-addnode-button':
        properties = {'type': callback_kwargs['addnode_elements_type'],
                      'name': callback_kwargs['addnode_element_name']}
        input_fields = []
        for state in context.states_list:
            if state and isinstance(state, list):
                if state[0]['id']['type'] == 'addnode-input-field':
                    input_fields = state
        for field in input_fields:
            property_name = field['id']['id']
            value = field['value']
            if not value:
                properties[property_name] = ''
            else:
                properties[property_name] = value
        active_network.add_an_active_node(properties['name'], properties)
        style.set_type_styles(active_network.get_active_node_types())
        network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
        return output(elements=active_network.elements, stylesheet=style.stylesheet,
                      grey_background=False, show_add_node_dialog=False, show_add_dialog=False,
                      add_addnode_property_label='', add_addnode_property_value='',
                      analysis_summary="", hierarchical_tree_data="",
                      network_info=network_info)

    ########## ADD EDGE DIALOG ##############

    ### OPEN ADD EDGE DIALOG ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-edge-button':
        edge_container = callback_kwargs['addedge_element_container']
        edge_container[1]['props']['options'] = \
            dash_formatter.dash_type_options(active_network.get_active_edge_types())
        selected_nodes = active_network.get_selected_nodes()
        if len(selected_nodes) == 2:
            source_options = dash_formatter.dash_type_options(selected_nodes)
            target_options = dash_formatter.dash_type_options(selected_nodes)
        else:
            all_nodes = list(active_network.active_nodes.keys())
            source_options = dash_formatter.dash_type_options(all_nodes)
            target_options = dash_formatter.dash_type_options(all_nodes)

        return output(addedge_element_container=edge_container, grey_background=True,
                      show_add_edge_dialog=True, show_add_dialog=False,
                      addedge_source_node_options=source_options, addedge_target_node_options=target_options)


    ### ADD ADDEDGE PROPERTY ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-addedge-property-button':
        if not callback_kwargs['add_addedge_property_label']:
            message = dash_formatter.dash_message('Please insert a property.', False)
            return output(message=message, grey_background=True)
        duplicate = False
        if callback_kwargs['add_addedge_property_label'].lower() == 'element type':
            duplicate = True
        else:
            for element in callback_kwargs['addedge_element_container'][4:]:
                if len(element['props']) > 1:
                    if callback_kwargs['add_addedge_property_label'].lower() == element['props']['children'][0]['props']['id']['id'].lower():
                        duplicate = True
        if not duplicate:
            edge_container = callback_kwargs['addedge_element_container']
            edge_container.append(dash_formatter.get_label(callback_kwargs['add_addedge_property_label']))
            edge_container.append(dash_formatter.get_text_field(callback_kwargs['add_addedge_property_label'],
                                                                callback_kwargs['add_addedge_property_value'],
                                                                'addedge'))
            return output(grey_background=True, addedge_element_container=edge_container,
                          add_addedge_property_label='', add_addedge_property_value='')
        else:
            message = dash_formatter.dash_message('Property already exists.', False)
            return output(message=message, grey_background=True)


    ### APPLY ADD EDGE ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'apply-addedge-button':
        properties = {'type': callback_kwargs['addedge_element_type'],
                      'name': callback_kwargs['addedge_element_name']}
        input_fields = []
        for state in context.states_list:
            if state and isinstance(state, list):
                if state[0]['id']['type'] == 'addedge-input-field':
                    input_fields = state
        for field in input_fields:
            property_name = field['id']['id']
            value = field['value']
            if not value:
                properties[property_name] = ''
            else:
                properties[property_name] = value
        active_network.add_an_active_edge(source=callback_kwargs['addedge_source_node'],
                                          target=callback_kwargs['addedge_target_node'], properties=properties)
        network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
        return output(elements=active_network.elements, grey_background=False, show_add_edge_dialog=False,
                      add_addedge_property_label='', add_addedge_property_value='', network_info=network_info)

    ########## DELETE DIALOG ############

    ### APPLY DELETE ELEMENT ###
    # When 'Delete Node' button is clicked: Delete the currently selected node(s).
    elif context.triggered[0]['prop_id'].split('.')[0] == 'delete-button':
        message = dash_formatter.dash_message('Select element(s) to delete ...', success=False)
        selected_nodes = active_network.get_selected_nodes()
        selected_edges = active_network.get_selected_edges()
        if not selected_nodes and not selected_edges:
            return output(message=message, grey_background=False, show_delete_dialog=False)
        if selected_nodes:
            for node in selected_nodes:
                active_network.delete_an_active_node(node)
        if selected_edges:
            for edge in selected_edges:
                active_network.delete_an_active_edge(edge)
        message = dash_formatter.dash_message('Selected elements were deleted.', success=True)
        network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
        return output(elements=active_network.elements, message=message,
                      grey_background=False, show_delete_dialog=False, network_info=network_info)


    ######### MERGE DIALOG #############

    ### APPLY MERGE ELEMENT ###
    # When Apply in merge elements dialog is clicked: Apply changes to selected element.
    elif context.triggered[0]['prop_id'].split('.')[0] == 'apply-merge-button':
        try:
            properties = {'type': callback_kwargs['merge_elements_type']}
            input_fields = []
            for state in context.states_list:
                if state and isinstance(state, list):
                    if state[0]['id']['type'] == 'merge-input-field':
                        input_fields = state
            for field in input_fields:
                property_name = field['id']['id']
                value = field['value']
                if not value:
                    properties[property_name] = ''
                else:
                    properties[property_name] = value


            selected_nodes = active_network.get_selected_nodes()
            selected_edges = active_network.get_selected_edges()

            if selected_nodes:
                active_network.merge_active_nodes(selected_nodes, properties['id'], properties)
                style.set_type_styles(active_network.get_active_node_types())

            network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())

            # Merging edges not possible at the moment.
            # elif selected_edges:
            #     ele_index = active_network.active_edges[selected_edges[0]]['element_index']
            #     new_id = str(active_network.elements[ele_index]['data']['id']) + "_merged"
            #     active_network.merge_active_edges(selected_edges, new_id, properties)

            return output(elements=active_network.elements, stylesheet=style.stylesheet,
                          grey_background=False, show_merge_dialog=False,
                          add_merge_property_label='', add_merge_property_value='',
                          network_info=network_info)

        except:
            text = 'An error occurred while trying to apply node merge.'
            message = dash_formatter.dash_message(text, False)
            visualizer_app.logger.exception(text)
            return output(message=message, grey_background=False, show_merge_dialog=False,
                          add_merge_property_label='', add_merge_property_value='')


    ### ADD MERGE PROPERTY ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'add-merge-property-button':
        if not callback_kwargs['add_merge_property_label']:
            message = dash_formatter.dash_message('Please insert a property.', False)
            return output(message=message, grey_background=True)
        duplicate = False
        if callback_kwargs['add_merge_property_label'].lower() == 'element type':
            duplicate = True
        else:
            for element in callback_kwargs['merge_element_container'][2:]:
                if len(element['props']) > 1:
                    if callback_kwargs['add_merge_property_label'].lower() == element['props']['children'][0]['props']['id']['id'].lower():
                        duplicate = True
        if not duplicate:
            merge_e_container = callback_kwargs['merge_element_container']
            merge_e_container.append(dash_formatter.get_label(callback_kwargs['add_merge_property_label']))
            merge_e_container.append(dash_formatter.get_text_field(callback_kwargs['add_merge_property_label'],
                                                                   callback_kwargs['add_merge_property_value'],
                                                                   'merge'))
            return output(grey_background=True, merge_element_container=merge_e_container,
                          add_merge_property_label='', add_merge_property_value='')
        else:
            message = dash_formatter.dash_message('Property already exists.', False)
            return output(message=message, grey_background=True)


    ######### EXPORT IMAGE DIALOG #########

    ### OPEN EXPORT IMAGE DIALOG ### TODO: MOVE TO OPEN DIALOG SECTION
    elif context.triggered[0]['prop_id'].split('.')[0] == 'export-image-button':
        return output(grey_background=True, show_export_image_dialog=True)


    ### APPLY IMAGE EXPORT ###
    elif context.triggered[0]['prop_id'].split('.')[0] == 'apply-export-image-button':
        export_type = callback_kwargs.get('export_type') or 'png'
        export = {'type': export_type,
                  'action': 'download'}
        return output(grey_background=False, show_export_image_dialog=False, image_export=export)


    ############################
    ### DYNAMIC MULTI INPUTS ###
    ############################

    elif context.triggered[0]['prop_id'].split('.')[0].startswith('{'):
        prop_str = context.triggered[0]['prop_id'].split('.')[0]
        try:
            trigger_json = json.loads(prop_str)
            type = trigger_json.get('type')
            raw_id = trigger_json.get('id')
        except Exception:
            type = prop_str.split(',')[1].split(':')[1][1:-2]
            raw_id = prop_str.split(',')[0][1:]
        my_id = prop_str.split(',')[0][1:]

        ### REMOVE EDIT PROPERTY ###
        if type == 'remove-input-field':
            field = my_id.split(';')[0][5:].split(':')[1]
            container_string = my_id.split(';')[1].split(':')[1][:-1].replace('-', '_')
            container = callback_kwargs[container_string]

            for idx, input in enumerate(container):
                if 'children' in input['props']:
                    if input['props']['children'] == field:
                        del container[idx:idx+2]
                        break

            if container_string == 'merge_element_container':
                return output(grey_background=True, show_merge_dialog=True,
                       merge_element_container=container)
            elif container_string == 'edit_element_container':
                return output(grey_background=True, show_edit_dialog=True,
                       edit_element_container=container)
            elif container_string == 'addnode_element_container':
                return output(grey_background=True, show_add_node_dialog=True,
                              addnode_element_container=container)
            elif container_string == 'addedge_element_container':
                return output(grey_background=True, show_add_edge_dialog=True,
                       addedge_element_container=container)
            elif container_string == 'filter_container':
                return output(grey_background=True, show_search_dialog=True,
                              filter_container=container)
            else:
                return output()


        ### HIGHLIGHT/HIDE CHECKBOXES ###
        if type == 'element-interaction-checkbox':
            checkbox_id = my_id.split(':')[1][1:-1]
            action = checkbox_id.split('-')[0]
            element_type = checkbox_id.split('-')[1]
            element_class = checkbox_id.split('-')[2]
            value = context.triggered[0]['value']
            selected = True if value else False
            if action == 'show':
                if element_class == 'node':
                    if selected:
                        active_network.unhide_elements(node_types=[element_type])
                    else:
                        active_network.hide_elements(node_types=[element_type])
                elif element_class == 'edge':
                    if selected:
                        active_network.unhide_elements(edge_types=[element_type])
                    else:
                        active_network.hide_elements(edge_types=[element_type])
            elif action == 'highlight':
                if element_class == 'node':
                    if selected:
                        active_network.highlight_elements(node_types=[element_type])
                    else:
                        active_network.unhighlight_elements(node_types=[element_type])
                elif element_class == 'edge':
                    if selected:
                        active_network.highlight_elements(edge_types=[element_type])
                    else:
                        active_network.unhighlight_elements(edge_types=[element_type])
            return output(elements=active_network.elements)

        elif type == 'label-display-checkbox':
            value_list = context.triggered[0]['value']
            value = my_id.split(':')[1].split('-')[1]
            if value_list:
                labels.append(value)
            else:
                labels.remove(value)
            for idx, e in enumerate(active_network.elements):
                if e['group'] == 'nodes':
                   new_label = ''
                   for l in labels:
                       if l in e['data']['info']:
                           new_label += str(e['data']['info'][l]) + ' \n'
                   active_network.elements[idx]['data']['label'] = new_label
            return output(elements=active_network.elements)

        ## CHOOSE FILTER PROPERTY ##
        # When property is chosen, load according values
        elif type == 'search-property-dropdown':
            dropdown_id = str(raw_id)
            selected_prop = context.triggered[0].get('value')
            if not selected_prop and callback_kwargs.get('search_property_dropdown_input'):
                try:
                    selected_prop = callback_kwargs['search_property_dropdown_input'][int(dropdown_id)]
                except Exception:
                    selected_prop = None

            if not selected_prop or selected_prop not in network_properties:
                local_kwargs = {
                    'search_value_options_' + dropdown_id: [],
                    'grey_background': True,
                }
            else:
                vals = sorted(list(network_properties[selected_prop]))
                options = dash_formatter.dash_type_options(vals)
                local_kwargs = {
                    'search_value_options_' + dropdown_id: options,
                    'grey_background': True,
                }
            return output(**local_kwargs)

        ## DELETE FILTER PROPERTY ##
        elif type == 'remove-search-field':
            dropdown_id = str(raw_id)
            ## Reset values ##
            filter_container = callback_kwargs.get('filter_container')
            if filter_container and int(dropdown_id) < len(filter_container):
                try:
                    # property
                    filter_container[int(dropdown_id)]['props']['children'][0]['props']['children'][0]['props']['value'] = None
                    # value
                    filter_container[int(dropdown_id)]['props']['children'][1]['props']['children'][0]['props']['value'] = None
                    # value options
                    filter_container[int(dropdown_id)]['props']['children'][1]['props']['children'][0]['props']['options'] = []
                    # And/Or selection
                    filter_container[int(dropdown_id)]['props']['children'][2]['props']['children'][0]['props']['value'] = 'AND'
                    filter_container += [filter_container.pop(int(dropdown_id))]
                except Exception:
                    pass

            local_kwargs = {
                'hide_filter_' + dropdown_id: True,
                'grey_background': True,
                'filter_container': filter_container if filter_container else dash.no_update,
            }
            return output(**local_kwargs)

    else:
        return output()



@visualizer_app.callback(Output('info-table', 'children'),
                         [Input('cytoscape', 'mouseoverNodeData'),
                          Input('cytoscape', 'mouseoverEdgeData'),
                          Input('cytoscape', 'tapNodeData'),
                          Input('cytoscape', 'tapEdgeData')])
def display_tap_node_data(node_data, edge_data, tap_node_data=None, tap_edge_data=None):
    """
    Writes node/edge data to infobox on mouseover and tap/selection events.
    :param node_data: Data of hovered node.
    :param edge_data: Data of hovered edge.
    :param tap_node_data: Data of clicked/selected node.
    :param tap_edge_data: Data of clicked/selected edge.
    :return:
    """
    context = dash.callback_context
    if not context.triggered or not context.triggered[0]['prop_id']:
        raise PreventUpdate

    prop = context.triggered[0]['prop_id'].split('.')[1]

    # Show node data when hovered or tapped on a node
    if prop in ('mouseoverNodeData', 'tapNodeData'):
        target = node_data if prop == 'mouseoverNodeData' else tap_node_data
        if not target or not isinstance(target, dict):
            raise PreventUpdate
        data = dict(target.get('info', {}))
        if 'community' in target and target['community'] is not None and 'community' not in data:
            data['community'] = target['community']
        info_table = dash_formatter.get_info_table()
        for element in data:
            info_table.append(dash_formatter.get_info_table_row(element, str(data[element])))
        return info_table

    elif prop in ('mouseoverEdgeData', 'tapEdgeData'):
        target = edge_data if prop == 'mouseoverEdgeData' else tap_edge_data
        if not target or not isinstance(target, dict):
            raise PreventUpdate
        data = dict(target.get('info', {}))
        info_table = dash_formatter.get_info_table()
        for element in data:
            info_table.append(dash_formatter.get_info_table_row(element, str(data[element])))
        return info_table


@visualizer_app.server.route('/downloadNetwork')
def download_network():
    result = active_network.serialize_network()
    filename = str(active_network.network_name) + '.json'
    if result['success']:
        return flask.send_file(result['mem_object'], mimetype='text/json',
                               download_name=filename,
                               as_attachment=True)


@visualizer_app.server.route('/exportNetwork')
def export_network():
    result = active_network.serialize_network_new_format()
    filename = str(active_network.network_name) + '.json'
    if result['success']:
        return flask.send_file(result['mem_object'], mimetype='text/json',
                               download_name=filename,
                               as_attachment=True)


@visualizer_app.server.route('/userDocumentation')
def send_documentation():
    return flask.send_from_directory('{}/visualizer/documentation'.format(path2root), 'visualizer_doc.html')


@visualizer_app.server.route('/images/<path:filename>')
def get_images(filename):
    return flask.send_from_directory('{}/visualizer/documentation/images'.format(path2root), filename)





def get_interaction_tables(active_network):
    node_interaction_table = dash_formatter.get_node_interaction_table()
    edge_interaction_table = dash_formatter.get_edge_interaction_table()
    for node_type in active_network.get_active_node_types():
        node_interaction_table.append(dash_formatter.get_element_interaction_row(node_type, 'node'))
    for edge_type in active_network.get_active_edge_types():
        edge_interaction_table.append(dash_formatter.get_element_interaction_row(edge_type, 'edge'))
    network_info = dash_formatter.dash_network_info(active_network.get_active_network_info())
    node_infos = []
    first_info = active_network.elements[0]['data'].get('info', {}) if active_network.elements else {}
    if active_network.node_label_field not in first_info:
        active_network.node_label_field = 'id'
    labels = [active_network.node_label_field]
    for e in active_network.elements:
        if e.get('group') == 'nodes':
            for info in e['data'].get('info', {}):
                if not info in node_infos:
                    node_infos.append(info)
    label_interaction_table = dash_formatter.get_label_table()
    for info in node_infos:
        if info == active_network.node_label_field:
            label_interaction_table.append(dash_formatter.get_label_table_row(info, True))
        else:
            label_interaction_table.append(dash_formatter.get_label_table_row(info, False))
    return node_interaction_table, edge_interaction_table, label_interaction_table


# ------------------------------------------------------------------------------------------------- #
# CLIENTSIDE CALLBACK: STREAM CYTOSCAPE NETWORK UPDATES TO INTELLIGENCE ENGINE
# ------------------------------------------------------------------------------------------------- #
visualizer_app.clientside_callback(
    """
    function(elements, tapNodeData, tabValue) {
        if (window.UNBOUND && typeof window.UNBOUND.onNetworkUpdate === 'function') {
            window.UNBOUND.onNetworkUpdate(elements, tapNodeData, tabValue);
        }
        return '';
    }
    """,
    Output('unbound-intel-trigger', 'children'),
    Input('cytoscape', 'elements'),
    Input('cytoscape', 'tapNodeData'),
    Input('tabs', 'value'),
    prevent_initial_call=False
)

# ------------------------------------------------------------------------------------------------- #
# REGISTER CASE DASHBOARD CALLBACKS (CASE MANAGEMENT, FILTERING, CREATION, DOSSIER, WORKSPACE CONTEXT)
# ------------------------------------------------------------------------------------------------- #
from visualizer.case_dashboard import register_dashboard_callbacks
register_dashboard_callbacks(visualizer_app)