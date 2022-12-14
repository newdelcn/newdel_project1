import numpy as np
from sklearn.neighbors import NearestNeighbors


class Smote:

    def __init__(self, sampling_rate=10, k=5):
        self.sampling_rate = sampling_rate
        self.k = k
        self.newindex = 0

    def fit(self, X, y=None):
        X = X.astype(np.uint8)
        if y is not None:
            negative_X = X[y < 0.15]
            negative_Y = y[y < 0.15]
            X = X[y >= 0.15]
            Y = y[y >= 0.15]
        n_samples, n_features = X.shape
        self.synthetic = np.zeros((n_samples * self.sampling_rate, n_features))
        self.synthetic_y = np.zeros(n_samples * self.sampling_rate)
        knn = NearestNeighbors(n_neighbors=self.k, metric='jaccard').fit(X)
        for i in range(len(X)):
            k_neighbors = knn.kneighbors(X[i].reshape(1, -1),
                                         return_distance=False)[0]
            self.synthetic_samples(X, Y, i, k_neighbors)

        if y is not None:
            return (np.concatenate((self.synthetic, X, negative_X), axis=0),
                    np.concatenate((self.synthetic_y, Y, negative_Y), axis=0))

        return np.concatenate((self.synthetic, X), axis=0)

    def synthetic_samples(self, X, Y, i, k_neighbors):
        for j in range(self.sampling_rate):
            tmp = np.array([X[n] for n in k_neighbors])
            tmp_Y = np.array([Y[n] for n in k_neighbors])
            random = np.random.uniform(low=0, high=1.0, size=(5))
            weights = random / np.sum(random)
            x = (tmp.T * weights).T
            y = tmp_Y * weights

            result_x = np.sum(x, axis=0)
            result_y = y.sum()
            self.synthetic[self.newindex] = result_x
            self.synthetic_y[self.newindex] = result_y
