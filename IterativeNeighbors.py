from sklearn.base import BaseEstimator, ClusterMixin
import numpy as np
from sklearn.metrics import pairwise_distances

class IterativeNeighbors(BaseEstimator, ClusterMixin):
    def __init__(self, k=5, max_clusters=3):
        self.k = k
        self.max_clusters = max_clusters

    def fit_predict(self, X, y=None):
        self.X = X
        n_samples = X.shape[0]
        self.labels_ = -np.ones(n_samples, dtype=int)
        current_label = 0
        visited = np.zeros(n_samples, dtype=bool)
        distances = pairwise_distances(X)

        while not all(visited) and current_label < self.max_clusters:
            unvisited_indices = np.where(~visited)[0]
            i = unvisited_indices[0]
            cluster = self._iterative_cluster(i, distances, visited)
            for idx in cluster:
                self.labels_[idx] = current_label
                visited[idx] = True
            current_label += 1

        # Assigner les points restants au cluster le plus proche
        for i in range(n_samples):
            if self.labels_[i] == -1:
                dists = []
                for label in range(current_label):
                    cluster_indices = np.where(self.labels_ == label)[0]
                    d = pairwise_distances(X[i].reshape(1, -1), X[cluster_indices]).mean()
                    dists.append(d)
                closest_cluster = np.argmin(dists)
                self.labels_[i] = closest_cluster

        return self.labels_

    def _iterative_cluster(self, index, distances, visited):
        neighbors = [index]
        remaining = set(np.where(~visited)[0])
        remaining.discard(index)

        while len(neighbors) < self.k and remaining:
            next_neighbor = min(remaining, key=lambda idx: np.mean(distances[idx][neighbors]))
            neighbors.append(next_neighbor)
            remaining.remove(next_neighbor)
        return neighbors
