"""Phase 6 search behavior, including the optional real image-encoder contract."""

import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from application.search_service import SearchService, fold_text
from application.visual_search import ImageEmbeddingAPI, VisualSearch, configured_visual_search
from data.catalog_repository import CatalogRepository
from data.catalog_search_repository import CatalogSearchRepository
from data.product_repository import ProductRepository
from presentation.web_server import create_web_server


class SearchClient:
    def call(self, path, body=None):
        request = Request(self.url + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)


class TextSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        catalog = CatalogRepository(db_path=Path(cls.temp.name) / "catalog.sqlite3")
        cls.search = SearchService(CatalogSearchRepository(catalog, ProductRepository()))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_vietnamese_accent_folding_and_relevance(self):
        self.assertEqual(fold_text("Đầm đỏ – giày trắng"), "dam do giay trang")
        accented = self.search.search_text("áo thun oversize")
        plain = self.search.search_text("ao thun oversize")
        self.assertEqual(accented[0][0]["slug"], "ao-thun-oversize-essential")
        self.assertEqual([p["id"] for p, _ in accented], [p["id"] for p, _ in plain])
        self.assertGreater(plain[0][1], plain[-1][1])

    def test_attributes_and_filters(self):
        results = self.search.search_text("cotton xanh rung M", {"category": "shirt", "color": "Xanh rừng",
            "size": "M", "min_price": 300000, "max_price": 500000})
        self.assertTrue(results)
        self.assertEqual(results[0][0]["slug"], "ao-thun-co-tron-xanh-rung")
        self.assertIn("ao-thun-oversize-essential", [item["slug"] for item, _ in results])
        self.assertTrue(all(item["category"] == "shirt" for item, _ in results))
        self.assertEqual(self.search.search_text("ao", {"category": "shoes"}), [])
        with self.assertRaises(ValueError):
            self.search.search_text("ao", {"max_price": 10, "min_price": 20})
        with self.assertRaises(ValueError):
            self.search.search_text("ao", {"sort_sql": "DROP TABLE products"})

    def test_invalid_encoder_configuration_remains_demo(self):
        with patch.dict(os.environ, {"COGU_IMAGE_ENCODER_URL": "http://remote.example/embed",
                                    "COGU_IMAGE_ENCODER_MODEL": "test"}):
            visual, reason = configured_visual_search(self.search.repository.catalog, ROOT / "images")
        self.assertIsNone(visual)
        self.assertIn("DEMO", reason)


class DemoSearchHTTPTests(SearchClient, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {"COGU_CATALOG_DB": str(Path(cls.temp.name) / "demo.sqlite3"),
                                    "COGU_IMAGE_ENCODER_URL": "", "COGU_IMAGE_ENCODER_MODEL": ""}):
            cls.server = create_web_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def test_voice_transcript_uses_enhanced_text_pipeline(self):
        status, body = self.call("/api/search/voice", {"audio_input": "Tìm áo thun oversize",
            "filters": {"category": "shirt"}})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["transcribed"], "Tìm áo thun oversize")
        self.assertEqual(body["results"][0]["product"]["slug"], "ao-thun-oversize-essential")
        self.assertEqual(body["pipeline"]["step_3_query"]["representation"]["type"], "voice")
        self.assertEqual(self.call("/api/search/text", {"text": "ao", "filters": {"bad": "x"}})[0], 400)

    def test_demo_image_mode_is_explicit_and_rejects_arbitrary_upload(self):
        status, capabilities = self.call("/api/search/capabilities")
        self.assertEqual(status, 200)
        self.assertEqual(capabilities["image_mode"], "demo")
        self.assertFalse(capabilities["upload_enabled"])
        self.assertIn("DEMO", capabilities["image_label"])
        self.assertEqual(self.call("/api/search/image", {"image_data": base64.b64encode(b"not an image").decode()})[0], 400)
        status, result = self.call("/api/search/image", {"image_path": "images/query_shoes.jpg"})
        self.assertEqual(status, 200)
        self.assertEqual(result["image_mode"], "demo")
        self.assertIn("DEMO", result["pipeline"]["step_2_image_service"]["action"])


class LocalEncoderHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        content = base64.b64decode(body["image_base64"], validate=True)
        self.requests.append((body["model"], body["mime_type"], hashlib.sha256(content).hexdigest()))
        digest = hashlib.sha256(content).digest()
        vector = [value / 255 for value in digest[:24]]
        response = json.dumps({"embedding": vector}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args):
        pass


class EncodedImageHTTPTests(SearchClient, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.encoder = ThreadingHTTPServer(("127.0.0.1", 0), LocalEncoderHandler)
        cls.encoder_thread = threading.Thread(target=cls.encoder.serve_forever, daemon=True)
        cls.encoder_thread.start()
        config = {"COGU_CATALOG_DB": str(Path(cls.temp.name) / "encoded.sqlite3"),
                  "COGU_IMAGE_ENCODER_URL": f"http://127.0.0.1:{cls.encoder.server_port}/embed",
                  "COGU_IMAGE_ENCODER_MODEL": "test-content-encoder"}
        with patch.dict(os.environ, config):
            cls.server = create_web_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.encoder.shutdown()
        cls.encoder.server_close()
        cls.thread.join(timeout=3)
        cls.encoder_thread.join(timeout=3)
        cls.temp.cleanup()

    def test_uploaded_bytes_match_encoded_catalogue_image(self):
        status, capabilities = self.call("/api/search/capabilities")
        self.assertEqual(status, 200)
        self.assertEqual(capabilities["image_mode"], "encoder")
        self.assertTrue(capabilities["upload_enabled"])
        content = (ROOT / "images" / "catalog-17.png").read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        self.assertIn(("test-content-encoder", "image/png", digest), LocalEncoderHandler.requests)
        status, body = self.call("/api/search/image", {"image_data": base64.b64encode(content).decode()})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["image_mode"], "encoder")
        self.assertEqual(body["results"][0]["product"]["slug"], "ao-thun-oversize-essential")
        self.assertAlmostEqual(body["results"][0]["score"], 1.0)
        shoes = (ROOT / "images" / "store-product-01.webp").read_bytes()
        status, shoes_result = self.call("/api/search/image", {"image_data": base64.b64encode(shoes).decode()})
        self.assertEqual(status, 200, shoes_result)
        self.assertEqual(shoes_result["results"][0]["product"]["slug"], "giay-chay-bo-nike-den")
        calls_before = len(LocalEncoderHandler.requests)
        cached = VisualSearch(CatalogRepository(db_path=Path(self.temp.name) / "encoded.sqlite3"), ROOT / "images",
                              ImageEmbeddingAPI(f"http://127.0.0.1:{self.encoder.server_port}/embed", "test-content-encoder"))
        self.assertEqual(cached.index.dimension, 24)
        self.assertEqual(len(LocalEncoderHandler.requests), calls_before, "Catalogue embeddings should be reused after restart")
        self.assertEqual(self.call("/api/search/image", {"image_data": base64.b64encode(b"not an image").decode()})[0], 400)
        self.assertEqual(self.call("/api/search/image", {"image_vector": [0.1, 0.2, 0.3]})[0], 400)
        self.assertTrue(all(model == "test-content-encoder" for model, _, _ in LocalEncoderHandler.requests))


if __name__ == "__main__":
    unittest.main()
