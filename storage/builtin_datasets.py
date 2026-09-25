import base64
import sys
import os
import json
import networkx as nx
import io
import csv
import re
import random
import copy
import ast
from copy import deepcopy
from pathlib import Path

# find path to root directory of the project so as to import from other packages
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

from framework.interfaces import DataManager
from storage import helpers
from analyzer.request_taker import InMemoryAnalyzer
import visualizer.io_utils as converter

node_update_action = 'update_node'
node_add_action = 'add_node'
node_delete_action = 'delete_node'

edge_update_action = 'update_edge'
edge_add_action = 'add_edge'
edge_delete_action = 'delete_edge'

max_num_recent_changes = 20
max_num_recent_interactions = 20


class BuiltinDataset:
    def __init__(self, path_2_data, uploaded=False, from_file=True):
        # dataset info
        self.name = None
        self.nodes = {}
        self.edges = []
        self.adj_list = {}
        self.in_adj_list = {}
        self.node_types = {}
        self.edge_types = {}
        self.recent_changes = []
        self.meta_info = {}
        if from_file:
            if uploaded:
                file = path_2_data
                for line in file.splitlines():
                    line = line.strip()
                    if len(line) == 0:
                        continue
                    if line.startswith('#'):  # ignore the comments
                        continue
                    line_object = json.loads(line)
                    if line_object['type'] == 'node':
                        node = line_object['properties']
                        if 'community' in line_object:
                            node['community'] = line_object['community']
                            node['community_confidence'] = line_object['community_confidence']
                        if 'social_influence_score' in line_object:
                            node['social_influence_score'] = line_object['social_influence_score']
                            node['normalized_social_influence'] = line_object['normalized_social_influence']
                        self.nodes[line_object['id']] = node
                        if 'type' in node:
                            node_type = node['type']
                            if node_type in self.node_types:
                                self.node_types[node_type] += 1
                            else:
                                self.node_types[node_type] = 1

                    elif line_object['type'] == 'edge':
                        edge = {'source': line_object['source'], 'target': line_object['target'],
                                'observed': True, 'properties': line_object['properties']}
                        if 'observed' in line_object:
                            if line_object['observed'] == 'false':
                                edge['observed'] = 'false'
                        self.edges.append(edge)
                        e_index = len(self.edges) - 1
                        source = edge['source']
                        if source in self.adj_list:
                            self.adj_list[source].append(e_index)
                        else:
                            self.adj_list[source] = [e_index]
                        target = edge['target']
                        if target in self.in_adj_list:
                            self.in_adj_list[target].append(e_index)
                        else:
                            self.in_adj_list[target] = [e_index]

                        if 'type' in line_object['properties']:
                            edge_type = line_object['properties']['type']
                            if edge_type in self.edge_types:
                                self.edge_types[edge_type] += 1
                            else:
                                self.edge_types[edge_type] = 1
                    else:
                        continue
            else:
                file = open(path_2_data, 'r')
                decoded = file.read()
                if decoded.startswith("{\n"):
                    in_data = json.loads(decoded)
                    data_list = converter.new_to_old(in_data)
                    try:
                        self.meta_info['directed'] = in_data['directed']
                        self.meta_info['multigraph'] = in_data['multigraph']
                        self.meta_info['graph'] = in_data['graph']
                    except KeyError:
                        print(
                            'Input JOSN must have directed, multigraph and graph fields. See specification for information.')
                else:
                    # a = json.loads(decoded)
                    data_list = [json.loads(line.strip()) for line in decoded.split('\n') if
                                 len(line) != 0 and not line.startswith('#')]

                # print('decoded = ', decoded)
                for line_object in data_list:
                    if line_object['type'] == 'node':
                        node = line_object['properties']
                        node['id'] = line_object['id']
                        self.nodes[line_object['id']] = node
                        if 'type' in node:
                            node_type = node['type']
                            if node_type in self.node_types:
                                self.node_types[node_type] += 1
                            else:
                                self.node_types[node_type] = 1
                    elif line_object['type'] == 'edge':
                        edge = {'source': line_object['source'], 'target': line_object['target'],
                                'observed': True, 'properties': line_object['properties']}
                        self.edges.append(edge)
                        e_index = len(self.edges) - 1
                        source = edge['source']
                        if source in self.adj_list:
                            self.adj_list[source].append(e_index)
                        else:
                            self.adj_list[source] = [e_index]
                        target = edge['target']
                        if target in self.in_adj_list:
                            self.in_adj_list[target].append(e_index)
                        else:
                            self.in_adj_list[target] = [e_index]
                        if 'type' in line_object['properties']:
                            edge_type = line_object['properties']['type']
                            if edge_type in self.edge_types:
                                self.edge_types[edge_type] += 1
                            else:
                                self.edge_types[edge_type] = 1
                    else:
                        continue
                file.close()

        else:
            # create network on-the-fly
            # TODO: supposed to be refactored
            pass

    def _generate_edges_nodes_and_node_ids_for_analyzing(self, network_edges, params):
        nx_nodes = {}
        nx_edges = []
        nx_node_ids = []

        for e in network_edges:
            if e is None:
                continue
            if helpers.is_valid_edge(e, params):
                source = e['source']
                target = e['target']
                if source not in nx_nodes:
                    source_index = len(nx_node_ids)
                    nx_nodes[source] = source_index
                    nx_node_ids.append(source)
                else:
                    source_index = nx_nodes[source]

                if target not in nx_nodes:
                    target_index = len(nx_node_ids)
                    nx_nodes[target] = target_index
                    nx_node_ids.append(target)
                else:
                    target_index = nx_nodes[target]

                nx_edges.append((source_index, target_index))

        return nx_edges, nx_nodes, nx_node_ids

    def get_network(self, node_ids=None, params=None, return_edge_index=False):
        """
        mimic the get_network function of DataManager, i.e., getting ego-network surrounding node_ids
        :param node_ids:
        :param params:
        :return:
        """
        if node_ids is None or any(v in ('__all__', 'all', 'select_all', 'all_entities') for v in node_ids):
            node_ids = list(self.nodes.keys())
        else:
            if len(list(node_ids)) == 0:
                node_ids = list(self.nodes.keys())
        edges = []
        for u in node_ids:
            if u in self.adj_list:
                edges.extend(self.adj_list[u])
        edges = [e for e in edges if helpers.is_valid_edge(self.edges[e], params)]
        involved_nodes = set([self.edges[e]['target'] for e in edges])
        node_ids = set(node_ids)
        involved_nodes = involved_nodes.union(node_ids)
        for v in involved_nodes:
            if v in self.adj_list:
                if v not in node_ids:
                    edges.extend([e for e in self.adj_list[v] if self.edges[e]['target'] in involved_nodes and
                                  helpers.is_valid_edge(self.edges[e]['target'], params)])
        nodes = [{'id': u, 'properties': self.nodes[u]} for u in involved_nodes if u in self.nodes]
        if not return_edge_index:
            edges = [self.edges[e] for e in edges]
        return {'edges': edges, 'nodes': nodes}

    def get_edges(self, node_ids=None, params=None):
        """
        mimic the get_edges function of DataManager
        :param node_ids:
        :param params:
        :return:
        """

        if node_ids is None:
            node_ids = list(self.nodes.keys())

        nx_edges, nx_nodes, _ = self._generate_edges_nodes_and_node_ids_for_analyzing(self.edges, params)
        nx_graph = nx.DiGraph()
        nx_graph.add_edges_from(nx_edges)

        nx_found_next_edges = []
        nx_not_found_next_edges = []
        for checking_node in node_ids:
            if checking_node in self.adj_list:
                if helpers.is_valid_node(checking_node, params):
                    nx_checking_node_id = nx_nodes.get(checking_node)
                    nx_next_edges = []
                    for edge in nx_graph.edges(nx_checking_node_id):
                        temp_edge = self.edges[nx_edges.index(edge)]
                        nx_next_edges.append(temp_edge)
                    nx_found_next_edges.append({'id': checking_node, 'edges': nx_next_edges})
            else:
                nx_not_found_next_edges.append(checking_node)

        return {'found': nx_found_next_edges, 'not_found': nx_not_found_next_edges}

    def get_neighbors(self, node_ids=None, params=None):
        """
        mimic the get_neighbors function of DataManager
        :param node_ids:
        :param params:
        :return:
        """
        if node_ids is None:
            node_ids = list(self.nodes.keys())

        nx_edges, nx_nodes, nx_node_ids = self._generate_edges_nodes_and_node_ids_for_analyzing(self.edges, params)
        nx_graph = nx.DiGraph()
        nx_graph.add_edges_from(nx_edges)

        nx_found_neighbors = []
        nx_not_found_neighbors = []

        for checking_node in node_ids:
            if checking_node in self.adj_list:
                if helpers.is_valid_node(checking_node, params):
                    nx_checking_node_id = nx_nodes.get(checking_node)
                    nx_neighbors = []
                    for nx_neighbor_node_id in nx_graph.neighbors(nx_checking_node_id):
                        neighbor_node_id = nx_node_ids[nx_neighbor_node_id]
                        temp_nx_edge = (nx_checking_node_id, nx_neighbor_node_id)
                        temp_edge_properties = self.edges[nx_edges.index(temp_nx_edge)].get('properties')

                        neighbor = {'neighbor_id': neighbor_node_id,
                                    'properties': self.nodes[neighbor_node_id],
                                    'edges_properties': temp_edge_properties}
                        nx_neighbors.append(neighbor)
                    nx_found_neighbors.append({'id': checking_node, 'neighbors': nx_neighbors})
            else:
                nx_not_found_neighbors.append(checking_node)

        # for u in node_ids:
        #     if u in self.adj_list:
        #         edges = [e for e in self.adj_list[u] if helpers.is_valid_edge(self.edges[e], params)]             
        #         edges = [e for e in edges if helpers.is_valid_node(self.nodes[self.edges[e]['target']], params)]

        #         if len(edges) > 0:
        #             groups = {}
        #             for e in edges:
        #                 v = self.edges[e]['target']
        #                 if v in groups:
        #                     groups[v].append(e)
        #                 else:
        #                     groups[v] = [e]
        #             neighbors = []
        #             for v in groups:
        #                 v_edges = groups[v]
        #                 v_edges = [self.edges[e]['properties'] for e in v_edges]
        #                 neighbor = {'neighbor_id': v, 'properties': self.nodes[v], 'edges': v_edges}
        #                 neighbors.append(neighbor)
        #             found.append({'id': u, 'neighbors': neighbors})
        #     else:
        #         not_found.append(u)

        return {'found': nx_found_neighbors, 'not_found': nx_not_found_neighbors}

    def search_nodes(self, node_ids=None, params=None):
        """
        mimic the search_nodes function of DataManager
        :param node_ids:
        :param params:
        :return:
        """
        if node_ids is None:
            node_ids = list(self.nodes.keys())
        found = []
        not_found = []
        for u in node_ids:
            if u in self.nodes:
                if helpers.is_valid_node(self.nodes[u], params):
                    found.append({'id': u, 'properties': self.nodes[u]})
            else:
                not_found.append(u)
        return {'found': found, 'not_found': not_found}

    def forget_changes(self):
        if len(self.recent_changes) > max_num_recent_changes:
            self.recent_changes = self.recent_changes[-max_num_recent_changes:]

    def update_a_node(self, node, properties):
        """

        :param node:
        :param properties:
        :return:
        """
        # print('node = ', node, ' properties = ', properties)
        if node not in self.nodes:
            return {'success': 0, 'message': 'node not found!'}
        else:
            node_properties = self.nodes[node]
            pre_properties = copy.deepcopy(node_properties)
            if node_properties is None:
                self.nodes[node] = properties
                if 'type' in properties:
                    node_type = properties['type']
                    if node_type in self.node_types:
                        self.node_types[node_type] += 1
                    else:
                        self.node_types[node_type] = 1
            else:
                type_change = False
                if 'type' in properties:
                    if 'type' in node_properties:
                        if properties['type'] != node_properties['type']:
                            type_change = True
                            node_type = node_properties['type']
                            # print('self.node_types =', self.node_types)
                            self.node_types[node_type] -= 1
                            if self.node_types[node_type] == 0:
                                del self.node_types[node_type]

                node_properties.clear()
                for p, value in properties.items():
                    node_properties[p] = value

                if type_change:
                    node_type = properties['type']
                    if node_type in self.node_types:
                        self.node_types[node_type] += 1
                    else:
                        self.node_types[node_type] = 1
            action = {'action': node_update_action, 'node': node, 'pre_properties': pre_properties}
            self.recent_changes.append(action)
            self.forget_changes()

            print('after update: node = ', node, 'properties = ', self.nodes[node])

            return {'success': 1, 'message': 'node updated successfully!'}

    def add_a_node(self, node, properties=None):
        """

        :param node:
        :param properties:
        :return:
        """
        if node in self.nodes:
            return {'success': 0, 'message': 'node already exists!'}
        else:
            self.nodes[node] = properties
            if 'type' in properties:
                node_type = properties['type']
                if node_type in self.node_types:
                    self.node_types[node_type] += 1
                else:
                    self.node_types[node_type] = 1
            action = {'action': node_add_action, 'node': node, 'properties': copy.deepcopy(properties)}
            self.recent_changes.append(action)
            self.forget_changes()
            return {'success': 1, 'message': 'node added successfully!'}

    def find_edge_index(self, source, target):
        """

        :param source:
        :param target:
        :return:
        """
        if source not in self.nodes:
            return -1
        if target not in self.nodes:
            return -1
        if source not in self.adj_list:
            return -1
        if target not in self.in_adj_list:
            return -1
        out_edges = self.adj_list[source]
        in_edges = self.in_adj_list[target]
        if len(out_edges) < len(in_edges):
            for e_index in out_edges:
                if self.edges[e_index]['target'] == target:
                    return e_index
            return -1
        else:
            for e_index in in_edges:
                if self.edges[e_index]['source'] == source:
                    return e_index
            return -1

    def update_an_edge(self, e_index=None, source=None, target=None, is_index=True, properties=None):
        """

        :param e_index:
        :param source:
        :param target:
        :param is_index:
        :param properties:
        :return:
        """
        if properties is None:
            return {'success': 0, 'message': 'nothing to update!'}
        if is_index:
            if e_index is None:
                return {'success': 0, 'message': 'is_index is True but e_index is None!'}
            edge_properties = self.edges[e_index]['properties']
            pre_properties = copy.deepcopy(edge_properties)
            if edge_properties is None:
                self.edges[e_index]['properties'] = properties
                if 'type' in properties:
                    edge_type = properties['type']
                    if edge_type in self.edge_types:
                        self.edge_types[edge_type] += 1
                    else:
                        self.edge_types[edge_type] = 1
            else:
                type_change = False
                if 'type' in properties:
                    if 'type' in edge_properties:
                        if properties['type'] != edge_properties['type']:
                            type_change = True
                            edge_type = edge_properties['type']
                            self.edge_types[edge_type] -= 1
                            if self.edge_types[edge_type] == 0:
                                del self.edge_types[edge_type]
                edge_properties.clear()
                for p, value in properties.items():
                    edge_properties[p] = value

                if type_change:
                    edge_type = properties['type']
                    if edge_type in self.edge_types:
                        self.edge_types[edge_type] += 1
                    else:
                        self.edge_types[edge_type] = 1
            action = {'action': edge_update_action,
                      'edge': {'e_index': e_index,
                               'source': self.edges[e_index]['source'],
                               'target': self.edges[e_index]['target']},
                      'pre_properties': pre_properties}
            self.recent_changes.append(action)
            self.forget_changes()
            return {'success': 1, 'message': 'edge updated successfully!'}
        else:
            if source is None or target is None:
                return {'success': 0, 'message': 'source or target is None!'}
            e_index = self.find_edge_index(source, target)
            if e_index < 0:
                return {'success': 0, 'message': 'edge not found!'}
            edge_properties = self.edges[e_index]['properties']
            pre_properties = copy.deepcopy(edge_properties)
            if edge_properties is None:
                self.edges[e_index]['properties'] = properties
                if 'type' in properties:
                    edge_type = properties['type']
                    if edge_type in self.edge_types:
                        self.edge_types[edge_type] += 1
                    else:
                        self.edge_types[edge_type] = 1
            else:
                type_change = False
                if 'type' in properties:
                    if 'type' in edge_properties:
                        if properties['type'] != edge_properties['type']:
                            type_change = True
                            edge_type = edge_properties['type']
                            self.edge_types[edge_type] -= 1
                            if self.edge_types[edge_type] == 0:
                                del self.edge_types[edge_type]

                for p, value in properties.items():
                    edge_properties[p] = value

                if type_change:
                    edge_type = properties['type']
                    if edge_type in self.edge_types:
                        self.edge_types[edge_type] += 1
                    else:
                        self.edge_types[edge_type] = 1
            # remember the action
            action = {'action': edge_update_action,
                      'edge': {'e_index': e_index, 'source': source, 'target': target},
                      'pre_properties': pre_properties}
            self.recent_changes.append(action)
            self.forget_changes()
            return {'success': 1, 'message': 'edge updated successfully!'}

    def add_an_edge(self, source, target, properties=None):
        """

        :param source:
        :param target:
        :param properties:
        :return:
        """
        if source not in self.nodes:
            return {'success': 0, 'message': 'source not found!'}
        if target not in self.nodes:
            return {'success': 0, 'message': 'target not found!'}
        e_index = self.find_edge_index(source=source, target=target)
        if e_index >= 0:
            if helpers.compare_edge_type(self.edges[e_index]['properties'], properties):
                return {'success': 0, 'message': 'edge already exists!'}
        e_index = len(self.edges)
        if source in self.adj_list:
            self.adj_list[source].append(e_index)
        else:
            self.adj_list[source] = [e_index]
        if target in self.in_adj_list:
            self.in_adj_list[target].append(e_index)
        else:
            self.in_adj_list[target] = [e_index]
        edge = {'source': source, 'target': target, 'properties': properties}
        self.edges.append(edge)
        if 'type' in properties:
            edge_type = properties['type']
            if edge_type in self.edge_types:
                self.edge_types[edge_type] += 1
            else:
                self.edge_types[edge_type] = 1
        # remember the action
        action = {'action': edge_add_action,
                  'edge': {'e_index': e_index, 'source': source, 'target': target},
                  'properties': copy.deepcopy(properties)}
        self.recent_changes.append(action)
        self.forget_changes()
        return {'success': 1, 'message': 'edge added successfully!'}

    def delete_an_edge(self, e_index=None, source=None, target=None, is_index=True):
        """

        :param e_index:
        :param source:
        :param target:
        :param is_index:
        :return:
        """
        # print('delete_an_edge:', e_index, source, target, is_index)
        if is_index:
            if e_index is None:
                return {'success': 0, 'message': 'is_index is True but e_index is None!'}
            edge = self.edges[e_index]
            properties = copy.deepcopy(self.edges[e_index]['properties'])
            source, target = edge['source'], edge['target']
            # print('deleting e = {} source = {} target = {}'.format(e_index, source, target))
            # remove from adj lists
            # print('source: ', source)
            # print('self.adj_list: ', self.adj_list)
            if source in self.nodes:
                self.adj_list[source].remove(e_index)

            # print('target: ', target)
            # print('self.in_adj_list', self.in_adj_list)
            if target in self.nodes:
                self.in_adj_list[target].remove(e_index)
            # change edge types
            edge_type = edge['properties']['type']
            self.edge_types[edge_type] -= 1
            if self.edge_types[edge_type] == 0:
                del self.edge_types[edge_type]
            # remove the edge
            self.edges[e_index] = None  # TODO ask?????
            # remember the action
            action = {'action': edge_delete_action,
                      'edge': {'e_index': e_index, 'source': source, 'target': target},
                      'properties': properties}
            self.recent_changes.append(action)
            self.forget_changes()
            return {'success': 1, 'message': 'edge deleted successfully!'}
        else:
            if source is None or target is None:
                return {'success': 0, 'message': 'source or target is None!'}
            e_index = self.find_edge_index(source, target)
            if e_index >= 0:
                properties = copy.deepcopy(self.edges[e_index]['properties'])
                # remove from adj lists
                if source in self.nodes:
                    self.adj_list[source].remove(e_index)
                if target in self.nodes:
                    self.in_adj_list[target].remove(e_index)
                # change edge types
                edge_type = self.edges[e_index]['properties']['type']
                self.edge_types[edge_type] -= 1
                if self.edge_types[edge_type] == 0:
                    del self.edge_types[edge_type]
                # remove the edge
                self.edges[e_index] = None
                # remember action
                action = {'action': edge_delete_action,
                          'edge': {'e_index': e_index, 'source': source, 'target': target},
                          'properties': properties}
                self.recent_changes.append(action)
                self.forget_changes()
                return {'success': 1, 'message': 'edge deleted successfully!'}
            else:
                return {'success': 0, 'message': 'edge does not exist!'}

    def delete_edges(self, deleted_edges, is_indexes=True):
        """
        delete a list of edges from a network
        :param deleted_edges:
        :param is_indexes:
        :return: List of errors
        """
        errors = []
        result_temp = None
        if is_indexes:
            for e_index in deleted_edges:
                result_temp = self.delete_an_edge(e_index=e_index, is_index=True)
                if not result_temp["success"]:
                    result_temp["e_index"] = e_index
                    errors.append(result_temp)
        else:
            for edge in deleted_edges:
                source, target = edge
                result_temp = self.delete_an_edge(source=source, target=target, is_index=False)
                if not result_temp["success"]:
                    result_temp["edge"] = edge
                    errors.append(result_temp)
        return errors

    def delete_a_node(self, node):
        """
        delete the node by node id
        :param node:
        :return:
        """
        # print('delete_a_node: ', node)
        if node not in self.nodes:
            return {'success': 0, 'message': 'node not found!'}
        # delete out-going edges
        if node in self.adj_list:
            self.delete_edges(copy.deepcopy(self.adj_list[node]), is_indexes=True)
            del self.adj_list[node]
        # delete in-coming edges
        if node in self.in_adj_list:
            self.delete_edges(copy.deepcopy(self.in_adj_list[node]), is_indexes=True)
            del self.in_adj_list[node]
        # change the types
        if 'type' in self.nodes[node]['type']:
            node_type = self.nodes[node]['type']
            self.node_types[node_type] -= 1
            if self.node_types[node_type] == 0:
                del self.node_types[node_type]
        # remember the action
        properties = copy.deepcopy(self.nodes[node])
        action = {'action': node_delete_action, 'node': node, 'properties': properties}
        self.recent_changes.append(action)
        self.forget_changes()
        # delete the node
        del self.nodes[node]

        return {'success': 1, 'message': 'node deleted successfully!'}

    def delete_nodes(self, nodes):
        """
        delete a list of nodes and their adjacent edges from a network
        :param nodes:
        :return: List of errors
        """
        errors = []
        result_temp = None
        for node in nodes:
            result_temp = self.delete_a_node(node)
            if not result_temp["success"]:
                result_temp["node"] = node
                errors.append(result_temp)
        return errors
        # print('after delete ', node)
        # self.print_dataset()
        # print('*******************')

    def save_nodes(self, nodes, params=None):
        """
        add or update information for a list of nodes in a network
        :param nodes: dictionary of node_id: properties
        :param params:
        :return:
        """
        errors = []
        result_temp = None
        for node, properties in nodes.items():
            if node in self.nodes:
                result_temp = self.update_a_node(node, properties=properties)
            else:
                result_temp = self.add_a_node(node, properties=properties)
            if not result_temp["success"]:
                result_temp["node"] = node
                errors.append(result_temp)
        return errors

    def save_edges(self, edges, params=None):
        """
        create or update information for a list of edges in a network
        :param edges: list of edge object with 'source', 'target' and 'properties' fields
        :param params:
        :return:
        """
        errors = []
        result_temp = None
        for edge in edges:
            source, target, properties = edge['source'], edge['target'], edge['properties']
            e_index = self.find_edge_index(source, target)
            if e_index < 0:
                result_temp = self.add_an_edge(source, target, properties=properties)
            else:
                result_temp = self.update_an_edge(e_index=e_index, is_index=True, properties=properties)
            if not result_temp["success"]:
                result_temp["edge"] = {"source": source, "target": target}
                errors.append(result_temp)
        return errors

    def dump_network(self, network, output_dir, params=None):
        """
        dump the whole network to a specified directory
        will fail if file already exists
        """
        if not params:
            params = {}
        try:
            if not params.get("output_format") == "json":
                raise NotImplementedError()
            if params.get("compressed"):
                raise NotImplementedError()
            output_path = Path(output_dir) / network
            with open(output_path, "x") as output_file:
                for node in self.nodes:
                    temp = {
                        "id": node,
                        "type": "node",
                        "properties": self.nodes[node].copy()
                    }
                    json.dump(temp, output_file)
                    output_file.write("\n")
                for edge in self.edges:  # type weight confidence
                    e_props = edge["properties"]
                    if params.get("edge_types") and not (e_props.get("type") in params["edge_types"]):
                        continue
                    if params.get("min_weight") and e_props.get("weight", 0) < params["min_weight"]:
                        continue
                    if params.get("min_confidence") and e_props.get("confidence", 0) < params["min_confidence"]:
                        continue
                    temp = edge.copy()
                    temp["type"] = "edge"
                    json.dump(temp, output_file)
                    output_file.write("\n")
            return 1
        except Exception:
            return 0

    def get_neighbor_counts(self, nodes):
        neighbor_counts = {}
        if nodes is not None:
            for node in nodes:
                if node in self.adj_list:
                    for e_index in self.adj_list[node]:
                        target = self.edges[e_index]['target']
                        if target in neighbor_counts:
                            neighbor_counts[target] += 1
                        else:
                            neighbor_counts[target] = 1
        return neighbor_counts

    def to_nxgraph(self):
        """
        convert to networkx graph
        :return:
        """
        graph = nx.MultiDiGraph()
        graph.add_nodes_from(list(self.nodes.keys()))
        
        for e in self.edges:
            if e is not None:
                if 'weight' in e['properties']:
                    graph.add_edge(e['source'], e['target'], weight=float(e['properties']['weight']))
                else:
                    graph.add_edge(e['source'], e['target'])

        return graph

    def print_dataset(self):
        print('nodes: ', self.nodes)
        print('edges: ', self.edges)
        # print('adj_list: ', self.adj_list)
        # print('in_adj_list ',self.in_adj_list)
        print('node_types: ', self.node_types)
        print('edge_types: ', self.edge_types)
        print('actions: ', self.recent_changes)


