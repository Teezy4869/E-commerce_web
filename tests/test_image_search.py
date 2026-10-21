"""
Tests for Image Search (IS-01, IS-02, IS-03)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from application.query_service import QueryService
from application.search_service import SearchService
from application.image_service import ImageService
from application.ranking_service import RankingService
from presentation.image_upload import ImageUpload


def setup():
    repo = ProductRepository()
    vector_index = VectorIndex(repo)
    search = SearchService(repo, vector_index)
    query = QueryService()
    image = ImageService()
    ranking = RankingService()
    return repo, vector_index, search, query, image, ranking


def test_is01_similar_vector():
    """IS-01: Query embedding close to a product embedding gives high similarity."""
    _, vector_index, search, query, _, ranking = setup()

    # Use an embedding very close to product 1 (Nike Running Shoes: [0.9, 0.1, 0.2])
    query_embedding = [0.90, 0.10, 0.20]
    q = query.image_query(query_embedding)
    candidates = search.search(q)
    ranked = ranking.rank(candidates)

    assert len(ranked) > 0, "Expected results for similar vector"
    # Product 1 should be the top result or near top
    top = ranked[0]
    assert top["score"] > 0.9, \
        f"Expected high similarity for near-identical vector, got {top['score']}"
    print("  PASS: IS-01 similar vector match")


def test_is02_multiple_candidates():
    """IS-02: Image search returns multiple candidates in descending similarity order."""
    _, _, search, query, _, ranking = setup()

    query_embedding = [0.85, 0.15, 0.25]
    q = query.image_query(query_embedding)
    candidates = search.search(q)
    ranked = ranking.rank(candidates)

    assert len(ranked) > 1, \
        f"Expected multiple candidates, got {len(ranked)}"
    # Verify descending order
    scores = [r["score"] for r in ranked]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], \
            f"Score {scores[i]} should be >= {scores[i + 1]}"
    print("  PASS: IS-02 multiple candidates in order")


def test_is03_zero_vector():
    """IS-03: Zero embedding does not crash; similarity returns 0.0."""
    _, vector_index, search, query, _, ranking = setup()

    query_embedding = [0.0, 0.0, 0.0]
    q = query.image_query(query_embedding)
    candidates = search.search(q)
    ranked = ranking.rank(candidates)

    # Should not crash
    for r in ranked:
        assert r["score"] == 0.0, \
            f"Expected 0.0 similarity for zero vector, got {r['score']}"
    print("  PASS: IS-03 zero-vector safety")


def test_image_query_representation():
    """Verify QueryService produces correct image query representation."""
    _, _, _, query, _, _ = setup()
    embedding = [0.5, 0.3, 0.2]
    q = query.image_query(embedding)
    assert q["type"] == "image", f"Expected type 'image', got '{q['type']}'"
    assert q["embedding"] == [0.5, 0.3, 0.2], \
        f"Expected embedding [0.5, 0.3, 0.2]"
    print("  PASS: image query representation")


def test_image_service_embedding():
    """Verify ImageService creates embeddings from direct vectors."""
    _, _, _, _, image, _ = setup()
    embedding = image.create_embedding([0.8, 0.2, 0.1])
    assert isinstance(embedding, np.ndarray), "Expected numpy array"
    assert len(embedding) == 3, "Expected 3-dimensional embedding"
    print("  PASS: ImageService embedding creation")


def test_is06_image_upload_component():
    """ImageUpload delegates supported sample images to ImageService."""
    _, _, _, _, image, _ = setup()
    uploader = ImageUpload(image)
    embedding = uploader.upload("images/query_shoes.jpg")
    assert len(embedding) == 3
    assert embedding == [0.88, 0.12, 0.22]
    print("  PASS: IS-06 ImageUpload component integration")


def test_is07_invalid_image_inputs():
    """Unsupported image paths and vector dimensions are rejected clearly."""
    _, vector_index, _, _, image, _ = setup()
    try:
        image.create_embedding("images/unknown.jpg")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for unknown image path")

    try:
        vector_index.search_similar([0.1, 0.2])
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for embedding dimension mismatch")
    print("  PASS: IS-07 invalid image inputs")


if __name__ == "__main__":
    print("\n=== IMAGE SEARCH TESTS ===\n")
    test_is01_similar_vector()
    test_is02_multiple_candidates()
    test_is03_zero_vector()
    test_image_query_representation()
    test_image_service_embedding()
    test_is06_image_upload_component()
    test_is07_invalid_image_inputs()
    print("\n  All image search tests passed!\n")
