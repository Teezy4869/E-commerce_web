import json
import os


class ProductRepository:
    """
    Data Layer — ProductRepository

    Provides access to product data without exposing storage details
    to application services.

    Loads products from the JSON dataset file.
    """

    def __init__(self, data_path=None):
        if data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base_dir, "dataset", "products.json")

        with open(data_path, "r", encoding="utf-8") as f:
            self.products = json.load(f)

    def all_products(self):
        """Return all products in the repository."""
        return self.products

    def get_by_id(self, product_id):
        """Return a single product by its ID, or None if not found."""
        for product in self.products:
            if product["id"] == product_id:
                return product
        return None
