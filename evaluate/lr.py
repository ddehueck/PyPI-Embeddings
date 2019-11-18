from collections import defaultdict
from six import iteritems
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.utils import shuffle as skshuffle
from sklearn.preprocessing import MultiLabelBinarizer
import pandas as pd
from tqdm import tqdm
import numpy as np
from scipy.sparse import csr_matrix


class LREvaluation:
    """
    Modified version of Bryan Perozzi's evaluation task from "DeepWalk: Online Learning of Social Representations"
    Original Code: https://github.com/phanein/deepwalk/blob/master/example_graphs/scoring.py
    """
    
    def __init__(self, nodes_topics_path, eval_topics_path):
        self.node_topics_df = pd.read_csv(nodes_topics_path, na_filter=False)
        # Id of nodes that have labeled topics
        self.labeled_node_ids = list(set(self.node_topics_df['node_id'].values))
        
        self.labels_matrix = self._build_labels_matrix(nodes_topics_path)
        self.mlb = self._build_mlb(eval_topics_path)
        
    def _build_labels_matrix(self, nodes_topics_path):
        # labels_matrix is N x num_labels - but saved as a CSR matrix!
        rows = self.node_topics_df.values[:, 1]
        
        # Convert overall node ids into just the ones being evaluated
        for i in range(len(rows)):
            rows[i] = self.labeled_node_ids.index(rows[i])
        
        # Cols are topic ids
        cols = self.node_topics_df.values[:, 2]
        data = np.ones(len(rows))
        labels_matrix = csr_matrix((data, (rows, cols)))
        
        return labels_matrix
    
    def _build_mlb(self, eval_topics_path):
        topic_ids = pd.read_csv(eval_topics_path, na_filter=False).index.values
        return MultiLabelBinarizer(range(len(topic_ids)))

    def evaluate(self, features_matrix, num_shuffles=10, training_percents=[0.1, 0.5, 0.9]):
        """
        Runs an evaluation task - logistic regression with the embeddings as features
        Evaluates embeddings over various training precentages
        
        :param features_matrix: N x 256 matrix
        returns: None - prints results
        """
        
        # Get labels
        labels_matrix, mlb = self.labels_matrix, self.mlb

        # Shuffle, to create train/test groups
        shuffles = []
        for x in range(num_shuffles):
            shuffles.append(skshuffle(features_matrix, labels_matrix))

        # Score each train/test group
        all_results = defaultdict(list) # Will add a list to any key call that doesn't exist yet

        for train_percent in tqdm(training_percents):
            for shuf in shuffles:

                X, y = shuf

                training_size = int(train_percent * X.shape[0])

                X_train = X[:training_size, :]
                y_train_ = y[:training_size]

                y_train = [[] for x in range(y_train_.shape[0])]

                cy = y_train_.tocoo()
                for i, j in zip(cy.row, cy.col):
                    y_train[i].append(j)

                assert sum(len(l) for l in y_train) == y_train_.nnz

                X_test = X[training_size:, :]
                y_test_ = y[training_size:]

                y_test = [[] for _ in range(y_test_.shape[0])]

                cy = y_test_.tocoo()
                for i, j in zip(cy.row, cy.col):
                    y_test[i].append(j)

                clf = TopKRanker(LogisticRegression(
                    solver='lbfgs',
                    max_iter=10000,
                ))
                clf.fit(X_train, y_train_)

                # find out how many labels should be predicted
                top_k_list = [len(l) for l in y_test]
                preds = clf.predict(X_test, top_k_list)

                results = {}
                averages = ["micro", "macro"]
                for average in averages:
                    results[average] = f1_score(mlb.fit_transform(y_test), mlb.fit_transform(preds), average=average)

                all_results[train_percent].append(results)

        print('Results, using embeddings of dimensionality', X.shape[1])
        print('-------------------')
        for train_percent in sorted(all_results.keys()):
            print('Train percent:', train_percent)
            print('-------------------')
            
            for index, result in enumerate(all_results[train_percent]):
                print('Shuffle #%d:   ' % (index + 1), result)
            avg_score = defaultdict(float)
            
            for score_dict in all_results[train_percent]:
                for metric, score in iteritems(score_dict):
                    avg_score[metric] += score
                    
            for metric in avg_score:
                avg_score[metric] /= len(all_results[train_percent])
                
            print('Average score:', dict(avg_score))
            print('-------------------')
            
            
class TopKRanker(OneVsRestClassifier):
    def predict(self, X, top_k_list):
        assert X.shape[0] == len(top_k_list)
        
        probs = np.asarray(super(TopKRanker, self).predict_proba(X))
        all_labels = []
        
        for i, k in enumerate(top_k_list):
            probs_ = probs[i, :]
            labels = self.classes_[probs_.argsort()[-k:]].tolist()
            all_labels.append(labels)
        return all_labels
    