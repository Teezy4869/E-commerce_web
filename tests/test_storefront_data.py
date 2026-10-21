"""Phase 2 catalogue checks that exercise the preserved search service."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.search_service import SearchService
from data.product_repository import ProductRepository


class StorefrontDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = ProductRepository()

    def test_vietnamese_query_retrieves_localized_products(self):
        results = SearchService(self.repository).search_text("giày trắng")
        self.assertTrue(results)
        self.assertTrue(any("trắng" in product["name_vi"] for product, _ in results))

    def test_catalogue_has_display_prices_and_images(self):
        products = self.repository.all_products()
        self.assertEqual(len(products), 12)
        for product in products:
            self.assertTrue(product["name_vi"])
            self.assertIsInstance(product["price_vnd"], int)
            self.assertGreater(product["price_vnd"], 0)
            image = os.path.join(os.path.dirname(os.path.dirname(__file__)), product["image"])
            self.assertTrue(os.path.isfile(image), image)


if __name__ == "__main__":
    unittest.main()
