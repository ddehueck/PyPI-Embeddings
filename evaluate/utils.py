import csv
import torch
import numpy as np


def read_deepwalk_embeds(path, dim=256):
    node_id_vector_dict = {}
    with open(path) as f:
        f.readline() # Skip header
        for l in f:
            l = l.replace("\n", "")
            l = l.split(" ")

            node_id = l[0]
            vector = [float(s) for s in l[1:]]

            assert len(vector) == dim
            node_id_vector_dict[node_id] = vector

    return node_id_vector_dict


def get_tsv_dict(metadata, tensor) -> dict:

    with open(metadata) as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        m_data = [r[0] for r in reader]

    with open(tensor) as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        t_data = [np.array(r) for r in reader]

    return dict(zip(m_data, t_data))


def get_random():
    name_vector_dict = get_tsv_dict('./vectors/doc2vec/metadata.tsv', './vectors/doc2vec/tensors.tsv')
    names = name_vector_dict.keys()
    vectors = [torch.randn(256).numpy() for i in range(len(names))]

    return dict(zip(names, vectors))


def build_features_matrix(labeled_node_ids, node_names, name_vec_dict):
    # N x 256
    features_matrix = []
    for n_id in labeled_node_ids:
        name = node_names[n_id]
        vec = name_vec_dict[name]
        vec = list(map(float, vec))
        features_matrix.append(vec)
    return np.array(features_matrix)