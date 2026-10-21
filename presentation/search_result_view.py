class SearchResultView:
    """
    Presentation Layer — SearchResultView

    Displays returned products and ranking information to the user.
    """

    @staticmethod
    def display_ranked_results(ranked_results, title="Search Results"):
        """Display a list of ranked results."""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")

        if not ranked_results:
            print("  No results found.")
            print(f"{'=' * 60}")
            return

        for result in ranked_results:
            product = result["product"]
            score = result["score"]
            rank = result["rank"]

            print(f"\n  Rank #{rank}")
            print(f"  Name:     {product['name']}")
            print(f"  Category: {product['category']}")
            print(f"  Color:    {product['color']}")
            print(f"  Price:    ${product['price']}")
            print(f"  Score:    {score}")
            print(f"  {'-' * 40}")

        print(f"\n  Total results: {len(ranked_results)}")
        print(f"{'=' * 60}")

    @staticmethod
    def display_order(order):
        """Display order information."""
        print(f"\n{'=' * 60}")
        print(f"  Order Information")
        print(f"{'=' * 60}")

        if order is None:
            print("  Order not found.")
        else:
            print(f"  Order ID:    {order['order_id']}")
            print(f"  Customer:    {order['customer_id']}")
            print(f"  Date:        {order['date']}")
            print(f"  Status:      {order['status']}")
            print(f"  Total:       ${order['total']}")

        print(f"{'=' * 60}")
