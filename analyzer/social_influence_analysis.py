import sys
import os
import networkx as nx

# find path to root directory of the project so as to import from other packages
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

import analyzer.common.helpers as helpers


def pagerank(network, params):
    """
    wrapper for NetworkX's parerank function
    :param network:
    :param params:

    :return: dictionary, in the form
        {
            'success': 1 if success, 0 otherwise
            'message': a string
            'scores': a dictionary of pagerank score of nodes in network
        }
    """
    try:
        graph, node_ids = helpers.convert_to_nx_directed_graph(network)
        pers = None
        if params and 'personalization' in params and isinstance(params['personalization'], dict):
            id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
            pers = {id_to_idx[nid]: weight for nid, weight in params['personalization'].items() if nid in id_to_idx}
            if not pers:
                pers = None

        pr = nx.pagerank(graph, personalization=pers)
        scores = [(node_ids[i], pr[i]) for i in range(len(node_ids))]
        scores = dict(scores)
        result = {'success': 1, 'message': 'the task is performed successfully', 'scores': scores}
        return result
    except Exception as e:
        print(e)
        result = {'success': 0, 'message': 'this algorithm is not suitable for the input network', 'scores': None}
        return result


def authority(network, params):
    """
    wrapper for NetworkX's hits function
    :param network:
    :param params:
    :return: dictionary, in the form
        {
            'success': 1 if success, 0 otherwise
            'message': a string
            'scores': a dictionary of pagerank score of nodes in network
        }
    """
    try:
        graph, node_ids = helpers.convert_to_nx_directed_graph(network)
        # print(graph)
        # print(node_ids)
        _, a = nx.hits(graph)
        scores = [(node_ids[i], a[i]) for i in range(len(node_ids))]
        # print(scores)
        scores = dict(scores)
        result = {'success': 1, 'message': 'the task is performed successfully', 'scores': scores}
        return result
    except Exception as e:
        print(e)
        result = {'success': 0, 'message': 'this algorithm is not suitable for the input network', 'scores': None}
        return result


def betweenness(network, params):
    """
    wrapper for NetworkX's betweeness_centrality function
    :param network:
    :param params:
    :return: dictionary, in the form
        {
            'success': 1 if success, 0 otherwise
            'message': a string
            'scores': a dictionary of pagerank score of nodes in network
        }

    """
    try:
        graph, node_ids = helpers.convert_to_nx_undirected_graph(network)  # TODO: to be refactor
        # print(graph)
        # print(node_ids)
        centralities = nx.betweenness_centrality(graph)
        scores = [(node_ids[i], centralities[i]) for i in range(len(node_ids))]
        # print(scores)
        scores = dict(scores)
        result = {'success': 1, 'message': 'the task is performed successfully', 'scores': scores}
        return result
    except Exception as e:
        print(e)
        result = {'success': 0, 'message': 'this algorithm is not suitable for the input network', 'scores': None}
        return result


def katz_centrality(network, params):
    """
    wrapper for NetworkX's katz_centrality function
    :param network:
    :param params:
    :return: dictionary, in the form
        {
            'success': 1 if success, 0 otherwise
            'message': a string
            'scores': a dictionary of pagerank score of nodes in network
        }

    """
    try:
        graph, node_ids = helpers.convert_to_nx_undirected_graph(network)  # TODO: to be refactor
        # print(graph)
        # print(node_ids)
        centralities = nx.katz_centrality(graph)
        scores = [(node_ids[i], centralities[i]) for i in range(len(node_ids))]
        # print(scores)
        scores = dict(scores)
        result = {'success': 1, 'message': 'the task is performed successfully', 'scores': scores}
        return result
    except Exception as e:
        print(e)
        result = {'success': 0, 'message': 'this algorithm is not suitable for the input network', 'scores': None}
        return result


def closeness_centrality(network, params):
    """
    wrapper for NetworkX's closeness_centrality function
    :param network:
    :param params:
    :return: dictionary with closeness centrality scores
    """
    try:
        graph, node_ids = helpers.convert_to_nx_undirected_graph(network)
        centralities = nx.closeness_centrality(graph)
        scores = {node_ids[i]: centralities[i] for i in range(len(node_ids))}
        result = {'success': 1, 'message': 'the task is performed successfully', 'scores': scores}
        return result
    except Exception as e:
        print(e)
        result = {'success': 0, 'message': 'this algorithm is not suitable for the input network', 'scores': None}
        return result


def degree_centrality(network, params):
    """
    wrapper for NetworkX's degree_centrality function
    :param network:
    :param params:
    :return: dictionary with degree centrality scores
    """
    try:
        graph, node_ids = helpers.convert_to_nx_undirected_graph(network)
        centralities = nx.degree_centrality(graph)
        scores = {node_ids[i]: centralities[i] for i in range(len(node_ids))}
        result = {'success': 1, 'message': 'the task is performed successfully', 'scores': scores}
        return result
    except Exception as e:
        print(e)
        result = {'success': 0, 'message': 'this algorithm is not suitable for the input network', 'scores': None}
        return result


def get_info():
    """
    get information about methods provided in this class
    """
    info = {'name': 'Social Influence Analysis',
            'methods': {
                'pagerank': {
                    'name': 'PageRank',
                    'parameter': {}
                },
                'degree_centrality': {
                    'name': 'Degree Centrality',
                    'parameter': {}
                },
                'betweenness': {
                    'name': 'Betweenness Centrality',
                    'parameter': {}
                },
                'closeness_centrality': {
                    'name': 'Closeness Centrality',
                    'parameter': {}
                },
                'authority': {
                    'name': 'Authority',
                    'parameter': {}
                }
            }
            }
    return info


class SocialInfluenceAnalyzer:
    """
    class for performing social influence analysis
    """

    def __init__(self, algorithm):
        """
        init a social influence analyzer using the given `algorithm`
        :param algorithm:
        """
        self.algorithm = algorithm
        self.methods = {
            'pagerank': pagerank,
            'authority': authority,
            'betweenness': betweenness,
            'betweenness_centrality': betweenness,
            'degree_centrality': degree_centrality,
            'degree': degree_centrality,
            'katz_centrality': katz_centrality,
            'katz': katz_centrality,
            'closeness_centrality': closeness_centrality,
            'closeness': closeness_centrality
        }

    def perform(self, network, params):
        """
        performing
        :param network:
        :param params:
        :return:
        """
        return self.methods[self.algorithm](network, params)
