import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import collections
from scipy.sparse import csr_matrix


class PyPIGraph:

    def __init__(self, nodes_path, edges_path, features_path):

        self.nodes = pd.read_csv(nodes_path, na_filter=False)
        self.edges = pd.read_csv(edges_path, na_filter=False)
        self.features = pd.read_csv(features_path, na_filter=False)

        self.graph = nx.DiGraph() # Directed - but connections both ways
        self.graph.add_nodes_from(self.nodes.index.values)
        self.graph.add_edges_from(self.edges.values[:, 1:])

    def draw_rand_subgraph(self, size=1000, with_labels=False):
        pos = nx.random_layout(self.graph)

        rand_nodes = np.random.choice(self.nodes.index.values, size=size)
        subgraph = self.graph.subgraph(rand_nodes)

        nx.draw_networkx(subgraph, pos=pos, width=0.5, node_size=1, with_labels=with_labels)
        plt.show()

    def degree_distribution(self):
        degree_sequence = sorted([d for n, d in self.graph.degree()], reverse=True)  # degree sequence
        degreeCount = collections.Counter(degree_sequence)
        deg, cnt = zip(*degreeCount.items())

        for d, c in zip(deg, cnt):
            print(f'Degree: {d} | Count: {c}')

    def num_nodes_with_connections(self):
        return sum([1 for n in self.graph.nodes if self.has_connections(n)])

    def num_nodes_with_features(self):
        return sum([1 for n in self.graph.nodes if self.has_features(n)])

    def num_nodes_with_connections_and_features(self):
        total = 0
        for n in self.graph.nodes:
            if self.has_connections(n) and self.has_features(n):
                total += 1
        return total

    def has_features(self, node_id):
        return len(self.features['language'].values[node_id]) > 0

    def has_connections(self, node_id):
        return self.graph.degree[node_id] > 0

    def get_dict_of_list_rep(self):
        dol = {}
        for n in self.graph.nodes:
            outs = [e[1] for e in self.graph.edges(n)]
            dol[n] = outs
        return dol

    def get_edge_csr(self):
        rows, cols = [], []
        for e in self.graph.edges():
            rows.append(e[0])
            cols.append(e[1])

        data = np.ones(len(rows))
        return csr_matrix((data, (rows, cols)))