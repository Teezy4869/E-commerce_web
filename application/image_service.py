import os

import numpy as np


class ImageService:
    """
    Application Layer — ImageService

    Prepares image representations for image search.

    The baseline uses artificial, deterministic embeddings. It does not
    call a real image encoder.
    """

    SIMULATED_EMBEDDINGS = {
        "images/query_shoes.jpg": np.array([0.88, 0.12, 0.22], dtype=float),
        "images/query_bag.jpg": np.array([0.12, 0.22, 0.88], dtype=float),
        "images/query_watch.jpg": np.array([0.22, 0.82, 0.12], dtype=float),
    }

    @staticmethod
    def _validate_embedding(embedding):
        if not hasattr(embedding, "__len__") or len(embedding) == 0:
            raise ValueError("image embedding must be a non-empty sequence")

        try:
            vector = np.array(embedding, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError("image embedding must contain numeric values") from exc

        if vector.ndim != 1:
            raise ValueError("image embedding must be one-dimensional")
        if not np.all(np.isfinite(vector)):
            raise ValueError("image embedding must contain finite values")

        return vector

    def create_embedding(self, image_input):
        """
        Create a deterministic feature vector from a supported image input.

        Supported baseline inputs:
        - a direct numeric vector, or
        - one of the predefined sample-image paths.
        """
        if isinstance(image_input, (list, tuple, np.ndarray)):
            return self._validate_embedding(image_input)

        if not isinstance(image_input, str) or not image_input.strip():
            raise ValueError("image input must be a vector or supported image path")

        normalized_path = image_input.strip().replace("\\", "/")
        if normalized_path in self.SIMULATED_EMBEDDINGS:
            return self.SIMULATED_EMBEDDINGS[normalized_path].copy()

        # Keep the baseline deterministic and honest: an unknown image path
        # cannot be encoded because no real image model is part of this phase.
        if not os.path.basename(normalized_path):
            raise ValueError("image path must identify a file")
        raise ValueError(
            f"unsupported image input '{image_input}'. "
            "Use a sample image path or a direct embedding vector."
        )

    def prepare_query(self, image_input):
        """Return an image embedding as a JSON-serializable list."""
        return self.create_embedding(image_input).tolist()
