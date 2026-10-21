"""HTTP regression checks for public assets and protected order data."""

import json
import os
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from presentation.web_server import create_web_server


class WebSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"COGU_ADMIN_TOKEN": "test-only-admin-secret"}):
            cls.server = create_web_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, body=None, token=None):
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token is not None:
            headers["X-Admin-Token"] = token
        request = Request(
            self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            with urlopen(request) as response:
                return response.status, response.headers, response.read()
        except HTTPError as error:
            return error.code, error.headers, error.read()

    def test_order_apis_require_admin_token(self):
        for path, body in (("/api/orders", None), ("/api/search/order", {"order_id": "O001"})):
            for token in (None, "wrong-token"):
                status, _, content = self.request(path, body, token)
                self.assertEqual(status, 403)
                self.assertNotIn(b"C001", content)
            status, _, content = self.request(path, body, "test-only-admin-secret")
            self.assertEqual(status, 200)
            self.assertIn(b"O001", content)

    def test_static_access_is_confined(self):
        for path in ("/", "/css/style.css", "/js/app.js", "/images/store-product-01.webp"):
            status, _, _ = self.request(path)
            self.assertEqual(status, 200, path)
        for path in (
            "/web/%2e%2e/dataset/orders.json",
            "/images/%2e%2e/dataset/orders.json",
            "/web/..%5cdataset%5corders.json",
            "/dataset/orders.json",
            "/main.py",
        ):
            status, _, content = self.request(path)
            self.assertEqual(status, 404, path)
            self.assertNotIn(b"C001", content)

    def test_public_search_remains_available_without_cross_origin_wildcard(self):
        status, headers, content = self.request("/api/search/text", {"text": "black shoes"})
        self.assertEqual(status, 200)
        self.assertGreater(len(json.loads(content)["results"]), 0)
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

    def test_voice_and_image_routes_keep_working(self):
        for path, body in (
            ("/api/search/voice", {"audio_input": "find running shoes"}),
            ("/api/search/image", {"image_vector": [0.88, 0.12, 0.22]}),
        ):
            status, _, content = self.request(path, body)
            self.assertEqual(status, 200, path)
            self.assertGreater(len(json.loads(content)["results"]), 0)

    def test_invalid_search_payloads_return_client_errors(self):
        for path, body in (
            ("/api/search/text", {"text": 12}),
            ("/api/search/voice", {"audio_input": []}),
            ("/api/search/image", {"image_vector": [1, 2]}),
        ):
            status, _, _ = self.request(path, body)
            self.assertEqual(status, 400, path)

    def test_order_access_fails_closed_without_configuration(self):
        self.server.RequestHandlerClass.admin_token = None
        try:
            status, _, content = self.request("/api/orders")
            self.assertEqual(status, 503)
            self.assertNotIn(b"C001", content)
        finally:
            self.server.RequestHandlerClass.admin_token = "test-only-admin-secret"


if __name__ == "__main__":
    unittest.main()
