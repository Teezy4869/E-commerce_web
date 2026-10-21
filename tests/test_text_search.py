"""
Tests for Text Search (TS-01, TS-02, TS-03)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.product_repository import ProductRepository
from application.query_service import QueryService
from application.search_service import SearchService


def setup():
    repo = ProductRepository()
    search = SearchService(repo)
    query = QueryService()
    return repo, search, query


def test_ts01_keyword_match():
    """TS-01: Exact/common keyword match — 'black shoes' returns black shoe products."""
    _, search, query = setup()
    q = query.text_query("black shoes")
    results = search.search(q)

    assert len(results) > 0, "Expected results for 'black shoes'"
    # All results should contain 'black' or 'shoes' in their searchable text
    for product, score in results:
        text = (product["name"] + " " + product["category"] + " " +
                product["color"] + " " + product.get("description", "")).lower()
        assert "black" in text or "shoes" in text, \
            f"Product '{product['name']}' does not match 'black shoes'"
    print("  PASS: TS-01 keyword match")


def test_ts02_multi_word_query():
    """TS-02: Multi-word query — higher scores for more matching terms."""
    _, search, _ = setup()
    results = search.search_text("black running shoes")

    assert len(results) > 0, "Expected results for 'black running shoes'"
    # First result should have highest score
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True), \
        "Results should be sorted by descending score"
    # Nike Running Shoes should score highest (matches black, running, shoes)
    top_product = results[0][0]
    top_score = results[0][1]
    assert top_score >= 3, \
        f"Top result should match at least 3 terms, got {top_score}"
    print("  PASS: TS-02 multi-word query")


def test_ts03_no_match():
    """TS-03: No matching product — 'green laptop' returns empty or no results."""
    _, search, query = setup()
    q = query.text_query("green laptop")
    results = search.search(q)

    # 'green' might match Green Hiking Shoes, but 'laptop' should have no product
    # Filter to products that match BOTH terms
    for product, score in results:
        text = (product["name"] + " " + product["category"] + " " +
                product["color"]).lower()
        # Score should be low (only partial match possible)
        assert score <= 1, \
            f"Unexpected high score {score} for 'green laptop' query"
    print("  PASS: TS-03 no match / low relevance")


def test_query_representation():
    """Verify QueryService produces correct text query representation."""
    _, _, query = setup()
    q = query.text_query("black shoes")
    assert q["type"] == "text", f"Expected type 'text', got '{q['type']}'"
    assert q["query"] == "black shoes", f"Expected query 'black shoes'"
    print("  PASS: text query representation")


def test_ts05_invalid_query():
    """Invalid text input is rejected clearly."""
    _, search, query = setup()
    try:
        query.text_query("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty text query")

    try:
        search.search({"type": "text", "query": ""})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty search query")
    print("  PASS: TS-05 invalid query handling")


if __name__ == "__main__":
    print("\n=== TEXT SEARCH TESTS ===\n")
    test_ts01_keyword_match()
    test_ts02_multi_word_query()
    test_ts03_no_match()
    test_query_representation()
    test_ts05_invalid_query()
    print("\n  All text search tests passed!\n")
