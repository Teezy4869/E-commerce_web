import numpy as np


class VectorIndex:
    """
    Data Layer — VectorIndex

    In-memory index over product image embeddings. Uses cosine similarity
    for the baseline image-retrieval prototype.
    """

    def __init__(self, product_repository):
        self.embeddings = {}
        for product in product_repository.all_products():
            product_id = product["id"]
            embedding = product.get("embedding")
            if embedding is not None:
                self.embeddings[product_id] = self._validate_vector(embedding)

        self.dimension = None
        if self.embeddings:
            self.dimension = len(next(iter(self.embeddings.values())))

    @staticmethod
    def _validate_vector(vector):
        try:
            array = np.asarray(vector, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError("embedding must contain numeric values") from exc

        if array.ndim != 1 or array.size == 0:
            raise ValueError("embedding must be a non-empty one-dimensional vector")
        if not np.all(np.isfinite(array)):
            raise ValueError("embedding must contain finite values")
        return array

    def get_embedding(self, product_id):
        return self.embeddings.get(product_id)

    def all_embeddings(self):
        return dict(self.embeddings)

    def search_similar(self, query_embedding, top_k=None):
        """Return (product_id, cosine_similarity) sorted descending."""
        query_vector = self._validate_vector(query_embedding)
        if self.dimension is not None and len(query_vector) != self.dimension:
            raise ValueError(
                f"embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(query_vector)}"
            )

        scores = [
            (product_id, self._cosine_similarity(query_vector, embedding))
            for product_id, embedding in self.embeddings.items()
        ]
        scores.sort(key=lambda item: item[1], reverse=True)

        if top_k is not None:
            if not isinstance(top_k, int) or top_k < 1:
                raise ValueError("top_k must be a positive integer")
            return scores[:top_k]
        return scores

    @staticmethod
    def _cosine_similarity(a, b):
        numerator = np.dot(a, b)
        denominator = np.linalg.norm(a) * np.linalg.norm(b)
        if denominator == 0:
            return 0.0
        return float(numerator / denominator)