#####################################
active_element_default_values = {
    'label': 'not_defined',
    'type': 'not_defined',
    'selected': False,
    'expandable': False,
    'community': -1,
    'community_confidence': -1,
    'social_influence_score': -1,
    'visualisation_social_influence_score': -1,
    'predicted': False,
    'hidden': False,
    'highlighted': False,
    'num_incoming_neighbor_selected': 0,
    'incoming_neighbor_selected': False,
    'source_selected': False
}


####################################


class ActiveNetwork(BuiltinDataset):
    """
    class for managing and manipulating network being processed by the visualizer
    """

    def __init__(self, path_2_data=None, uploaded=False, from_file=None, selected_nodes=None, initialize=False,
                 params=dict()):
        """

        :param path_2_data: path to data file
        :param uploaded: True if network is to be
        :param from_file: True if to read from local file, i.e., from path_2_data
        :param selected_nodes: list of selected nodes to initilize the active network
        :param initialize: True if to initialize the active network
        :param params: ditionary
        """
        if from_file is None:
            from_file = True if path_2_data else False
        BuiltinDataset.__init__(self, path_2_data, uploaded, from_file)
        self.active_nodes = {}  # dictionary of active nodes:{node_id: {'expandable':True/False,
        # 'element_index': index of
        # the corresponding element in self.elements}}

        self.active_edges = {}  # dictionary of active edge:{edge_index: {
        # 'element_index': index of
        # the corresponding element in self.elements}}

        self.elements = []
        #
        self.network_name = None
        self.node_label_field = None
        self.edge_label_field = None
        #
        self.analyzer = InMemoryAnalyzer()
        self.predicted_edges = {}  # dictionary {source:[]}
        self.active_predicted_edges = {}
        # dictionary of active predicted edge:{edge_index: {
        # 'element_index': index of
        # the corresponding element in self.elements}}

        self.last_analysis = None  # info about last analysis
        if initialize:
            self.initialize(selected_nodes, params)
        self.selected_nodes = set()
        self.selected_edges = set()
        self.recent_interactions = []

    def truncate(self, core_nodes, max_num=5000):
        if len(self.active_nodes) < max_num:
            return
        sampled_nodes = random.sample(list(self.active_nodes.keys()), max_num)
        sampled_nodes = set(sampled_nodes)
        if core_nodes is not None:
            sampled_nodes = sampled_nodes.union(set(core_nodes))

        self.active_nodes = dict([(node, None) for node in sampled_nodes])
        self.active_edges = dict([(e, None) for e in self.active_edges if
                                  self.edges[e]['source'] in self.active_nodes and
                                  self.edges[e]['target'] in self.active_nodes])

    ############################################
    def initialize(self, selected_nodes=None, params={}):
        # print('in initialize')
        # print('selected_nodes = ', selected_nodes)
        self.active_nodes = {}
        self.active_edges = {}
        self.elements = []
        self.predicted_edges = {}  # dictionary {source:[]}
        self.last_analysis = None  # info about last analysis

        if 'network_name' in params:
            self.network_name = params['network_name']
        else:
            self.network_name = 'sub-network'

        if 'node_label_field' in params:
            self.node_label_field = params['node_label_field']
        else:
            # TODO: to be refactored to remove hard coding
            self.node_label_field = 'name'

        if 'edge_label_field' in params:
            self.edge_label_field = params['edge_label_field']
        else:
            # TODO: to be refactored to remove hard coding
            self.edge_label_field = 'name'

        if selected_nodes and any(v in ('__all__', 'all', 'select_all', 'all_entities') for v in selected_nodes):
            selected_nodes = None
        sub_network = self.get_network(selected_nodes, return_edge_index=True)
        # print(sub_network)
        self.active_edges = dict([(e, None) for e in sub_network['edges']])
        self.active_nodes = dict([(node['id'], None) for node in sub_network['nodes']])
        self.truncate(selected_nodes)
        # added node
        for node in self.active_nodes:
            node_info = self.nodes[node]
            node_info['id'] = node
            # if self.node_label_field is not None:
            #     if self.node_label_field not in node_info:
            #         node_info[self.node_label_field] = active_element_default_values[self.node_label_field]
            # else:
            #     node_info['id'] = node
            node_data = {'element_type': 'node',
                         'id': node,
                         'type': node_info['type'],
                         'label': active_element_default_values['label'],
                         'selected': active_element_default_values['selected'],
                         'expandable': active_element_default_values['expandable'],
                         'community': active_element_default_values['community'],
                         'community_confidence': active_element_default_values['community_confidence'],
                         'social_influence_score': active_element_default_values['social_influence_score'],
                         'visualisation_social_influence_score':
                             active_element_default_values['visualisation_social_influence_score'],
                         'hidden': active_element_default_values['hidden'],
                         'highlighted': active_element_default_values['highlighted'],
                         'num_incoming_neighbor_selected': active_element_default_values[
                             'num_incoming_neighbor_selected'],
                         'incoming_neighbor_selected': active_element_default_values['incoming_neighbor_selected'],
                         'info': node_info}
            # add node label
            if self.node_label_field is not None:
                if self.node_label_field in node_info:
                    node_data['label'] = node_info[self.node_label_field]
                else:
                    node_data['label'] = node_data['id']
            else:
                node_data['label'] = node_data['id']
            # check expandability
            expandable = False
            if node in self.adj_list:
                for e_index in self.adj_list[node]:
                    if e_index not in self.active_edges:
                        expandable = True
                        break
            node_data['expandable'] = expandable

            element = {'group': 'nodes', 'data': node_data}

            self.elements.append(element)
            self.active_nodes[node] = {'expandable': expandable, 'element_index': len(self.elements) - 1}

        if self.edges and 'weight' in self.edges[0].get('properties', {}):
            min_weight = float('inf')
            max_weight = 0
            for edge in self.edges:
                if 'weight' in edge.get('properties', {}):
                    if edge['properties']['weight'] < min_weight:
                        min_weight = edge['properties']['weight']
                    elif edge['properties']['weight'] > max_weight:
                        max_weight = edge['properties']['weight']

        for e_index in self.active_edges:
            edge_info = self.edges[e_index]
            edge_data = {'element_type': 'edge',
                         'id': e_index,
                         'source': edge_info['source'],
                         'target': edge_info['target'],
                         'type': active_element_default_values['type'],
                         'label': active_element_default_values['label'],
                         'selected': active_element_default_values['selected'],
                         'predicted': active_element_default_values['predicted'],
                         'hidden': active_element_default_values['hidden'],
                         'highlighted': active_element_default_values['highlighted'],
                         'source_selected': active_element_default_values['source_selected'],
                         'info': edge_info['properties']}
            # add type
            if 'type' in edge_info['properties']:
                edge_data['type'] = edge_info['properties']['type']
            if 'probability' in edge_info['properties']:
                edge_data['probability'] = edge_info['properties']['probability']
            if 'weight' in edge_info['properties'] and max_weight > min_weight:
                edge_data['normalized_weight'] = (edge_info['properties']['weight'] - min_weight) / (max_weight - min_weight)
            # add edge label
            if self.edge_label_field is not None:
                if self.edge_label_field in edge_info:
                    edge_data['label'] = edge_info[self.edge_label_field]
            else:
                edge_data['label'] = ''  # blank label

            # Forensic Modality, Acceptance Status, & Provenance
            e_props = edge_info.get('properties', {})
            edge_data['modality'] = str(e_props.get('modality') or ('PREDICTED' if edge_data.get('predicted') else 'OBSERVED')).upper()
            edge_data['acceptance'] = str(e_props.get('acceptance') or e_props.get('acceptance_status') or ('PROPOSED' if edge_data.get('predicted') else 'CONFIRMED')).upper()
            if 'confidence' in e_props:
                edge_data['confidence'] = e_props['confidence']
            if 'provenance' in e_props:
                edge_data['provenance'] = e_props['provenance']
            if 'source_file' in e_props:
                edge_data['source_file'] = e_props['source_file']
            if 'quote' in e_props:
                edge_data['quote'] = e_props['quote']
            if 'db_id' in e_props:
                edge_data['db_id'] = e_props['db_id']

            element = {'group': 'edges', 'data': edge_data}
            self.elements.append(element)
            self.active_edges[e_index] = {'element_index': len(self.elements) - 1}

    def get_active_node_types(self):
        """
        get types of active nodes
        :return: list of type, each type is a string
        """
        types = set()
        for _, node_info in self.active_nodes.items():
            types.add(self.elements[node_info['element_index']]['data']['type'])
        return list(types)

    def get_active_edge_types(self):
        """
        get types of active edges
        :return: list of type, each type is a string
        """
        types = set()
        for _, edge_info in self.active_edges.items():
            types.add(self.elements[edge_info['element_index']]['data']['type'])
        if len(self.predicted_edges) > 0:
            types.add('predicted')
        return list(types)

    def get_active_element_types(self, element=None):
        """
        get types of active nodes or active edges
        :param element:
        :return:
        """
        if element is None:
            return {'node': self.get_active_node_types(), 'edge': self.get_active_edge_types()}
        elif element == 'node':
            return self.get_active_node_types()
        elif element == 'edge':
            return self.get_active_edge_types()
        else:
            return None

    def hide_elements(self, hide_all=False, node_types=None, edge_types=None,
                      element_indexes=None, nodes=None, edges=None):
        """

        :param hide_all:
        :param node_types: list of node types to hide
        :param edge_types: list of edge types to hide
        :param element_indexes:  list of element indexes to hide
        :param nodes: list of node ids to hide
        :param edges: list of edge ids to hide
        :return:
        """

        flag = True

        if hide_all:
            flag = False

        if node_types is not None:
            node_types = set(node_types)
            flag = False

        if edge_types is not None:
            edge_types = set(edge_types)
            flag = False

        if element_indexes is not None:
            element_indexes = set(element_indexes)
            flag = False

        if nodes is not None:
            nodes = set(nodes)
            flag = False

        if edges is not None:
            edges = set(edges)
            flag = False

        if flag:
            return

        for e in range(len(self.elements)):
            if hide_all:
                self.elements[e]['data']['hidden'] = True
            elif element_indexes is not None:
                if e in element_indexes:
                    self.elements[e]['data']['hidden'] = True
            elif edge_types is not None:
                if self.elements[e]['data']['type'] in edge_types:
                    self.elements[e]['data']['hidden'] = True
            elif node_types is not None:
                if self.elements[e]['data']['type'] in node_types:
                    self.elements[e]['data']['hidden'] = True
            elif nodes is not None:
                if self.elements[e]['data']['element_type'] == 'node':
                    if self.elements[e]['data']['id'] in nodes:
                        self.elements[e]['data']['hidden'] = True
            elif edges is not None:
                if self.elements[e]['data']['element_type'] == 'edge':
                    if self.elements[e]['data']['id'] in edges:
                        self.elements[e]['data']['hidden'] = True
            else:
                pass

    def unhide_elements(self, unhide_all=False, node_types=None, edge_types=None,
                        element_indexes=None, nodes=None, edges=None):
        """

        :param unhide_all:
        :param node_types: list of node types to unhide
        :param edge_types: list of edge types to unhide
        :param element_indexes:  list of element indexes to unhide
        :param nodes: list of node ids to unhide
        :param edges: list of edge ids to unhide
        :return:
        """

        flag = True

        if unhide_all:
            flag = False

        if node_types is not None:
            node_types = set(node_types)
            flag = False

        if edge_types is not None:
            edge_types = set(edge_types)
            flag = False

        if element_indexes is not None:
            element_indexes = set(element_indexes)
            flag = False

        if nodes is not None:
            nodes = set(nodes)
            flag = False

        if edges is not None:
            edges = set(edges)
            flag = False

        if flag:
            return

        for e in range(len(self.elements)):
            if unhide_all:
                self.elements[e]['data']['hidden'] = False
            elif element_indexes is not None:
                if e in element_indexes:
                    self.elements[e]['data']['hidden'] = False
            elif edge_types is not None:
                if self.elements[e]['data']['type'] in edge_types:
                    self.elements[e]['data']['hidden'] = False
            elif node_types is not None:
                if self.elements[e]['data']['type'] in node_types:
                    self.elements[e]['data']['hidden'] = False
            elif nodes is not None:
                if self.elements[e]['data']['element_type'] == 'node':
                    if self.elements[e]['data']['id'] in nodes:
                        self.elements[e]['data']['hidden'] = False
            elif edges is not None:
                if self.elements[e]['data']['element_type'] == 'edge':
                    if self.elements[e]['data']['id'] in edges:
                        self.elements[e]['data']['hidden'] = False
            else:
                pass

    def highlight_elements(self, highlight_all=False, node_types=None, edge_types=None,
                           element_indexes=None, nodes=None, edges=None):
        """

        :param highlight_all:
        :param node_types: list of node types to highlight
        :param edge_types: list of edge types to highlight
        :param element_indexes:  list of element indexes to highlight
        :param nodes: list of node ids to highlight
        :param edges: list of edge ids to highlight
        :return:
        """

        flag = True

        if highlight_all:
            flag = False

        if node_types is not None:
            node_types = set(node_types)
            flag = False

        if edge_types is not None:
            edge_types = set(edge_types)
            flag = False

        if element_indexes is not None:
            element_indexes = set(element_indexes)
            flag = False

        if nodes is not None:
            nodes = set(nodes)
            flag = False

        if edges is not None:
            edges = set(edges)
            flag = False

        if flag:
            return

        for e in range(len(self.elements)):
            if highlight_all:
                self.elements[e]['data']['highlighted'] = True
            elif element_indexes is not None:
                if e in element_indexes:
                    self.elements[e]['data']['highlighted'] = True
            elif edge_types is not None:
                if self.elements[e]['data']['type'] in edge_types:
                    self.elements[e]['data']['highlighted'] = True
            elif node_types is not None:
                if self.elements[e]['data']['type'] in node_types:
                    self.elements[e]['data']['highlighted'] = True
            elif nodes is not None:
                if self.elements[e]['data']['element_type'] == 'node':
                    if self.elements[e]['data']['id'] in nodes:
                        self.elements[e]['data']['highlighted'] = True
            elif edges is not None:
                if self.elements[e]['data']['element_type'] == 'edge':
                    if self.elements[e]['data']['id'] in edges:
                        self.elements[e]['data']['highlighted'] = True
            else:
                pass

    def unhighlight_elements(self, unhighlight_all=False, node_types=None, edge_types=None,
                             element_indexes=None, nodes=None, edges=None):
        """

        :param unhighlight_all:
        :param node_types: list of node types to unhighlight
        :param edge_types: list of edge types to unhighlight
        :param element_indexes:  list of element indexes to unhighlight
        :param nodes: list of node ids to unhighlight
        :param edges: list of edge ids to unhighlight
        :return:
        """

        flag = True

        if unhighlight_all:
            flag = False

        if node_types is not None:
            node_types = set(node_types)
            flag = False

        if edge_types is not None:
            edge_types = set(edge_types)
            flag = False

        if element_indexes is not None:
            element_indexes = set(element_indexes)
            flag = False

        if nodes is not None:
            nodes = set(nodes)
            flag = False

        if edges is not None:
            edges = set(edges)
            flag = False

        if flag:
            return

        for e in range(len(self.elements)):
            if unhighlight_all:
                self.elements[e]['data']['highlighted'] = False
            elif element_indexes is not None:
                if e in element_indexes:
                    self.elements[e]['data']['highlighted'] = False
            elif edge_types is not None:
                if self.elements[e]['data']['type'] in edge_types:
                    self.elements[e]['data']['highlighted'] = False
            elif node_types is not None:
                if self.elements[e]['data']['type'] in node_types:
                    self.elements[e]['data']['highlighted'] = False
            elif nodes is not None:
                if self.elements[e]['data']['element_type'] == 'node':
                    if self.elements[e]['data']['id'] in nodes:
                        self.elements[e]['data']['highlighted'] = False
            elif edges is not None:
                if self.elements[e]['data']['element_type'] == 'edge':
                    if self.elements[e]['data']['id'] in edges:
                        self.elements[e]['data']['highlighted'] = False
            else:
                pass

    def get_active_network_info(self):
        """
        get meta info about the active part of the network
        :return:
        """
        # num_nodes = len([e for e in self.elements if e['element_type': 'node'] == 'node'])
        # num_edges = len(self.elements) - num_nodes
        num_nodes = len(self.active_nodes)
        num_edges = len(self.active_edges)

        return {'network_name': self.network_name, 'num_nodes': num_nodes, 'num_edges': num_edges}

    def get_selected_nodes(self):
        """

        :return: list of all selected nodes
        """
        # print('selected nodes = ', self.selected_nodes)
        return list(self.selected_nodes)

    def get_selected_edges(self):
        """

        :return: list of selected edges
        """
        return list(self.selected_edges)

    def expand_nodes(self, node_ids, get_change=False):
        """
        adding the neighbors of nodes in node_ids into element list
        :param node_ids:
        :return:
        """

        sub_network = self.get_network(node_ids, return_edge_index=True)
        added_edges = set([e_index for e_index in sub_network['edges'] if e_index not in self.active_edges])
        added_nodes = set([node['id'] for node in sub_network['nodes'] if node['id'] not in self.active_nodes])

        if 'weight' in self.edges[0]['properties']:
            min_weight = float('inf')
            max_weight = 0
            for edge in self.edges:
                if 'weight' in edge['properties']:
                    if edge['properties']['weight'] < min_weight:
                        min_weight = edge['properties']['weight']
                    elif edge['properties']['weight'] > max_weight:
                        max_weight = edge['properties']['weight']

        if get_change:
            # check expandability of existing nodes
            changed_expandability_nodes = set()
            for node in self.active_nodes:
                expandable = False
                if node in self.adj_list:
                    for e_index in self.adj_list[node]:
                        if e_index in self.active_edges:
                            continue
                        if e_index in added_edges:
                            continue
                        expandable = True
                        break
                an_info = self.active_nodes[node]  # active node's info
                if an_info['expandable'] != expandable:
                    changed_expandability_nodes.add(node)
            # added elements
            added_elements = []
            added_elements_indexes = {}
            for node in added_nodes:
                # added node
                node_info = self.nodes[node]
                node_data = {'element_type': 'node',
                             'id': node,
                             'type': node_info['type'],
                             'label': active_element_default_values['label'],
                             'selected': active_element_default_values['selected'],
                             'expandable': active_element_default_values['expandable'],
                             'community': active_element_default_values['community'],
                             'community_confidence': active_element_default_values['community_confidence'],
                             'social_influence_score': active_element_default_values['social_influence_score'],
                             'visualisation_social_influence_score':
                                 active_element_default_values['visualisation_social_influence_score'],
                             'hidden': active_element_default_values['hidden'],
                             'highlighted': active_element_default_values['highlighted'],
                             'num_incoming_neighbor_selected': active_element_default_values[
                                 'num_incoming_neighbor_selected'],
                             'incoming_neighbor_selected': active_element_default_values['incoming_neighbor_selected'],
                             'info': node_info}

                # add label
                if self.node_label_field is not None:
                    if self.node_label_field in node_info:
                        node_data['label'] = node_info[self.node_label_field]
                else:
                    node_data['label'] = node_data['id']
                # check expandability
                expandable = False
                if node in self.adj_list:
                    for e_index in self.adj_list[node]:
                        if e_index in self.active_edges:
                            continue
                        if e_index in added_edges:
                            continue
                        expandable = True
                        break

                node_data['expandable'] = expandable
                element = {'group': 'nodes', 'data': node_data}
                added_elements.append(element)
                added_elements_indexes[node] = len(added_elements) - 1

            for e_index in added_edges:
                edge_info = self.edges[e_index]
                edge_data = {'element_type': 'edge',
                             'id': e_index, 'source': edge_info['source'],
                             'type': active_element_default_values['type'],
                             'label': active_element_default_values['label'],
                             'selected': False,
                             'predicted': active_element_default_values['predicted'],
                             'target': edge_info['target'],
                             'hidden': active_element_default_values['hidden'],
                             'highlighted': active_element_default_values['highlighted'],
                             'source_selected': active_element_default_values['source_selected'],
                             'info': edge_info['properties']}
                # add type
                if 'type' in edge_info['properties']:
                    edge_data['type'] = edge_info['properties']['type']

                # add probability
                if 'probability' in edge_info['properties']:
                    edge_data['probability'] = edge_info['properties']['probability']

                # add weight
                if 'weight' in edge_info['properties'] and max_weight > min_weight:
                    edge_data['normalized_weight'] = (edge_info['properties']['weight'] - min_weight) / (
                                max_weight - min_weight)

                # add label
                if self.edge_label_field is not None:
                    if self.edge_label_field in edge_info:
                        edge_data['label'] = edge_info[self.edge_label_field]
                else:
                    edge_data['label'] = ''  # blank label

                # add source selected
                source = edge_info['source']
                if source in self.active_nodes:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        edge_data['source_selected'] = True

                element = {'group': 'edges', 'data': edge_data}
                added_elements.append(element)

                # change incoming neighbor selected in target
                source = edge_info['source']
                if source in self.active_nodes:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:

                        target = edge_info['target']
                        if target in added_elements_indexes:
                            added_elements[added_elements_indexes[target]]['data'][
                                'num_incoming_neighbor_selected'] += 1
                            added_elements[added_elements_indexes[target]]['data']['incoming_neighbor_selected'] = True

            result = {'success': 1, 'message': 'Successful', 'changed_expandability': changed_expandability_nodes,
                      'added_nodes': added_nodes, 'added_edges': added_edges, 'added_elements': added_elements}
            return result

        else:  # update directly
            self.erase_previous_analysis_result(task_id='social_influence_analysis')
            self.erase_previous_analysis_result(task_id='community_detection')
            self.erase_previous_analysis_result(task_id='link_prediction')
            self.last_analysis = None
            # check expandability of existing nodes
            for node in self.active_nodes:
                expandable = False
                if node in self.adj_list:
                    for e_index in self.adj_list[node]:
                        if e_index in self.active_edges:
                            continue
                        if e_index in added_edges:
                            continue
                        expandable = True
                        break
                an_info = self.active_nodes[node]  # active node's info
                self.elements[an_info['element_index']]['data']['expandable'] = expandable
                an_info['expandable'] = expandable

            for node in added_nodes:
                # added node
                node_info = self.nodes[node]
                node_data = {'element_type': 'node',
                             'id': node,
                             'type': node_info['type'],
                             'selected': active_element_default_values['selected'],
                             'expandable': active_element_default_values['expandable'],
                             'community': active_element_default_values['community'],
                             'community_confidence': active_element_default_values['community_confidence'],
                             'social_influence_score': active_element_default_values['social_influence_score'],
                             'visualisation_social_influence_score':
                                 active_element_default_values['visualisation_social_influence_score'],
                             'hidden': active_element_default_values['hidden'],
                             'highlighted': active_element_default_values['highlighted'],
                             'num_incoming_neighbor_selected': active_element_default_values[
                                 'num_incoming_neighbor_selected'],
                             'incoming_neighbor_selected': active_element_default_values['incoming_neighbor_selected'],
                             'info': node_info}
                # add label
                if self.node_label_field is not None:
                    if self.node_label_field in node_info:
                        node_data['label'] = node_info[self.node_label_field]
                else:
                    node_data['label'] = node_data['id']
                # check expandability
                expandable = False
                if node in self.adj_list:
                    for e_index in self.adj_list[node]:
                        if e_index in self.active_edges:
                            continue
                        if e_index in added_edges:
                            continue
                        expandable = True
                        break
                node_data['expandable'] = expandable
                element = {'group': 'nodes', 'data': node_data}
                self.elements.append(element)
                self.active_nodes[node] = {'expandable': expandable, 'element_index': len(self.elements) - 1}

            for e_index in added_edges:
                # added edge
                edge_info = self.edges[e_index]
                edge_data = {'element_type': 'edge',
                             'id': e_index, 'source': edge_info['source'],
                             'type': active_element_default_values['type'],
                             'label': active_element_default_values['label'],
                             'selected': active_element_default_values['selected'],
                             'predicted': active_element_default_values['predicted'],
                             'target': edge_info['target'],
                             'hidden': active_element_default_values['hidden'],
                             'highlighted': active_element_default_values['highlighted'],
                             'source_selected': active_element_default_values['source_selected'],
                             'info': edge_info['properties']}
                # add type
                if 'type' in edge_info['properties']:
                    edge_data['type'] = edge_info['properties']['type']
                if 'probability' in edge_info['properties']:
                    edge_data['probability'] = edge_info['properties']['probability']
                # add label
                if self.edge_label_field is not None:
                    if self.edge_label_field in edge_info:
                        edge_data['label'] = edge_info[self.edge_label_field]

                if 'weight' in edge_info['properties'] and max_weight > min_weight:
                    edge_data['normalized_weight'] = (edge_info['properties']['weight'] - min_weight) / (
                                max_weight - min_weight)

                else:
                    edge_data['label'] = ''  # blank label

                # Forensic Modality, Acceptance Status, & Provenance
                e_props = edge_info.get('properties', {})
                edge_data['modality'] = str(e_props.get('modality') or ('PREDICTED' if edge_data.get('predicted') else 'OBSERVED')).upper()
                edge_data['acceptance'] = str(e_props.get('acceptance') or e_props.get('acceptance_status') or ('PROPOSED' if edge_data.get('predicted') else 'CONFIRMED')).upper()
                if 'confidence' in e_props:
                    edge_data['confidence'] = e_props['confidence']
                if 'provenance' in e_props:
                    edge_data['provenance'] = e_props['provenance']
                if 'source_file' in e_props:
                    edge_data['source_file'] = e_props['source_file']
                if 'quote' in e_props:
                    edge_data['quote'] = e_props['quote']
                if 'db_id' in e_props:
                    edge_data['db_id'] = e_props['db_id']

                element = {'group': 'edges', 'data': edge_data}

                # add source selected
                source = edge_info['source']
                if source in self.active_nodes:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        edge_data['source_selected'] = True

                self.elements.append(element)
                self.active_edges[e_index] = {'element_index': len(self.elements) - 1}

                # change incoming neighbor selected in target
                source = edge_info['source']
                if source in self.active_nodes:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        target = edge_info['target']
                        if target in self.active_nodes:
                            target_element_index = self.active_nodes[target]['element_index']
                            target_element = self.elements[target_element_index]['data']
                            target_element['num_incoming_neighbor_selected'] += 1
                            target_element['incoming_neighbor_selected'] = True

            result = {'success': 1, 'message': 'Successful'}
            return result

    def remove_element(self, element_indexes):
        """
        remove the elements at position element_indexes from element list
        :param element_indexes:
        :return:
        """
        # print('element_indexes = ', element_indexes)
        element_indexes.sort(reverse=True)  # to save computation when left shifting the elements
        # print('element_indexes = ', element_indexes)
        for element_index in element_indexes:
            # print('\t', element_index, '\t', len(self.elements), '\t', element_indexes)
            element = self.elements[element_index]
            if element['data']['element_type'] == 'node':
                # remove an active node
                self.active_nodes.pop(element['data']['id'])
            else:
                # remove an active edge
                if not element['data']['predicted']:
                    # an observed edge
                    self.active_edges.pop(element['data']['id'])
                else:
                    source = element['data']['source']
                    self.predicted_edges[source].remove(element_index)

            if element_index < len(self.elements) - 1:  # not the last element
                # then shift the subsequent elements to the left
                for i in range(element_index, len(self.elements) - 1, 1):
                    self.elements[i] = self.elements[i + 1]
                    # update the element_index in active nodes and active edges
                    if self.elements[i]['data']['element_type'] == 'node':
                        node_id = self.elements[i]['data']['id']
                        self.active_nodes[node_id]['element_index'] = i
                    else:
                        if not self.elements[i]['data']['predicted']:
                            e_index = self.elements[i]['data']['id']
                            self.active_edges[e_index]['element_index'] = i
                        else:
                            source = self.elements[i]['data']['source']
                            self.predicted_edges[source].remove(i + 1)
                            self.predicted_edges[source].append(i)
                            pass
            else:
                # TODO: check this
                pass
            del self.elements[-1]

    def deactivate_nodes(self, node_ids, get_change=False):
        """
        removing the nodes and its adjacent edges from the active network
        :param node_ids:
        :return:
        """
        sub_network = self.get_network(node_ids, return_edge_index=True)
        node_ids = set(node_ids)
        removed_edges = set([e_index for e_index in sub_network['edges'] if
                             (self.edges[e_index]['source'] in node_ids or
                              self.edges[e_index]['target'] in node_ids) and e_index in self.active_edges])

        if get_change:
            # check expandability of existing nodes
            changed_expandability_nodes = set()
            # check incomming neighbor selected
            changed_incoming_neighbor_selected_nodes = set()

            removed_elements = []
            for e_index in removed_edges:
                removed_elements.append(self.active_edges[e_index]['element_index'])
                source, target = self.edges[e_index]['source'], self.edges[e_index]['target']
                # check incomming neighbor selected
                if source in node_ids:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        if target in self.active_nodes:
                            target_element_index = self.active_nodes[target]['element_index']
                            if self.elements[target_element_index]['data']['num_incoming_neighbor_selected'] == 1:
                                changed_incoming_neighbor_selected_nodes.add(target)
                # check expandability of existing nodes
                if source in self.active_nodes:
                    if target in node_ids:
                        if not self.active_nodes[source]['expandable']:
                            changed_expandability_nodes.add(source)
            for node in node_ids:
                if node in self.active_nodes:
                    removed_elements.append(self.active_nodes[node]['element_index'])

            result = {'success': 1, 'message': 'Successful',
                      'changed_incoming_neighbor_selected': changed_incoming_neighbor_selected_nodes,
                      'changed_expandability': changed_expandability_nodes,
                      'removed_elements': removed_elements, 'removed_edges': removed_edges}
            return result
        else:  # update directly
            self.erase_previous_analysis_result(task_id='social_influence_analysis')
            self.erase_previous_analysis_result(task_id='community_detection')
            self.erase_previous_analysis_result(task_id='link_prediction')
            self.last_analysis = None
            #####################
            removed_elements = []
            for e_index in removed_edges:
                # the edge element to be removed
                removed_elements.append(self.active_edges[e_index]['element_index'])

                source, target = self.edges[e_index]['source'], self.edges[e_index]['target']
                # check incomming neighbor selected
                if source in node_ids:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        if target in self.active_nodes:
                            target_element_index = self.active_nodes[target]['element_index']
                            target_element = self.elements[target_element_index]['data']
                            num_incoming_neighbor_selected = target_element['num_incoming_neighbor_selected']
                            if num_incoming_neighbor_selected > 0:
                                num_incoming_neighbor_selected -= 1
                            target_element['num_incoming_neighbor_selected'] = num_incoming_neighbor_selected
                            if num_incoming_neighbor_selected == 0:
                                target_element['incoming_neighbor_selected'] = False

                # check the expandability of existing nodes
                if source in self.active_nodes:
                    if target in node_ids:
                        if not self.active_nodes[source]['expandable']:
                            an_info = self.active_nodes[source]
                            an_info['expandable'] = True
                            self.elements[an_info['element_index']]['data']['expandable'] = True

            for node in node_ids:
                if node in self.active_nodes:
                    removed_elements.append(self.active_nodes[node]['element_index'])
                    # remove the node from selected nodes
                    if node in self.selected_nodes:
                        self.selected_nodes.remove(node)
            self.remove_element(removed_elements)
            result = {'success': 1, 'message': 'Successful'}
            return result

    def deactivate_edges(self, edge_ids, get_change=False):
        """
        removing the edges from active network
        :param edge_ids:
        :return:
        """
        edge_ids = set(edge_ids)
        removed_edges = set([e_index for e_index in edge_ids if e_index in self.active_edges])

        if get_change:
            removed_elements = []
            changed_incoming_neighbor_selected_nodes = set()
            for e_index in removed_edges:
                removed_elements.append(self.active_edges[e_index]['element_index'])
                source, target = self.edges[e_index]['source'], self.edges[e_index]['target']
                # check incomming neighbor selected
                if source in self.active_nodes:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        if target in self.active_nodes:
                            target_element_index = self.active_nodes[target]['element_index']
                            if self.elements[target_element_index]['data']['num_incoming_neighbor_selected'] == 1:
                                changed_incoming_neighbor_selected_nodes.add(target)

            result = {'success': 1, 'message': 'Successful',
                      'changed_incoming_neighbor_selected': changed_incoming_neighbor_selected_nodes,
                      'removed_elements': removed_elements, 'removed_edges': removed_edges}
            return result
        else:  # update directly
            self.erase_previous_analysis_result(task_id='social_influence_analysis')
            self.erase_previous_analysis_result(task_id='community_detection')
            self.erase_previous_analysis_result(task_id='link_prediction')
            self.last_analysis = None
            #####################
            removed_elements = []
            for e_index in removed_edges:
                # the edge element to be removed
                removed_elements.append(self.active_edges[e_index]['element_index'])

                source, target = self.edges[e_index]['source'], self.edges[e_index]['target']
                # check incomming neighbor selected
                if source in self.active_nodes:
                    source_element_index = self.active_nodes[source]['element_index']
                    source_element = self.elements[source_element_index]['data']
                    if source_element['selected']:
                        if target in self.active_nodes:
                            target_element_index = self.active_nodes[target]['element_index']
                            target_element = self.elements[target_element_index]['data']
                            num_incoming_neighbor_selected = target_element['num_incoming_neighbor_selected']
                            if num_incoming_neighbor_selected > 0:
                                num_incoming_neighbor_selected -= 1
                            target_element['num_incoming_neighbor_selected'] = num_incoming_neighbor_selected
                            if num_incoming_neighbor_selected == 0:
                                target_element['incoming_neighbor_selected'] = False
                # remove the edge from the selected set
                if e_index in self.selected_edges:
                    self.selected_edges.remove(e_index)

            self.remove_element(removed_elements)
            result = {'success': 1, 'message': 'Successful'}
            return result

    def remove_predicted_edges(self, source_ids=None):
        """
        remove predicted edges starting from nodes in source_ids
        :param source_ids:
        :return:
        """
        for node in source_ids:
            if node in self.predicted_edges:
                # print('edges to be removed: ', self.predicted_edges[node])
                self.remove_element(copy.deepcopy(self.predicted_edges[node]))
                del self.predicted_edges[node]

    def toggle_node_selection(self, node_id):
        """
        change the selected property of node and its outgoing edges
        :param node_id:
        :return:
        """
        if node_id not in self.active_nodes:
            pass
        # change at node
        element_index = self.active_nodes[node_id]['element_index']
        element = self.elements[element_index]
        element['data']['selected'] = not element['data']['selected']
        selected = element['data']['selected']

        # change at adjacent true edge and neighbors
        if node_id in self.adj_list:
            for e_index in self.adj_list[node_id]:
                if e_index not in self.active_edges:
                    continue
                # change at edge
                edge_element_index = self.active_edges[e_index]['element_index']
                edge_element = self.elements[edge_element_index]['data']
                edge_element['source_selected'] = selected

                #
                target = self.edges[e_index]['target']
                if target in self.active_nodes:
                    target_element_index = self.active_nodes[target]['element_index']
                    target_element = self.elements[target_element_index]['data']
                    if selected:
                        target_element['num_incoming_neighbor_selected'] += 1
                        target_element['incoming_neighbor_selected'] = True
                    else:
                        target_element['num_incoming_neighbor_selected'] -= 1
                        if target_element['num_incoming_neighbor_selected'] <= 0:
                            target_element['num_incoming_neighbor_selected'] = 0
                            target_element['incoming_neighbor_selected'] = False

        # change at predicted edges
        if node_id in self.predicted_edges:
            for element_index in self.predicted_edges[node_id]:
                element = self.elements[element_index]
                element['data']['source_selected'] = not element['data']['source_selected']

        if selected:
            self.selected_nodes.add(node_id)
            return 'selected'
        else:
            self.selected_nodes.remove(node_id)
            return 'unselected'

    def toggle_edge_selection(self, edge_id):
        """
        change the selected property of node and its outgoing edges
        :param edge_id:
        :return:
        """
        if edge_id is None:
            return
        if type(edge_id) == str:
            try:
                edge_id = int(edge_id)
            except ValueError:
                print('cannot cast "{}" to a number'.format(edge_id))
                print('looks like the clicked-on edge is a predicted one!')
                return
        if edge_id in self.active_edges:
            # change at edge
            # print('before: ', self.selected_edges)
            element_index = self.active_edges[edge_id]['element_index']
            element = self.elements[element_index]
            element['data']['selected'] = not element['data']['selected']
            selected = element['data']['selected']
            if selected:
                self.selected_edges.add(edge_id)
                return 'selected'
            else:
                self.selected_edges.remove(edge_id)
                return 'unselected'
            # print('after: ', self.selected_edges)

    @staticmethod
    def _merge_class(existing_classes, new_class=""):
        exclude = {
            'crimenet-focus-pair', 'crimenet-intermediary', 'crimenet-focus-edge',
            'crimenet-nhop-node', 'crimenet-nhop-edge', 'crimenet-dimmed',
            'crimenet-cluster-node', 'crimenet-cluster-edge'
        }
        tokens = [t for t in (existing_classes or '').split() if t not in exclude]
        if new_class and new_class not in tokens:
            tokens.append(new_class)
        return " ".join(tokens)

    def erase_previous_analysis_result(self, task_id, node_ids=None):
        """
        :param task_id:
        :param node_ids:
        :return:
        """
        if task_id == 'social_influence_analysis':
            self.last_influence_result = None
            for element in self.elements:
                if element.get('data', {}).get('element_type') == 'node':
                    element['data']['social_influence_score'] = active_element_default_values['social_influence_score']
                    element['data']['visualisation_social_influence_score'] = \
                        active_element_default_values['visualisation_social_influence_score']
                    if 'classes' in element:
                        element['classes'] = self._merge_class(element['classes'], '')
                elif element.get('data', {}).get('element_type') == 'edge':
                    if 'classes' in element:
                        element['classes'] = self._merge_class(element['classes'], '')
        ##############
        elif task_id == 'community_detection':
            self.last_community_result = None
            for element in self.elements:
                if element.get('data', {}).get('element_type') == 'node':
                    element['data']['community'] = active_element_default_values['community']
                    element['data']['community_confidence'] = active_element_default_values['community_confidence']
                    if 'info' in element['data'] and isinstance(element['data']['info'], dict):
                        element['data']['info'].pop('community', None)
                        element['data']['info'].pop('community_confidence', None)
                    if 'classes' in element:
                        element['classes'] = self._merge_class(element['classes'], '')
                elif element.get('data', {}).get('element_type') == 'edge':
                    if 'classes' in element:
                        element['classes'] = self._merge_class(element['classes'], '')
        ##############
        elif task_id == 'path_analysis':
            self.last_path_result = None
            for element in self.elements:
                if 'classes' in element:
                    element['classes'] = self._merge_class(element['classes'], '')
        ##############
        elif task_id == 'link_prediction':
            if node_ids is None:
                node_ids = set(self.active_nodes.keys())
            self.remove_predicted_edges(node_ids)
        ##############
        elif task_id == 'node_embedding':
            return
        ##############
        else:
            print('task {} is not supported', task_id)

    #################################
    def get_active_edges(self, no_hidden_edges=True):
        """
        get list of edges
        :return:
        """
        if no_hidden_edges:
            edges = []
            for j in self.active_edges:
                element_index = self.active_edges[j]['element_index']
                element = self.elements[element_index]
                if not element['data']['hidden']:
                    edges.append(self.edges[j])
            return edges

        else:
            edges = [self.edges[j] for j in self.active_edges]
            return edges

    def compare_tasks(self, task):
        # TODO: to check more on parameters

        if self.last_analysis is None:
            return False
        if self.last_analysis['task_id'] == 'link_prediction':
            return False
        if self.last_analysis['task_id'] != task['task_id']:
            return False
        if self.last_analysis['options']['method'] != task['options']['method']:
            return False
        if task['task_id'] == 'community_detection':
            if 'K' in task['options']['parameters']:
                if 'K' in self.last_analysis['options']['parameters']:
                    if self.last_analysis['options']['parameters']['K'] != task['options']['parameters']['K']:
                        return False
        return True

    def apply_analysis(self, task_id, method, params, get_result=False, add_default_params=True, scope='FULL_NETWORK'):
        """
        perform analysis on the active network and update the according properties of elements
        supporting scopes: 'FULL_NETWORK', 'SELECTED_ENTITY', 'SELECTED_SUBGRAPH', 'SELECTED_PAIR'
        """
        if params is None:
            params = {}
        scope = str(params.get('scope') or scope or 'FULL_NETWORK').upper()

        node_meta = {}
        for n in self.active_nodes:
            if n in self.active_nodes and self.active_nodes[n]['element_index'] < len(self.elements):
                el_data = self.elements[self.active_nodes[n]['element_index']].get('data', {})
                lbl = el_data.get('label') or el_data.get('name') or n
                ntype = el_data.get('type') or (el_data.get('info', {}).get('type') if isinstance(el_data.get('info'), dict) else 'person') or 'person'
                node_meta[n] = {'label': str(lbl), 'name': str(lbl), 'type': str(ntype)}

        # Determine target nodes and edges based on requested execution scope
        all_active_edges = self.get_active_edges()
        all_active_nodes = list(self.active_nodes.keys())

        if scope == 'SELECTED_SUBGRAPH':
            subgraph_nodes = [n for n in self.selected_nodes if n in self.active_nodes]
            if len(subgraph_nodes) < 2:
                res = {'success': 0, 'message': 'Selected Subgraph scope requires selecting at least 2 connected nodes on the graph.'}
                self.last_analysis_message = res['message']
                return res
            subgraph_edges = [
                e for e in all_active_edges
                if str(e.get('source')) in subgraph_nodes and str(e.get('target')) in subgraph_nodes
            ]
            network = {
                'edges': subgraph_edges,
                'nodes': subgraph_nodes,
                'node_metadata': {n: node_meta[n] for n in subgraph_nodes if n in node_meta}
            }
        elif scope == 'SELECTED_ENTITY':
            entity = None
            if params and params.get('entity'):
                entity = str(params['entity'])
            elif self.selected_nodes:
                entity = str(list(self.selected_nodes)[0])
            if not entity or entity not in self.active_nodes:
                res = {'success': 0, 'message': 'Selected Entity scope requires clicking an entity node on the graph to focus.'}
                self.last_analysis_message = res['message']
                return res

            if task_id == 'social_influence_analysis' and method in ('pagerank', 'pagerank_centrality'):
                params['personalization'] = {entity: 1.0}
            elif task_id == 'path_analysis' and method in ('n_hop', 'nhop'):
                params['root'] = entity

            network = {
                'edges': all_active_edges,
                'nodes': all_active_nodes,
                'node_metadata': node_meta
            }
        elif scope == 'SELECTED_PAIR':
            source = params.get('source')
            target = params.get('target')
            if (not source or not target) and len(self.selected_nodes) >= 2:
                sel_list = list(self.selected_nodes)
                source = str(sel_list[0])
                target = str(sel_list[1])
                params['source'] = source
                params['target'] = target
            if not source or not target:
                res = {'success': 0, 'message': 'Selected Pair scope requires selecting exactly 2 entities (source and target) on the graph.'}
                self.last_analysis_message = res['message']
                return res

            network = {
                'edges': all_active_edges,
                'nodes': all_active_nodes,
                'node_metadata': node_meta
            }
        else:
            # FULL_NETWORK
            if task_id == 'path_analysis' and method in ('shortest_path', 'path', 'all_paths'):
                if not params.get('source') or not params.get('target'):
                    if len(self.selected_nodes) >= 2:
                        sel_list = list(self.selected_nodes)
                        params['source'] = str(sel_list[0])
                        params['target'] = str(sel_list[1])
                    else:
                        res = {'success': 0, 'message': 'Shortest path analysis requires selecting 2 entities on the graph, or specifying source & target.'}
                        self.last_analysis_message = res['message']
                        return res
            elif task_id == 'path_analysis' and method in ('n_hop', 'nhop'):
                if not params.get('root') and not params.get('source'):
                    if self.selected_nodes:
                        params['root'] = str(list(self.selected_nodes)[0])
                    else:
                        res = {'success': 0, 'message': 'N-Hop neighborhood analysis requires selecting a root entity on the graph.'}
                        self.last_analysis_message = res['message']
                        return res

            network = {
                'edges': all_active_edges,
                'nodes': all_active_nodes,
                'node_metadata': node_meta
            }

        if add_default_params:
            if task_id == 'link_prediction' and not params.get('sources'):
                params['sources'] = list(self.selected_nodes)

        options = {'method': method, 'parameters': params}
        task = {
            'task_id': task_id,
            'network': network,
            'options': options
        }

        if get_result:
            result = self.analyzer.perform_analysis(task=task, params=None)
            return result

        result = self.analyzer.perform_analysis(task=task, params=None)
        if not result or result.get('success') == 0:
            self.last_analysis_message = result.get('message', 'Analysis could not be performed.') if result else 'Analysis failed.'
            return result or {'success': 0, 'message': 'Analysis failed.'}

        self.last_analysis_message = None
        self.last_analysis = {'task_id': task['task_id'], 'options': task['options']}
        self.last_analysis_result = result

        #################################
        # 1. SOCIAL INFLUENCE ANALYSIS
        #################################
        if task_id == 'social_influence_analysis':
            self.erase_previous_analysis_result(task_id='social_influence_analysis')
            self.erase_previous_analysis_result(task_id='community_detection')
            self.erase_previous_analysis_result(task_id='path_analysis')
            self.last_influence_result = result
            scores = result.get('scores', {})
            if scores:
                score_values = [v for v in scores.values() if v is not None]
                min_score = min(score_values) if score_values else 0.0
                max_score = max(score_values) if score_values else 1.0
                sorted_scores = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
                top_nodes = set(str(k) for k, v in sorted_scores[:5] if v > 0)

                for node in scores:
                    if node in self.active_nodes:
                        element_index = self.active_nodes[node]['element_index']
                        element = self.elements[element_index]
                        score = scores[node]
                        element['data']['social_influence_score'] = score
                        element['data']['visualisation_social_influence_score'] = helpers.min_max_scaling(
                            score, min_score, max_score, (0.2, 0.99)
                        )
                        if str(node) in top_nodes:
                            element['classes'] = self._merge_class(element.get('classes', ''), 'crimenet-cluster-node')

        #################################
        # 2. COMMUNITY DETECTION
        #################################
        elif task_id == 'community_detection':
            self.erase_previous_analysis_result(task_id='social_influence_analysis')
            self.erase_previous_analysis_result(task_id='community_detection')
            self.erase_previous_analysis_result(task_id='path_analysis')
            self.last_community_result = result
            membership = result.get('membership', {})
            entity_target_comm = None
            if scope == 'SELECTED_ENTITY' and self.selected_nodes:
                entity = str(list(self.selected_nodes)[0])
                if entity in membership:
                    entity_target_comm = list(membership[entity].keys())[0]

            for node in membership:
                if node in self.active_nodes:
                    element_index = self.active_nodes[node]['element_index']
                    element = self.elements[element_index]
                    c, m = list(membership[node].items())[0]
                    element['data']['community'] = c
                    element['data']['community_confidence'] = m
                    if 'info' not in element['data'] or not isinstance(element['data']['info'], dict):
                        element['data']['info'] = {}
                    element['data']['info']['community'] = str(c)
                    element['data']['info']['community_confidence'] = str(m)
                    if node in self.nodes and isinstance(self.nodes[node], dict):
                        self.nodes[node]['community'] = c

                    if entity_target_comm is not None:
                        if c == entity_target_comm:
                            element['classes'] = self._merge_class(element.get('classes', ''), 'crimenet-cluster-node')
                        else:
                            element['classes'] = self._merge_class(element.get('classes', ''), 'crimenet-dimmed')

            if entity_target_comm is not None:
                for el in self.elements:
                    if el.get('group') == 'edges':
                        esrc = str(el.get('data', {}).get('source', ''))
                        etgt = str(el.get('data', {}).get('target', ''))
                        src_c = list(membership.get(esrc, {}).keys())[0] if esrc in membership else None
                        tgt_c = list(membership.get(etgt, {}).keys())[0] if etgt in membership else None
                        if src_c == entity_target_comm and tgt_c == entity_target_comm:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-cluster-edge')
                        else:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')

        #################################
        # 3. PATH ANALYSIS
        #################################
        elif task_id == 'path_analysis':
            self.erase_previous_analysis_result(task_id='social_influence_analysis')
            self.erase_previous_analysis_result(task_id='community_detection')
            self.erase_previous_analysis_result(task_id='path_analysis')
            self.last_path_result = result

            if method in ('shortest_path', 'path', 'all_paths'):
                path = result.get('path') or []
                if not path and result.get('paths'):
                    all_p = result.get('paths', [])
                    path_nodes = set()
                    path_edges = set()
                    for p in all_p:
                        for idx_p in range(len(p)):
                            path_nodes.add(str(p[idx_p]))
                            if idx_p < len(p) - 1:
                                path_edges.add((str(p[idx_p]), str(p[idx_p+1])))
                                path_edges.add((str(p[idx_p+1]), str(p[idx_p])))
                    src = str(params.get('source', ''))
                    tgt = str(params.get('target', ''))
                    for el in self.elements:
                        if el.get('group') == 'nodes':
                            nid = str(el.get('data', {}).get('id', ''))
                            if nid in (src, tgt):
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-focus-pair')
                            elif nid in path_nodes:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-intermediary')
                            else:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')
                        elif el.get('group') == 'edges':
                            esrc = str(el.get('data', {}).get('source', ''))
                            etgt = str(el.get('data', {}).get('target', ''))
                            if (esrc, etgt) in path_edges or (etgt, esrc) in path_edges:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-focus-edge')
                            else:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')
                elif path:
                    src = str(path[0])
                    tgt = str(path[-1])
                    inter = set(str(n) for n in path[1:-1])
                    path_edges = set()
                    for idx_p in range(len(path) - 1):
                        path_edges.add((str(path[idx_p]), str(path[idx_p+1])))
                        path_edges.add((str(path[idx_p+1]), str(path[idx_p])))

                    for el in self.elements:
                        if el.get('group') == 'nodes':
                            nid = str(el.get('data', {}).get('id', ''))
                            if nid in (src, tgt):
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-focus-pair')
                            elif nid in inter:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-intermediary')
                            else:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')
                        elif el.get('group') == 'edges':
                            esrc = str(el.get('data', {}).get('source', ''))
                            etgt = str(el.get('data', {}).get('target', ''))
                            if (esrc, etgt) in path_edges or (etgt, esrc) in path_edges:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-focus-edge')
                            else:
                                el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')

            elif method in ('n_hop', 'nhop'):
                root = str(result.get('root') or '')
                neighborhood = set(str(n) for n in result.get('neighborhood') or [])
                hop_distances = result.get('hop_distances') or {}
                for el in self.elements:
                    if el.get('group') == 'nodes':
                        nid = str(el.get('data', {}).get('id', ''))
                        if nid == root:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-focus-pair')
                            el.get('data', {})['nhop_distance'] = 0
                        elif nid in neighborhood:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-nhop-node')
                            el.get('data', {})['nhop_distance'] = hop_distances.get(nid, 1)
                        else:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')
                    elif el.get('group') == 'edges':
                        esrc = str(el.get('data', {}).get('source', ''))
                        etgt = str(el.get('data', {}).get('target', ''))
                        if esrc in neighborhood and etgt in neighborhood:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-nhop-edge')
                        else:
                            el['classes'] = self._merge_class(el.get('classes', ''), 'crimenet-dimmed')

        #################################
        # 4. LINK PREDICTION
        #################################
        elif task_id == 'link_prediction':
            self.erase_previous_analysis_result('link_prediction')
            predictions = result['predictions']
            for source in predictions:
                self.remove_predicted_edges([source])
                if len(predictions[source]) > 0:
                    self.predicted_edges[source] = []
                for target in predictions[source]:
                    predicted_edge_data = {'element_type': 'edge',
                                           'id': '{}_{}'.format(source, target),
                                           'source': source,
                                           'target': target,
                                           'type': 'predicted',
                                           'selected': False,
                                           'label': '',
                                           'predicted': True,
                                           'hidden': active_element_default_values['hidden'],
                                           'highlighted': active_element_default_values['highlighted'],
                                           'source_selected': True,
                                           'info': {'type': 'predicted'}}
                    predicted_element = {'group': 'edges', 'data': predicted_edge_data}
                    self.elements.append(predicted_element)
                    self.predicted_edges[source].append(len(self.elements) - 1)
        elif task_id == 'node_embedding':
            pass
        else:
            pass

        return result

    def dump_network(self, filename, output_dir):
        """
        dump the whole network to a specified directory
        will fail if file already exists
        """
        try:
            output_path = Path(output_dir) / filename
            # with open(output_path, "x") as output_file:
            with open(output_path, "w") as output_file:
                ##############################
                # all the nodes
                for node in self.nodes:
                    node_info = {
                        'id': node,
                        'type': 'node',
                        'properties': self.nodes[node]
                    }
                    json.dump(node_info, output_file)
                    output_file.write('\n')
                ##############################
                # all the edges
                for edge in self.edges:  # type weight confidence
                    edge_info = edge.copy()
                    edge_info['type'] = 'edge'
                    json.dump(edge_info, output_file)
                    output_file.write('\n')
                ##############################
                # all the active nodes
                for node in self.active_nodes:
                    node_info = {
                        'id': node,
                        'type': 'active_node',
                        'properties': self.active_nodes[node]
                    }
                    json.dump(node_info, output_file)
                    output_file.write('\n')
                ##############################
                # all the active edges:
                for edge in self.active_edges:
                    edge_info = {
                        'id': edge,
                        'type': 'active_edge',
                        'properties': self.active_edges[edge]
                    }
                    json.dump(edge_info, output_file)
                    output_file.write('\n')
                ##############################
                # all predicted edges
                for node in self.predicted_edges:
                    node_info = {
                        'id': node,
                        'type': 'predicted_edge',
                        'edges': self.predicted_edges[node]
                    }
                    json.dump(node_info, output_file)
                    output_file.write('\n')
                ##############################
                # all the elements
                for element in self.elements:
                    elment_info = {
                        'type': 'active_element',
                        'properties': element
                    }
                    json.dump(elment_info, output_file)
                    output_file.write('\n')
                ##############################
                # last analysis
                analysis_info = {
                    'type': 'last_analysis',
                    'properties': self.last_analysis
                }
                json.dump(analysis_info, output_file)
                output_file.write('\n')
                ##############################
            return 1
        except Exception as e:
            return e

    def serialize_network(self):
        """
        serialize the whole network into a byte array
        """

        # try:
        mem = io.BytesIO()
        ##############################
        # all the nodes
        for node in self.nodes:
            if node:
                node_info = {
                    'id': node,
                    'type': 'node',
                    'properties': self.nodes[node]
                }
                node_str = '{}\n'.format(json.dumps(node_info))
                mem.write(node_str.encode('utf-8'))
        ##############################
        # all the edges
        for edge in self.edges:
            if edge:
            # type weight confidence
                edge_info = edge.copy()
                edge_info['type'] = 'edge'
                edge_str = '{}\n'.format(json.dumps(edge_info))
                mem.write(edge_str.encode('utf-8'))
        ##############################
        # all the active nodes
        for node in self.active_nodes:
            if node:
                node_info = {
                    'id': node,
                    'type': 'active_node',
                    'properties': self.active_nodes[node]
                }
                node_str = '{}\n'.format(json.dumps(node_info))
                mem.write(node_str.encode('utf-8'))
        ##############################
        # all the active edges:
        for edge in self.active_edges:
            if edge:
                edge_info = {
                    'id': edge,
                    'type': 'active_edge',
                    'properties': self.active_edges[edge]
                }
                edge_str = '{}\n'.format(json.dumps(edge_info))
                mem.write(edge_str.encode('utf-8'))
        ##############################
        # all predicted edges
        for node in self.predicted_edges:
            if node:
                node_info = {
                    'id': node,
                    'type': 'predicted_edge',
                    'edges': self.predicted_edges[node]
                }
                node_str = '{}\n'.format(json.dumps(node_info))
                mem.write(node_str.encode('utf-8'))
        ##############################
        # all the elements
        for element in self.elements:
            if element:
                elment_info = {
                    'type': 'active_element',
                    'properties': element
                }
                element_str = '{}\n'.format(json.dumps(elment_info))
                mem.write(element_str.encode('utf-8'))
        ##############################
        # last analysis
        analysis_info = {
            'type': 'last_analysis',
            'properties': self.last_analysis
        }
        analysis_str = '{}\n'.format(json.dumps(analysis_info))
        mem.write(analysis_str.encode('utf-8'))
        ##############################
        mem.seek(0)
        return {'success': 1, 'mem_object': mem}
        # except Exception as e:
        #    return {'success': 0, 'exception': e}

    def serialize_network_new_format(self):
        """
        serialize the whole network into a byte array
        """
        mem = io.BytesIO()

        data = {}

        if self.meta_info:
            data.update(self.meta_info)

        ##############################
        # all the nodes

        data['nodes'] = []

        for node in self.nodes:
            if node:
                data['nodes'].append(self.nodes[node])

        data['links'] = []

        ##############################
        # all the edges
        for edge in self.edges:
            if edge:
                d = edge['properties']
                d['source'] = edge['source']
                d['target'] = edge['target']
                data['links'].append(d)

        string_data = json.dumps(data, indent=4)
        mem.write(string_data.encode('utf-8'))
        ##############################
        mem.seek(0)
        return {'success': 1, 'mem_object': mem}
        # except Exception as e:
        #    return {'success': 0, 'exception': e}

    def load_from_file(self, path_2_data):
        try:
            # reset the current containers
            self.nodes = {}
            self.edges = []
            self.adj_list = {}
            self.node_types = set()
            self.edge_types = set()

            self.active_nodes = {}
            self.active_edges = {}

            self.elements = []
            #
            self.network_name = None
            self.node_label_field = None
            self.edge_label_field = None
            #
            self.predicted_edges = {}
            self.last_analysis = None
            self.selected_nodes = set()
            self.selected_edges = set()
            self.recent_interactions = []

            # load from file

            file = open(path_2_data, 'r')
            for line in file:
                if line.startswith('#'):  # ignore the comments
                    continue
                line_object = json.loads(line.strip())
                #####################################
                # nodes
                if line_object['type'] == 'node':
                    node = line_object['properties']
                    self.nodes[line_object['id']] = node
                    if 'type' in node:
                        self.node_types.add(node['type'])
                #####################################
                # edges
                elif line_object['type'] == 'edge':
                    edge = {'source': line_object['source'], 'target': line_object['target'],
                            'observed': True, 'properties': line_object['properties']}
                    self.edges.append(edge)
                    e_index = len(self.edges) - 1
                    source = edge['source']
                    if source in self.adj_list:
                        self.adj_list[source].append(e_index)
                    else:
                        self.adj_list[source] = [e_index]
                    if 'type' in line_object['properties']:
                        self.edge_types.add(line_object['properties']['type'])
                #####################################
                # active nodes
                elif line_object['type'] == 'active_node':
                    node = line_object['properties']
                    self.active_nodes[line_object['id']] = node

                #####################################
                # active edges
                elif line_object['type'] == 'active_edge':
                    edge = line_object['properties']
                    self.active_edges[line_object['id']] = edge
                    pass
                #####################################
                # predicted edges
                elif line_object['type'] == 'predicted_edge':
                    node = line_object['id']
                    edges = line_object['edges']
                    self.predicted_edges[node] = edges
                #####################################
                # active elements
                elif line_object['type'] == 'active_element':
                    element = line_object['properties']
                    self.elements.append(element)
                #####################################
                # last analysis
                elif line_object['type'] == 'last_analysis':
                    self.last_analysis = line_object['properties']
                #####################################
                else:
                    continue
            self.edge_types = list(self.edge_types)
            self.node_types = list(self.node_types)
        except Exception as e:
            return e

    @staticmethod
    def infer_entity_type(val, col_name=None):
        s = str(val).strip()
        if not s:
            return 'entity'
        col = (col_name or '').lower()
        if any(k in col for k in ['phone', 'mobile', 'call', 'msisdn', 'caller', 'callee']):
            return 'phone'
        if any(k in col for k in ['veh', 'car', 'plate', 'reg']):
            return 'vehicle'
        if any(k in col for k in ['fir', 'case', 'crime']):
            return 'case'
        if any(k in col for k in ['loc', 'place', 'city', 'address', 'area']):
            return 'location'
        if any(k in col for k in ['org', 'comp', 'bank', 'firm', 'agency']):
            return 'organization'

        # Value pattern heuristics
        if re.match(r'^\+?[6-9]\d{9}$', s):
            return 'phone'
        if re.match(r'^[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4}$', s, re.IGNORECASE) or s.lower().startswith('veh_'):
            return 'vehicle'
        if re.match(r'^(FIR|CASE|CRIME)[-_/]\d+', s, re.IGNORECASE):
            return 'case'

        org_words = ['traders', 'logistics', 'exports', 'infotech', 'motors', 'pvt', 'ltd', 'limited', 'enterprises', 'bank', 'corp', 'solutions']
        lower_s = s.lower()
        if any(w in lower_s for w in org_words):
            return 'organization'

        loc_words = ['bagh', 'place', 'noida', 'estate', 'thane', 'delhi', 'mumbai', 'chowk', 'vashi', 'bhiwandi', 'sector', 'nagar', 'road', 'marg']
        if any(w in lower_s for w in loc_words):
            return 'location'

        return 'person'

    @staticmethod
    def parse_csv_to_data_list(csv_text):
        lines = [l for l in csv_text.strip().splitlines() if l.strip() and not l.strip().startswith('#')]
        if not lines:
            return []

        delimiter = ','
        try:
            dialect = csv.Sniffer().sniff("\n".join(lines[:10]), delimiters=',;\t|')
            delimiter = dialect.delimiter
        except Exception:
            if '\t' in lines[0]:
                delimiter = '\t'
            elif ';' in lines[0]:
                delimiter = ';'
            elif '|' in lines[0]:
                delimiter = '|'

        reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
        all_rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not all_rows:
            return []

        first_row = [c.strip() for c in all_rows[0]]
        first_row_lower = [c.lower() for c in first_row]

        src_aliases = {'source', 'src', 'from', 'caller', 'sender', 'entity1', 'entity_a', 'node1', 'person1', 'suspect', 'origin', 'a'}
        tgt_aliases = {'target', 'tgt', 'to', 'callee', 'receiver', 'entity2', 'entity_b', 'node2', 'person2', 'associate', 'destination', 'b'}

        src_idx = -1
        tgt_idx = -1
        weight_idx = -1
        type_idx = -1
        time_idx = -1

        for i, col in enumerate(first_row_lower):
            if src_idx == -1 and (col in src_aliases or any(a in col for a in ['caller', 'sender', 'source', 'from'])):
                src_idx = i
            elif tgt_idx == -1 and (col in tgt_aliases or any(a in col for a in ['callee', 'receiver', 'target', 'to'])):
                tgt_idx = i
            elif weight_idx == -1 and col in {'weight', 'calls', 'duration', 'amount', 'count', 'frequency', 'freq', 'score'}:
                weight_idx = i
            elif type_idx == -1 and col in {'type', 'relation', 'relationship', 'edge_type', 'link_type', 'action', 'interaction'}:
                type_idx = i
            elif time_idx == -1 and col in {'timestamp', 'time', 'date', 'datetime', 'call_time', 'txn_date'}:
                time_idx = i

        has_header = (src_idx != -1 and tgt_idx != -1) or any(
            col in {'name', 'id', 'type', 'source', 'target', 'from', 'to', 'phone', 'vehicle', 'case', 'amount', 'duration'}
            for col in first_row_lower
        )

        data_rows = all_rows[1:] if has_header else all_rows
        header = first_row if has_header else [f"col_{i}" for i in range(len(all_rows[0]))]

        data_list = []
        nodes_seen = set()

        def add_node(nid, col_name=None, ntype=None):
            sid = str(nid).strip()
            if not sid or sid in nodes_seen:
                return
            nodes_seen.add(sid)
            t = ntype or ActiveNetwork.infer_entity_type(sid, col_name)
            props = {
                'id': sid,
                'name': sid.replace('_', ' '),
                'type': t
            }
            data_list.append({'type': 'node', 'id': sid, 'properties': props})

        def add_edge(src, tgt, edge_type=None, weight=1.0, edge_props=None):
            s_src = str(src).strip()
            s_tgt = str(tgt).strip()
            if not s_src or not s_tgt or s_src == s_tgt:
                return
            et = edge_type or 'connected_to'
            props = {'type': et, 'weight': weight}
            if edge_props:
                for k, v in edge_props.items():
                    if k not in props and v:
                        props[k] = v
            data_list.append({'type': 'edge', 'source': s_src, 'target': s_tgt, 'properties': props})

        # Case 1: Standard edge-list (src and tgt columns identified)
        if src_idx != -1 and tgt_idx != -1:
            for row in data_rows:
                if len(row) <= max(src_idx, tgt_idx):
                    continue
                src = row[src_idx].strip()
                tgt = row[tgt_idx].strip()
                if not src or not tgt:
                    continue

                w = 1.0
                if weight_idx != -1 and len(row) > weight_idx:
                    try:
                        w = float(re.sub(r'[^\d.]', '', row[weight_idx]))
                    except Exception:
                        w = 1.0

                et = None
                if type_idx != -1 and len(row) > type_idx and row[type_idx].strip():
                    et = row[type_idx].strip()

                props = {}
                for i, val in enumerate(row):
                    if i not in {src_idx, tgt_idx, weight_idx, type_idx} and i < len(header):
                        props[header[i]] = val.strip()
                if time_idx != -1 and len(row) > time_idx:
                    props['timestamp'] = row[time_idx].strip()

                add_node(src, col_name=header[src_idx])
                add_node(tgt, col_name=header[tgt_idx])
                add_edge(src, tgt, edge_type=et, weight=w, edge_props=props)

        # Case 2: Multi-entity record table (e.g. suspect, phone, vehicle, fir, location)
        elif len(header) >= 2 and any(k in first_row_lower for k in ['suspect', 'person', 'name', 'phone', 'vehicle', 'fir', 'case']):
            primary_idx = 0
            for i, col in enumerate(first_row_lower):
                if col in {'suspect', 'person', 'name', 'accused', 'caller'}:
                    primary_idx = i
                    break

            for row in data_rows:
                if len(row) <= primary_idx:
                    continue
                primary_val = row[primary_idx].strip()
                if not primary_val:
                    continue
                add_node(primary_val, col_name=header[primary_idx])

                for j, cell in enumerate(row):
                    if j == primary_idx or j >= len(header):
                        continue
                    val = cell.strip()
                    if not val:
                        continue
                    col_name = header[j].lower()
                    rel = 'associated_with'
                    if 'phone' in col_name:
                        rel = 'uses_phone'
                    elif 'veh' in col_name:
                        rel = 'uses_vehicle'
                    elif 'fir' in col_name or 'case' in col_name:
                        rel = 'named_in'
                    elif 'loc' in col_name:
                        rel = 'seen_at'
                    elif 'org' in col_name:
                        rel = 'affiliated_with'

                    add_node(val, col_name=header[j])
                    add_edge(primary_val, val, edge_type=rel, weight=1.0)

        # Case 3: Fallback 2+ columns -> col 0 is source, col 1 is target
        else:
            for row in data_rows:
                if len(row) < 2:
                    continue
                src = row[0].strip()
                tgt = row[1].strip()
                if not src or not tgt:
                    continue
                w = 1.0
                if len(row) >= 3:
                    try:
                        w = float(re.sub(r'[^\d.]', '', row[2]))
                    except Exception:
                        pass
                et = row[3].strip() if len(row) >= 4 and row[3].strip() else 'linked_to'
                add_node(src)
                add_node(tgt)
                add_edge(src, tgt, edge_type=et, weight=w)

        return data_list

    def deserialize_network(self, uploaded_file, initialize=True):
        """
        Deserialize network data from JSON or CSV format.
        :param uploaded_file: base64 encoded data URI string
        :param initialize: whether to initialize elements
        """
        # reset the current containers
        self.nodes = {}
        self.edges = []
        self.adj_list = {}
        self.in_adj_list = {}
        self.node_types = {}
        self.edge_types = {}

        self.active_nodes = {}
        self.active_edges = {}

        self.elements = []
        self.network_name = None
        self.node_label_field = None
        self.edge_label_field = None

        self.predicted_edges = {}
        self.last_analysis = None
        self.selected_nodes = set()
        self.selected_edges = set()
        self.recent_interactions = []
        self.meta_info = {}

        # load from file
        print('\t\t DESERIALIZING')

        content_type, content_string = uploaded_file.split(',')
        decoded = base64.b64decode(content_string).decode('utf-8', errors='replace')
        decoded_clean = decoded.strip()

        # Check if JSON or CSV
        data_list = []
        is_json = False

        if decoded_clean.startswith("{\n") or decoded_clean.startswith("{\r\n"):
            try:
                in_data = json.loads(decoded)
                data_list = converter.new_to_old(in_data)
                try:
                    self.meta_info['directed'] = in_data.get('directed', False)
                    self.meta_info['multigraph'] = in_data.get('multigraph', False)
                    self.meta_info['graph'] = in_data.get('graph', {})
                except KeyError:
                    pass
                is_json = True
            except Exception:
                is_json = False

        if not is_json:
            first_non_comment = next((l.strip() for l in decoded_clean.splitlines() if l.strip() and not l.strip().startswith('#')), '')
            if first_non_comment.startswith('{') and ('"type"' in first_non_comment or "'type'" in first_non_comment):
                try:
                    data_list = [json.loads(line.strip()) for line in decoded.splitlines() if len(line.strip()) != 0 and not line.strip().startswith('#')]
                    is_json = True
                except Exception:
                    is_json = False

        if not is_json:
            # Parse as CSV!
            data_list = self.parse_csv_to_data_list(decoded)

        # print('decoded = ', decoded)
        for line_object in data_list:
            #####################################
            # nodes
            if line_object['type'] == 'node':
                node = line_object['properties']
                self.nodes[line_object['id']] = node
                if 'type' in node:
                    node_type = node['type']
                    if node_type in self.node_types:
                        self.node_types[node_type] += 1
                    else:
                        self.node_types[node_type] = 1
            #####################################
            # edges
            elif line_object['type'] == 'edge':
                edge = {'source': line_object['source'], 'target': line_object['target'],
                        'observed': True, 'properties': line_object['properties']}
                self.edges.append(edge)
                e_index = len(self.edges) - 1
                source, target = edge['source'], edge['target']
                if source in self.adj_list:
                    self.adj_list[source].append(e_index)
                else:
                    self.adj_list[source] = [e_index]

                if target in self.in_adj_list:
                    self.in_adj_list[target].append(e_index)
                else:
                    self.in_adj_list[target] = [e_index]

                if 'type' in line_object['properties']:
                    edge_type = line_object['properties']['type']
                    if edge_type in self.edge_types:
                        self.edge_types[edge_type] += 1
                    else:
                        self.edge_types[edge_type] = 1
            #####################################
            # active nodes
            elif line_object['type'] == 'active_node':
                node = line_object['properties']
                self.active_nodes[line_object['id']] = node

            #####################################
            # active edges
            elif line_object['type'] == 'active_edge':
                edge = line_object['properties']
                self.active_edges[line_object['id']] = edge
                pass
            #####################################
            # predicted edges
            elif line_object['type'] == 'predicted_edge':
                node = line_object['id']
                edges = line_object['edges']
                self.predicted_edges[node] = edges
            #####################################
            # active elements
            elif line_object['type'] == 'active_element':
                element = line_object['properties']
                self.elements.append(element)
                # selected nodes
                if element['data']['element_type'] == 'node':
                    if element['data']['selected']:
                        self.selected_nodes.add(element['data']['id'])
                else:
                    if element['data']['selected']:
                        self.selected_edges.add(element['data']['id'])
            #####################################
            # last analysis
            elif line_object['type'] == 'last_analysis':
                self.last_analysis = line_object['properties']
            #####################################
            else:
                continue
        # self.edge_types = list(self.edge_types)
        # self.node_types = list(self.node_types)
        # except Exception as e:
        #    return e

        # initialize the active if it is blank
        if initialize:
            if len(self.elements) == 0:
                self.initialize()

    def print_elements(self):
        for e in self.elements:
            print(e)

    def forget_interactions(self):
        if len(self.recent_interactions) > max_num_recent_interactions:
            self.recent_interactions = self.recent_interactions[-max_num_recent_interactions:]

    def update_an_active_node(self, node, properties):
        """
        update properties of an active node
        :param node:id of the node to be updated
        :param properties: dictionary
        :return:
        """
        print('********************************************')
        print('update_an_active_node: node = ', node)
        print('update_an_active_node: properties = ', properties)
        if node not in self.active_nodes:
            return {'success': 0, 'message': 'node is not active!'}
        else:
            pre_properties = copy.deepcopy(self.nodes[node])
            # update in the underlying network
            result = self.update_a_node(node, properties=properties)
            # print(result)
            if result['success'] == 1:
                # update the corresponding active element
                element_index = self.active_nodes[node]['element_index']
                # update the type
                if 'type' in properties:
                    self.elements[element_index]['data']['type'] = properties['type']
                # add name field as 'label' to resemble changes in visualizer.
                if 'name' in properties:
                    self.elements[element_index]['data']['label'] = properties['name']
                if self.node_label_field is not None:
                    if self.node_label_field in properties:
                        self.elements[element_index]['data']['label'] = properties[self.node_label_field]

                # remember the interaction
                interaction = {'action': node_update_action, 'node': node, 'pre_properties': pre_properties}
                self.recent_interactions.append(interaction)
                self.forget_interactions()
                return {'success': 1, 'message': 'node updated successfully!'}
            else:
                return result

    def add_an_active_node(self, node, properties):
        """
        add a node into active network
        :param node: id of the node
        :param properties: dictionary
        :return:
        """
        # try to add the node into the underlying network
        result = self.add_a_node(node, properties=properties)
        if result['success'] == 1:
            if 'name' not in properties:
                properties['name'] = ''
            # activate the node
            node_data = {'element_type': 'node',
                         'id': node,
                         'type': properties['type'],
                         'label': properties['name'],
                         'selected': active_element_default_values['selected'],
                         'expandable': active_element_default_values['expandable'],
                         'community': active_element_default_values['community'],
                         'community_confidence': active_element_default_values['community_confidence'],
                         'social_influence_score': active_element_default_values['social_influence_score'],
                         'visualisation_social_influence_score':
                             active_element_default_values['visualisation_social_influence_score'],
                         'hidden': active_element_default_values['hidden'],
                         'highlighted': active_element_default_values['highlighted'],
                         'num_incoming_neighbor_selected': active_element_default_values[
                             'num_incoming_neighbor_selected'],
                         'incoming_neighbor_selected': active_element_default_values['incoming_neighbor_selected'],
                         'info': properties}
            # add label
            if self.node_label_field is not None:
                if self.node_label_field in properties:
                    node_data['label'] = properties[self.node_label_field]
                else:
                    node_data['label'] = node
            else:
                node_data['label'] = node_data['id']
            # check expandability
            node_data['expandable'] = False
            element = {'group': 'nodes', 'data': node_data}
            self.elements.append(element)
            self.active_nodes[node] = {'expandable': False, 'element_index': len(self.elements) - 1}

            interaction = {'action': node_add_action, 'node': node, 'properties': copy.deepcopy(properties)}
            self.recent_interactions.append(interaction)
            self.forget_interactions()
            return {'success': 1, 'message': 'node  added successfully!'}
        else:
            return result

    def update_an_active_edge(self, edge_id, properties):
        """
        update properties of an active edge
        :param edge_id: integer, id of the edge
        :param properties: dictionary
        :return:
        """
        if edge_id not in self.active_edges:
            return {'success': 0, 'message': 'edge is not active!'}
        else:
            edge = self.edges[edge_id]
            pre_properties = copy.deepcopy(self.edges[edge_id]['properties'])
            source, target = edge['source'], edge['target']
            result = self.update_an_edge(edge_id, properties=properties, is_index=True)
            if result['success'] == 1:
                # update the type
                if 'type' in properties:
                    element_index = self.active_edges[edge_id]['element_index']
                    self.elements[element_index]['data']['type'] = properties['type']
                # update the probability
                if 'probability' in properties:
                    element_index = self.active_edges[edge_id]['element_index']
                    self.elements[element_index]['data']['probability'] = properties['probability']
                # remember the interaction
                interaction = {'action': edge_update_action,
                               'edge': {'e_index': edge_id, 'source': source, 'target': target},
                               'pre_properties': pre_properties}
                self.recent_interactions.append(interaction)
                self.forget_interactions()
                return {'success': 1, 'message': 'node updated successfully!'}
            else:
                return result

    def add_an_active_edge(self, source, target, properties):
        """
        add an edge into the active network
        :param source: id of the source node
        :param target: id of the target node
        :param properties: dictionary
        :return:
        """
        if source not in self.active_nodes:
            return {'success': 0, 'message': 'source not active!'}
        if target not in self.active_nodes:
            return {'success': 0, 'message': 'target not active!'}
        # trying to add the edge into the underlying network
        result = self.add_an_edge(source, target, properties=properties)
        if result['success'] == 1:
            # active the edge
            e_index = len(self.edges) - 1
            edge_info = self.edges[e_index]
            edge_data = {'element_type': 'edge',
                         'id': e_index,
                         'source': edge_info['source'],
                         'target': edge_info['target'],
                         'type': active_element_default_values['type'],
                         'label': active_element_default_values['label'],
                         'selected': active_element_default_values['selected'],
                         'predicted': active_element_default_values['predicted'],
                         'hidden': active_element_default_values['hidden'],
                         'highlighted': active_element_default_values['highlighted'],
                         'source_selected': active_element_default_values['source_selected'],
                         'info': edge_info['properties']}
            # add type
            if 'type' in edge_info['properties']:
                edge_data['type'] = edge_info['properties']['type']
            # add edge label
            if self.edge_label_field is not None:
                if self.edge_label_field in edge_info:
                    edge_data['label'] = edge_info[self.edge_label_field]
            else:
                edge_data['label'] = ''  # blank label

            element = {'group': 'edges', 'data': edge_data}
            self.elements.append(element)
            self.active_edges[e_index] = {'element_index': len(self.elements) - 1}

            interaction = {'action': edge_add_action,
                           'edge': {'e_index': e_index, 'source': source, 'target': target},
                           'properties': properties}
            self.recent_interactions.append(interaction)
            self.forget_interactions()

    def delete_an_active_edge(self, edge_id):
        """
        delete an edge from the active network
        :param edge_id: integer, id of the edge
        :return:
        """
        if edge_id not in self.active_edges:
            return {'success': 0, 'message': 'edge is not active!'}
        else:
            # deactivate the edge
            element_index = self.active_edges[edge_id]['element_index']
            self.selected_edges.remove(edge_id)
            self.remove_element([element_index])
            # deleted the edge from the underlying network
            edge = self.edges[edge_id]
            source, target = edge['source'], edge['target']
            properties = copy.deepcopy(edge['properties'])

            self.delete_an_edge(edge_id, is_index=True)

            interaction = {'action': edge_delete_action,
                           'edge': {'e_index': edge_id, 'source': source, 'target': target},
                           'properties': properties}
            self.recent_interactions.append(interaction)
            self.forget_interactions()

    def delete_an_active_node(self, node):
        """
        delete a node from the active network
        :param node:
        :return:
        """
        if node not in self.active_nodes:
            return {'success': 0, 'message': 'node is not active!'}
        else:
            # deactivate the node
            self.deactivate_nodes([node])
            # delete the node from the underlying network
            properties = copy.deepcopy(self.nodes[node])

            self.delete_a_node(node)

            interaction = {'action': node_delete_action, 'node': node, 'properties': properties}
            self.recent_interactions.append(interaction)
            self.forget_interactions()

    def merge_active_nodes(self, nodes, new_node, new_properties):
        """
        merge a list of active nodes
        :param nodes: list of node ids
        :param new_node: id of the new node
        :param new_properties: dictionary, properties of the new node
        :return:
        """
        print('nodes = ', nodes)
        print('new_node = ', new_node)
        print('new_properties = ', new_properties)
        # get affected edges
        affected_edges = []
        nodes = set(nodes)
        for node in nodes:
            if node not in self.active_nodes:
                continue
            if node in self.adj_list:
                for e in self.adj_list[node]:
                    if e in self.active_edges:
                        affected_edges.append(e)
            if node in self.in_adj_list:
                for e in self.in_adj_list[node]:
                    if e in self.active_edges:
                        affected_edges.append(e)
        # replace affected edges by new edges
        new_edges = []
        affected_edges = set(affected_edges)
        for e in affected_edges:
            # deactivate the edges:

            # Disabled edge deactivation because of a bug where edges where removed, even thought, they had
            # nothing to do with the merged nodes. Everything seems to work now as intended ...
            # if e in self.active_edges:
                # self.remove_element([self.active_edges[e]['element_index']])
                # self.deactivate_edges([self.active_edges[e]['element_index']])
            # create a new edge
            source, target = self.edges[e]['source'], self.edges[e]['target']
            properties = copy.deepcopy(self.edges[e]['properties'])
            if source in nodes:
                source = new_node
            if target in nodes:
                target = new_node
            new_edges.append((source, target, properties))
        # delete the nodes
        for node in nodes:
            self.delete_an_active_node(node)
        # add the new node
        self.add_an_active_node(new_node, new_properties)
        # add the new edges
        for edge in new_edges:
            source, target, properties = edge[0], edge[1], edge[2]
            self.add_an_active_edge(source, target, properties)
        # set the node to selected
        self.toggle_node_selection(new_node)

    def isolate_nodes(self, selected_node_ids):
        """
        Isolates selected nodes and all directly linked nodes (connected neighbors)
        to provide a clear, clutter-free view of the selected entities and whom they are linked to.
        """
        selected = set(selected_node_ids)
        linked_nodes = set(selected)

        # Collect all active nodes connected to any selected node (incoming or outgoing)
        for e_idx, e_info in self.active_edges.items():
            if e_idx < len(self.edges):
                edge = self.edges[e_idx]
                src = edge.get('source')
                tgt = edge.get('target')
                if src in selected and tgt in self.active_nodes:
                    linked_nodes.add(tgt)
                if tgt in selected and src in self.active_nodes:
                    linked_nodes.add(src)

        # Also include any nodes already highlighted as incoming_neighbor_selected
        for el in self.elements:
            if el.get('group') == 'nodes':
                d = el.get('data', {})
                if d.get('incoming_neighbor_selected') and d.get('id') in self.active_nodes:
                    linked_nodes.add(d.get('id'))

        new_elements = []
        new_active_nodes = {}
        new_active_edges = {}

        self.erase_previous_analysis_result(task_id='social_influence_analysis')
        self.erase_previous_analysis_result(task_id='community_detection')
        self.erase_previous_analysis_result(task_id='link_prediction')
        self.last_analysis = None

        # Add node elements (preserving selected and linked red outline indicators)
        for el in self.elements:
            data = el.get('data', {})
            group = el.get('group')
            if group == 'nodes':
                node_id = data.get('id')
                if node_id in linked_nodes:
                    if node_id in selected:
                        data['selected'] = True
                        data['incoming_neighbor_selected'] = False
                    else:
                        data['selected'] = False
                        data['incoming_neighbor_selected'] = True

                    el_idx = len(new_elements)
                    new_elements.append(el)
                    if node_id in self.active_nodes:
                        node_info = dict(self.active_nodes[node_id])
                        node_info['element_index'] = el_idx
                        node_info['expandable'] = True
                        new_active_nodes[node_id] = node_info

        # Add edge elements connecting the kept nodes
        for el in self.elements:
            data = el.get('data', {})
            group = el.get('group')
            if group == 'edges':
                src = data.get('source')
                tgt = data.get('target')
                if src in linked_nodes and tgt in linked_nodes:
                    if src in selected:
                        data['source_selected'] = True
                    el_idx = len(new_elements)
                    new_elements.append(el)
                    edge_id = data.get('id')
                    for e_idx, e_info in self.active_edges.items():
                        if e_info.get('element_index') == el.get('element_index') or e_idx == edge_id:
                            new_e = dict(e_info)
                            new_e['element_index'] = el_idx
                            new_active_edges[e_idx] = new_e
                            break

        self.elements = new_elements
        self.active_nodes = new_active_nodes
        self.active_edges = new_active_edges
        self.selected_nodes = set(selected)
        return len(new_active_nodes), len(new_elements) - len(new_active_nodes)

    def restore_full_network(self):
        """
        Restores full network view while preserving the current node selection.
        """
        selected = list(self.get_selected_nodes())
        self.initialize()
        for node in selected:
            if node in self.active_nodes:
                self.toggle_node_selection(node)
        return len(self.active_nodes), len(self.elements) - len(self.active_nodes)


