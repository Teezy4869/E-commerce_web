import json
import os


class OrderRepository:
    """
    Data Layer — OrderRepository

    Provides access to order data.
    Supports Search Order (UC-05) and View Order (UC-07).
    """

    def __init__(self, data_path=None):
        if data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base_dir, "dataset", "orders.json")

        with open(data_path, "r", encoding="utf-8") as f:
            self.orders = json.load(f)

    def all_orders(self):
        """Return all orders."""
        return self.orders

    def find_order(self, order_id):
        """Find an order by order_id. Returns the order dict or None."""
        for order in self.orders:
            if order["order_id"] == order_id:
                return order
        return None
