class RankingService:
    """
    Application Layer — RankingService

    Takes candidate products with retrieval scores and produces
    an ordered result list.

    The baseline uses simple score-based ranking without learned models,
    popularity weighting, or business-signal adjustments.
    """

    def rank(self, candidates):
        """
        Rank a list of (product, score) tuples.

        Returns a list of dicts:
            [{"product": product, "score": score, "rank": rank}, ...]
        sorted by descending score.
        """
        # Sort by score descending
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x[1],
            reverse=True
        )

        ranked_results = []
        for rank_position, (product, score) in enumerate(sorted_candidates, 1):
            ranked_results.append({
                "product": product,
                "score": round(score, 4) if isinstance(score, float) else score,
                "rank": rank_position
            })

        return ranked_results
