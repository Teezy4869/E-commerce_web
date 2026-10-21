"""Phase 3: catalogue persistence, selection, filters and HTTP contract."""

import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.catalog_service import CatalogService
from data.catalog_repository import CatalogRepository
from presentation.web_server import create_web_server
from scripts.sync_catalog_scope import sync


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temporary.name) / "catalog.sqlite3"
        cls.repository = CatalogRepository(db_path=cls.db_path)
        cls.service = CatalogService(cls.repository)
        with patch.dict(os.environ, {"COGU_CATALOG_DB": str(cls.db_path)}):
            cls.server = create_web_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temporary.cleanup()

    def get(self, path):
        try:
            with urlopen(self.base + path) as response:
                return response.status, response.headers, response.read()
        except HTTPError as error:
            return error.code, error.headers, error.read()

    def test_seed_has_three_categories_and_preserves_legacy_fixture(self):
        result = self.service.list_products({"page_size": ["48"]})
        self.assertEqual(result["total"], 38)
        self.assertEqual(len(result["products"]), 38)
        categories = {item["category"]: item["count"] for item in self.repository.facets()["categories"]}
        self.assertEqual(categories, {"shirt": 11, "trousers": 12, "shoes": 15})
        self.assertEqual({item["id"] for item in result["products"] if item["id"] >= 31}, set(range(31, 46)))
        for product in result["products"]:
            self.assertTrue((Path(__file__).resolve().parents[1] / product["image"]).is_file())
            self.assertGreater(product["price_vnd"], 0)
            detail = self.repository.get_product(product["slug"])
            self.assertTrue(detail["variants"])
            self.assertTrue(detail["material"])
        original = json.loads((Path(__file__).resolve().parents[1] / "dataset" / "products.json").read_text(encoding="utf-8"))
        self.assertEqual(len(original), 12)

    def test_filters_sort_and_pagination(self):
        result = self.service.list_products({"category": ["shirt"], "page_size": ["2"], "page": ["2"], "sort": ["price_asc"]})
        self.assertEqual(result["total"], 11)
        self.assertEqual(result["pages"], 6)
        self.assertEqual(len(result["products"]), 2)
        self.assertTrue(all(item["category"] == "shirt" for item in result["products"]))
        self.assertLessEqual(result["products"][0]["price_vnd"], result["products"][1]["price_vnd"])
        matched = self.service.list_products({"color": ["Trắng ngà"], "size": ["M"]})
        self.assertIn("ao-thun-oversize-essential", [item["slug"] for item in matched["products"]])
        for bad in ({"sort": ["DROP TABLE"]}, {"page": ["0"]}, {"page_size": ["999"]},
                    {"min_price": ["200"], "max_price": ["100"]},
                    {"category": ["other"]}, {"category": ["bag"]}, {"category": ["jacket"]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.service.list_products(bad)

    def test_color_size_resolve_distinct_persistent_stock_records(self):
        slug = "ao-thun-oversize-essential"
        green_m = self.repository.get_variant(slug, "Xanh rừng", "M")
        green_l = self.repository.get_variant(slug, "Xanh rừng", "L")
        ivory_m = self.repository.get_variant(slug, "Trắng ngà", "M")
        self.assertEqual((green_m["stock"], green_l["stock"], ivory_m["stock"]), (7, 0, 14))
        self.assertEqual(len({green_m["sku"], green_l["sku"], ivory_m["sku"]}), 3)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute("UPDATE product_variants SET stock = ? WHERE sku = ?", (11, ivory_m["sku"]))
            db.commit()
        again = CatalogRepository(db_path=self.db_path)
        self.assertEqual(again.get_variant(slug, "Trắng ngà", "M")["stock"], 11)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute("UPDATE product_variants SET stock = ? WHERE sku = ?", (14, ivory_m["sku"]))
            db.commit()

    def test_catalogue_sync_removes_old_category_and_keeps_existing_stock(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "shop.sqlite3"
            CatalogRepository(db_path=path)
            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE product_variants SET stock = 3 WHERE id = 1706")
                db.execute("""INSERT INTO products
                    (id, slug, name_vi, description_vi, category, material, price_vnd, image, is_new, is_bestseller)
                    VALUES (90, 'old-watch', 'Đồng hồ cũ', 'Món cũ', 'watch', 'Thép', 100000,
                            'images/catalog-17.png', 0, 0)""")
                db.commit()
            outcome = sync(db_path=path)
            self.assertEqual((outcome["added"], outcome["removed"]), (0, 1))
            self.assertTrue(Path(outcome["backup"]).is_file())
            repeated = sync(db_path=path)
            self.assertEqual((repeated["added"], repeated["removed"]), (0, 0))
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT stock FROM product_variants WHERE id = 1706").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM products WHERE category = 'watch'").fetchone()[0], 0)
    def test_catalog_apis_and_pages(self):
        for path in ("/shop", "/product?slug=ao-thun-oversize-essential", "/css/catalog.css", "/js/shop.js", "/images/catalog-17.png"):
            status, _, _ = self.get(path)
            self.assertEqual(status, 200, path)
        status, _, body = self.get("/api/catalog/products?page_size=12")
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual((result["total"], len(result["products"]), result["pages"]), (38, 12, 4))
        status, _, body = self.get("/api/catalog/products/ao-thun-oversize-essential")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["product"]["variants"]), 8)
        for color, size, expected in (("Xanh rừng", "M", 7), ("Xanh rừng", "L", 0), ("Trắng ngà", "M", 14)):
            path = f"/api/catalog/stock?slug=ao-thun-oversize-essential&color={quote(color)}&size={size}"
            status, _, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["variant"]["stock"], expected)
        for path, status_expected in (("/api/catalog/products?sort=invalid", 400),
                                      ("/api/catalog/stock?slug=x&color=x&size=x", 404),
                                      ("/api/catalog/products/no-such-product", 404),
                                      ("/dataset/catalog_seed.json", 404)):
            status, _, _ = self.get(path)
            self.assertEqual(status, status_expected)

    def test_web_multimodal_search_uses_full_catalog(self):
        for endpoint, payload in (("text", {"text": "áo thun oversize"}),
                                  ("voice", {"audio_input": "áo thun oversize"})):
            request = Request(self.base + f"/api/search/{endpoint}",
                              data=json.dumps(payload).encode("utf-8"),
                              headers={"Content-Type": "application/json"})
            with urlopen(request) as response:
                data = json.load(response)
            self.assertIn(17, [item["product"]["id"] for item in data["results"]])
        request = Request(self.base + "/api/search/image",
                          data=json.dumps({"image_vector": [0.82, 0.14, 0.22]}).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            data = json.load(response)
        self.assertEqual(data["total_candidates"], 38)


if __name__ == "__main__":
    unittest.main()
