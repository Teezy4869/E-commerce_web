"""
Tests for Ranking Service (RK-01, RK-02, RK-03)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.ranking_service import RankingService


def setup():
    return RankingService()


def test_rk01_descending_score():
    """RK-01: Verify results are sorted by descending score."""
    ranking = setup()
    candidates = [
        ({"id": 1, "name": "A"}, 1),
        ({"id": 2, "name": "B"}, 3),
        ({"id": 3, "name": "C"}, 2),
    ]
    ranked = ranking.rank(candidates)
    scores = [r["score"] for r in ranked]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], \
            f"Score {scores[i]} should be >= {scores[i + 1]}"
    print("  PASS: RK-01 descending score order")


def test_rk02_best_first():
    """RK-02: Best candidate appears first."""
    ranking = setup()
    candidates = [
        ({"id": 1, "name": "Low"}, 1),
        ({"id": 2, "name": "High"}, 5),
        ({"id": 3, "name": "Mid"}, 3),
    ]
    ranked = ranking.rank(candidates)
    assert ranked[0]["product"]["name"] == "High", \
        f"Expected 'High' first, got '{ranked[0]['product']['name']}'"
    assert ranked[0]["rank"] == 1, \
        f"Expected rank 1, got {ranked[0]['rank']}"
    print("  PASS: RK-02 best candidate first")


def test_rk03_stable_structure():
    """RK-03: Every ranked result contains product, score, and rank."""
    ranking = setup()
    candidates = [
        ({"id": 1, "name": "A", "category": "x"}, 2.5),
        ({"id": 2, "name": "B", "category": "y"}, 1.0),
    ]
    ranked = ranking.rank(candidates)
    for r in ranked:
        assert "product" in r, "Missing 'product' key"
        assert "score" in r, "Missing 'score' key"
        assert "rank" in r, "Missing 'rank' key"
    print("  PASS: RK-03 stable result structure")


def test_empty_candidates():
    """Edge case: ranking empty candidate list."""
    ranking = setup()
    ranked = ranking.rank([])
    assert ranked == [], "Expected empty list for empty candidates"
    print("  PASS: empty candidates")


def test_float_score_rounding():
    """Verify float scores are rounded to 4 decimal places."""
    ranking = setup()
    candidates = [
        ({"id": 1, "name": "A"}, 0.123456789),
    ]
    ranked = ranking.rank(candidates)
    assert ranked[0]["score"] == 0.1235, \
        f"Expected 0.1235, got {ranked[0]['score']}"
    print("  PASS: float score rounding")


if __name__ == "__main__":
    print("\n=== RANKING TESTS ===\n")
    test_rk01_descending_score()
    test_rk02_best_first()
    test_rk03_stable_structure()
    test_empty_candidates()
    test_float_score_rounding()
    print("\n  All ranking tests passed!\n")
