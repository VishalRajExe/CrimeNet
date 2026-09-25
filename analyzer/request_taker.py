import sys
import os

# find path to root directory of the project so as to import from other packages
path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

from framework.interfaces import AnalysisRequester
from analyzer.community_detection import CommunityDetector
from analyzer.social_influence_analysis import SocialInfluenceAnalyzer
from analyzer.link_prediction import LinkPredictor
from analyzer.node_embedding import NodeEmbedder
from analyzer.path_analysis import PathAnalyzer

from analyzer import community_detection
from analyzer import link_prediction
from analyzer import social_influence_analysis
from analyzer import node_embedding
from analyzer import path_analysis


def get_info():
    """
    get information about available methods for each analysis task
    :return: dictionary: keys are tasks' id, values are dictionaries that describe the methods available for the task
    """
    info = {'community_detection': community_detection.get_info(),
            'link_prediction': link_prediction.get_info(),
            'social_influence_analysis': social_influence_analysis.get_info(),
            'path_analysis': path_analysis.get_info(),
            'node_embedding': node_embedding.get_info()
            }
    return info


class InMemoryAnalyzer(AnalysisRequester):
    def __init__(self):
        """
        #TODO: more to be added
        """
        self.community_detector = None
        self.social_influence_analyzer = None
        self.link_predictor = None
        self.node_embedder = None
        self.path_analyzer = None

    def perform_analysis(self, task, params):
        """
        request to perform an analysis task
        :param task: dictionary that contains information about a requested task, in the following format
            {
                "task_id": id of the task, either
                        "community_detection",
                        "social_influence_analysis"
                        "link_prediction",
                        "node_embedding"
                        # TODO: more to be added
                "network": either: a string to identify the in-database network to perform the task on, or
                           a network in format of edge list, i.e., a list of dictionaries, each contains information
                            about an edge, each in the following format
                            {
                                "source": id of source node,
                                "target": id of target node,
                                "observed": True if the edge is observed in data, False otherwise (e.g., the edge is
                                    inferred by latent link detection algorithms)
                                "properties": dictionary that contains properties of the edge, in the following format
                                            {
                                                "weight": optional, weight of the edge
                                                "type": type of the edge, e.g., "work for", or "friend of",
                                                "confidence": optional, confidence/certainty of the edge
                                                ...
                                            }
                                ...
                            }
                "options:" dictionary that contains algorithm/method selection and its parameters to perform the task,
                    in the following format
                    {
                        "method": one of predefined methods corresponding to the "task_id"
                        "parameters": dictionary that contains information about predefined parameters for the selected
                            method
                    }
                "run_id": id for the run
            }
            the list of task_ids, the algorithms/methods for the tasks and their parameters will be described in another
            document
        :param params: dictionary that contain other options for the task, in the following format
            {
                "run_id": id of the run
                "save_db": database manager that can be utilized for saving the task result
                "output_directory": (optional) directory to save the task result to files
                "compressed": (optional) to compress the output files or not
            }
        :return: 1 if the task is performed successfully, or 0 otherwise
        """
        network = task['network']
        if type(network) == str:
            # TODO: retrieve network from database
            print('in-database network is not supported')
            # TODO: what should be returned?
            return None
        algorithm = task['options']['method']
        algorithm_params = task['options']['parameters']
        # print('algorithm_params = ', algorithm_params)

        # print('task = ', task['task_id'])
        if task['task_id'] == 'community_detection':
            # print('task: community detection\n\tmethod = ', algorithm)
            # print('\tparams = ', cd_params)
            self.community_detector = CommunityDetector(algorithm)
            return self.community_detector.perform(network, algorithm_params)
        elif task['task_id'] == 'social_influence_analysis':
            self.social_influence_analyzer = SocialInfluenceAnalyzer(algorithm)
            return self.social_influence_analyzer.perform(network, algorithm_params)
        elif task['task_id'] == 'link_prediction':
            self.link_predictor = LinkPredictor(algorithm)
            return self.link_predictor.perform(network, algorithm_params)
        elif task['task_id'] == 'node_embedding':
            self.node_embedder = NodeEmbedder(algorithm)
            return self.node_embedder.perform(network, algorithm_params)
        elif task['task_id'] == 'path_analysis':
            self.path_analyzer = PathAnalyzer(algorithm)
            return self.path_analyzer.perform(network, algorithm_params)
        else:
            print('task %s is not defined' % task['task_id'])
            return None