class BuiltinDatasetsManager(DataManager):
    """
    class for managing builtin datasets
    """

    def __init__(self, connector, params, load_on_construcion=False):
        super(BuiltinDatasetsManager, self).__init__(connector, params)
        self.datasets = {}
        if load_on_construcion:
            self.add_dataset('bbc_islam_groups', 'BBC Islam Groups',
                             '%s/datasets/preprocessed/bbc_islam_groups.json' % path2root)
            self.add_dataset('911_hijackers', '911 Hijackers',
                             '%s/datasets/preprocessed/911_hijackers.json' % path2root)
            # data_manager.add_dataset('enron', 'Enron Email Network',
            #                         '%s/datasets/preprocessed/enron.json' % path2root)
            # data_manager.add_dataset('moreno_crime', 'Moreno Crime Network',
            #                         '%s/datasets/preprocessed/moreno_crime.json' % path2root)
            #
            # data_manager.add_dataset('imdb', 'IMDB',
            #                         '%s/datasets/preprocessed/imdb.json' % path2root)

            self.add_dataset('baseball_steroid_use', 'Baseball Steorid Use',
                             '%s/datasets/preprocessed/baseball_steroid_use.json' % path2root)

            self.add_dataset('madoff', 'Madoff fraud',
                             '%s/datasets/preprocessed/madoff.json' % path2root)

            self.add_dataset('montreal_gangs', 'Montreal Street Gangs',
                             '%s/datasets/preprocessed/montreal_gangs.json' % path2root)

            self.add_dataset('noordintop', 'Noordin Top',
                             '%s/datasets/preprocessed/noordintop.json' % path2root)

            self.add_dataset('rhodes_bombing', 'Rhodes Bombing',
                             '%s/datasets/preprocessed/rhodes_bombing.json' % path2root)

            self.add_dataset('synthetic_black_falcon', '[TEST / SYNTHETIC DATA] Operation Black Falcon',
                             '%s/datasets/preprocessed/synthetic_investigation_test_data.json' % path2root)

    def add_dataset(self, datset_id, name, path_2_data, settings=None, uploaded=False, from_file=True):
        """
        To add a dataset from file
        :param datset_id:
        :param name:
        :param settings: dict of dataset settings
        :param path_2_data: file containing the dataset, each line is a JSON object about either a node or an edge
            node object is in the following format:
            {
                "type": "node"
                "id": id of the node
                "properties": json object containing information about the node
            }

            edge object is in the following format:
            {
                "type": "edge"
                "source" id of source node,
                "target": id of target node,
                "properties": dictionaries containing properties of the edge, in the following format
                        {
                            "type": type of the edge, e.g., "work for", or "friend of",
                            "weight": optional, weight of the edge,
                            "confidence": optional, confidence/certainty of the edge,
                            ...
                        }
            }
        :return: a dictionary, in the following format
            {
                'success': 1 if the dataset is added successfully, 0 otherwise
                'message': a string
            }

        """
        if not settings:
            settings = {}
        try:
            if datset_id in self.datasets:
                return {'success': 0, 'message': 'dataset_id is already existed'}
            dataset = BuiltinDataset(path_2_data, uploaded, from_file)
            self.datasets[datset_id] = {
                'name': name,
                'data': dataset,
                'description': settings["description"] if "description" in settings else "",
                'version': settings["version"] if "version" in settings else 1.0,
                'directed': settings["directed"] if "directed" in settings else True,
                'multigraph': settings["multigraph"] if "multigraph" in settings else False
            }
            return {'success': 1, 'message': 'dataset is created successfully'}
        except Exception as e:
            print(e)
            return {'success': 0, 'message': 'there should be some error in IO'}

    def create_network(self, network_id, name, nodes, edges, settings=None):
        """
        create a network from node and edge lists
        :param name: string
        :param network_id: string
        :param nodes: list of nodes, each is is a dictionary
                {
                'id': string, id of the node
                'properties': dictionary, properties of the node
                }
        :param edges: list of edges, each is is a dictionary
                {
                'source': string, id of the source node
                'target': string, id of the target node
                'properties': dictionary, properties of the edges
                }
        :return: a dictionary, in the following format
            {
                'success': 1 if the dataset is added successfully, 0 otherwise
                'message': a string
            }
        """
        if not settings:
            settings = {}
        if network_id in self.datasets:
            return {'success': 0, 'message': 'dataset_id is already existed'}
        g = BuiltinDataset(None, from_file=False)
        for node in nodes:
            g.nodes[node['id']] = node['properties']
            if 'type' in node['properties']:
                g.node_types.add(node['properties']['type'])

        for edge in edges:
            if edge['source'] in g.nodes and edge['target'] in g.nodes:
                g.edges.append(edge)
                e_index = len(g.edges) - 1
                source = edge['source']
                if source in g.adj_list:
                    g.adj_list[source].append(e_index)
                else:
                    g.adj_list[source] = [e_index]
                if 'type' in edge['properties']:
                    g.edge_types.add(edge['properties']['type'])
        self.datasets[network_id] = {
            'name': name,
            'data': g,
            'description': settings["description"] if "description" in settings else "",
            'version': settings["version"] if "version" in settings else 1.0,
            'directed': settings["directed"] if "directed" in settings else True,
            'multigraph': settings["multigraph"] if "multigraph" in settings else False
        }
        return {'success': 1, 'message': 'dataset is created successfully'}

    def search_networks(self, networks=None, params=None):
        """

        :param networks:
        :param params:
        :return:
        """
        if networks is None:
            networks = list(self.datasets.keys())
        found = []
        not_found = []
        for g in networks:
            if g in self.datasets:
                n = self.datasets[g]
                properties = {'name': n['name'],
                              'edge_types': n['data'].edge_types,
                              'node_types': n['data'].node_types,
                              'num_nodes': len(n['data'].nodes),
                              'num_edges': len(n['data'].edges)
                              }
                found.append({'id': g, 'properties': properties})
            else:
                not_found.append(g)
        return {'found': found, 'not_found': not_found}

    def get_network(self, network, node_ids=None, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].get_network(node_ids=node_ids, params=params)
        else:
            return {'edges': [], 'nodes': []}

    def get_edges(self, node_ids, network, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].get_edges(node_ids=node_ids, params=params)
        else:
            return {'found': [], 'not_found': node_ids}

    def get_neighbors(self, node_ids, network, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].get_neighbors(node_ids=node_ids, params=params)
        else:
            return {'found': [], 'not_found': node_ids}

    def search_nodes(self, node_ids, network, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].search_nodes(node_ids=node_ids, params=params)
        else:
            return {'found': [], 'not_found': node_ids}

    def save_nodes(self, nodes, network, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].save_nodes(nodes=nodes, params=params)
        else:
            return nodes

    def save_edges(self, edges, network, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].save_edges(edges=edges, params=params)
        else:
            return edges

    def delete_node(self, node_ids, network):
        if network in self.datasets:
            return self.datasets[network]['data'].delete_node(node_ids=node_ids)
        else:
            return node_ids

    def delete_edges(self, edges, network):
        if network in self.datasets:
            return self.datasets[network]['data'].delete_edges(deleted_edges=edges)
        else:
            return edges

    def dump_network(self, network, output_dir, params=None):
        if network in self.datasets:
            return self.datasets[network]['data'].dump_network(network=network, output_dir=output_dir,
                                                               params=params)
        else:
            return 0

    def load_file(self, file_path):
        """
        Load a previously saved network from a file, adds its dataset to the data manager
        and initializes an ActiveNetwork
        :param file_path:
        :return:
        """
        pass

    def load_active_network(self, network_id=None, network_name=None, node_ids=None, initialize=True,
                            from_file=False, file_path=None, params={}):
        """
        Initialize an ActiveNetwork from a given internal dataset and (optionally) a list of entities.
        :param network_id:
        :param network_name:
        :param node_ids:
        :param initialize:
        :param from_file:
        :param file_path:
        :param params:
        :return:
        """
        if not from_file:
            if network_id not in self.datasets:
                return {'success': 0, 'message': 'dataset_id not found'}
            else:
                dataset = self.datasets[network_id]['data']
                # create a blank active network
                active_network = ActiveNetwork(path_2_data=None, from_file=False, uploaded=False, initialize=False)
                active_network.nodes = dataset.nodes
                active_network.edges = dataset.edges
                active_network.adj_list = dataset.adj_list
                active_network.node_types = dataset.node_types
                active_network.edge_types = dataset.edge_types
                if network_name is not None:
                    params['network_name'] = network_name
                if initialize:
                    active_network.initialize(selected_nodes=node_ids, params=params)
                return {'success': 1, 'message': 'active network created successfully',
                        'active_network': active_network}
        else:
            print('reading from file')
            active_network = ActiveNetwork(path_2_data=None, from_file=False, uploaded=False, initialize=False)
            active_network.load_from_file(file_path)
            if initialize:
                active_network.initialize(selected_nodes=node_ids, params=params)
            return {'success': 1, 'message': 'active network created successfully',
                    'active_network': active_network}

    def save_data(self, save_path):
        """
        Save the dataset and the current state of the active_network to a file.
        :param save_path:
        :return:
        """
