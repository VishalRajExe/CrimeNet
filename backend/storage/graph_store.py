"""
graph_store.py - Operational Graph Store for CrimeNet
Manages live operational network topology, suspects, transactions, phone calls, vehicles.
Supports Neo4j bolt driver when NEO4J_URI is configured, with a high-performance
in-memory / NetworkX property graph engine for instantaneous local queries.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import networkx as nx

from ..config import STORAGE_DIR

logger = logging.getLogger("crimenet.storage.graph")

GRAPH_BACKUP_PATH = STORAGE_DIR / "operational_graphs.json"


class PropertyGraphStore:
    def __init__(self):
        # Dictionary of case_id -> nx.MultiDiGraph
        self.graphs: Dict[str, nx.MultiDiGraph] = {}
        self.neo4j_driver = None
        self._init_neo4j()
        self._load_local_graphs()

    def _init_neo4j(self):
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")
        if neo4j_uri:
            try:
                from neo4j import GraphDatabase
                self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
                logger.info("Connected to remote Neo4j instance at %s", neo4j_uri)
            except Exception as e:
                logger.warning("Neo4j driver connection failed (%s), using local property graph.", e)

    def _load_local_graphs(self):
        if GRAPH_BACKUP_PATH.exists():
            try:
                with open(GRAPH_BACKUP_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for case_id, gdata in data.items():
                        g = nx.MultiDiGraph()
                        for node in gdata.get("nodes", []):
                            nid = node.get("id")
                            if nid:
                                g.add_node(nid, **node)
                        for edge in gdata.get("edges", []):
                            u = edge.get("source")
                            v = edge.get("target")
                            if u and v:
                                g.add_edge(u, v, **edge)
                        self.graphs[case_id] = g
                logger.info("Loaded %d operational graphs from local storage.", len(self.graphs))
            except Exception as e:
                logger.error("Error loading operational graph backups: %s", e)

    def save_to_disk(self):
        try:
            dump = {}
            for cid, g in self.graphs.items():
                nodes = [dict(data, id=n) for n, data in g.nodes(data=True)]
                edges = []
                for u, v, k, data in g.edges(keys=True, data=True):
                    edges.append(dict(data, source=u, target=v, key=k))
                dump[cid] = {"nodes": nodes, "edges": edges}
            with open(GRAPH_BACKUP_PATH, "w", encoding="utf-8") as f:
                json.dump(dump, f, indent=2)
        except Exception as e:
            logger.error("Failed saving operational graph to disk: %s", e)

    def get_graph(self, case_id: str) -> nx.MultiDiGraph:
        if case_id not in self.graphs:
            self.graphs[case_id] = nx.MultiDiGraph()
        return self.graphs[case_id]

    def add_node(self, case_id: str, node_id: str, **attributes):
        g = self.get_graph(case_id)
        if g.has_node(node_id):
            g.nodes[node_id].update(attributes)
        else:
            g.add_node(node_id, **attributes)
        self._sync_neo4j_node(node_id, attributes)

    def add_edge(self, case_id: str, source: str, target: str, **attributes):
        g = self.get_graph(case_id)
        g.add_edge(source, target, **attributes)
        self._sync_neo4j_edge(source, target, attributes)

    def set_graph_data(self, case_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        g = nx.MultiDiGraph()
        for n in nodes:
            nid = n.get("id")
            if nid:
                g.add_node(nid, **n)
        for e in edges:
            u = e.get("source")
            v = e.get("target")
            if u and v:
                g.add_edge(u, v, **e)
        self.graphs[case_id] = g
        self.save_to_disk()

    def get_graph_data(self, case_id: str) -> Dict[str, Any]:
        g = self.get_graph(case_id)
        nodes = []
        for n, d in g.nodes(data=True):
            entry = dict(d)
            entry["id"] = str(n)
            if "label" not in entry:
                entry["label"] = str(n)
            nodes.append(entry)
        edges = []
        for u, v, k, d in g.edges(keys=True, data=True):
            entry = dict(d)
            entry["source"] = str(u)
            entry["target"] = str(v)
            entry["id"] = entry.get("id", f"{u}->{v}_{k}")
            edges.append(entry)
        return {"nodes": nodes, "edges": edges}

    def _sync_neo4j_node(self, node_id: str, attrs: Dict[str, Any]):
        if not self.neo4j_driver:
            return
        try:
            with self.neo4j_driver.session() as session:
                label = attrs.get("type", "Entity").capitalize()
                query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
                session.run(query, id=node_id, props=attrs)
        except Exception as e:
            logger.debug("Neo4j sync node notice: %s", e)

    def _sync_neo4j_edge(self, u: str, v: str, attrs: Dict[str, Any]):
        if not self.neo4j_driver:
            return
        try:
            with self.neo4j_driver.session() as session:
                rel_type = attrs.get("label", attrs.get("relation", "CONNECTED_TO")).upper().replace(" ", "_")
                query = f"""
                MATCH (a {{id: $u}}), (b {{id: $v}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """
                session.run(query, u=u, v=v, props=attrs)
        except Exception as e:
            logger.debug("Neo4j sync edge notice: %s", e)


default_graph_store = PropertyGraphStore()
