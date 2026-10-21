"""Phase 7 HTTP checks: grounded answers, account scope, comparison and fallback."""

import http.cookiejar
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from presentation.web_server import create_web_server


class ShoppingAITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temporary.name, "store.sqlite3"))
        self.environment = patch.dict(os.environ, {"COGU_CATALOG_DB": self.db, "COGU_LLM_URL": "", "COGU_LLM_MODEL": "", "COGU_LLM_API_KEY": ""})
        self.environment.start()
        self._start()

    def _start(self):
        self.server = create_web_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def _stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def tearDown(self):
        self._stop()
        self.environment.stop()
        self.temporary.cleanup()

    @staticmethod
    def client():
        return {"opener": urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())), "csrf": ""}

    def call(self, client, method, path, body=None, csrf=True):
        headers = {"Content-Type": "application/json"}
        if method != "GET" and csrf and client["csrf"]:
            headers["X-CSRF-Token"] = client["csrf"]
        request = urllib.request.Request(self.base + path, method=method, headers=headers,
            data=json.dumps(body or {}, ensure_ascii=False).encode("utf-8") if method != "GET" else None)
        try:
            with client["opener"].open(request, timeout=10) as response:
                return response.status, self._parse(client, response)
        except urllib.error.HTTPError as error:
            return error.code, self._parse(client, error)

    @staticmethod
    def _parse(client, response):
        data = json.load(response)
        if "csrf_token" in data:
            client["csrf"] = data["csrf_token"]
        return data

    def register(self, client, email):
        code, data = self.call(client, "POST", "/api/auth/register", {"email": email, "name": "COGU Tester", "password": "StrongPassword123!"})
        self.assertEqual(code, 201, data)

    def test_preferences_and_recommendations_persist_per_customer(self):
        alice, bob = self.client(), self.client()
        self.register(alice, "alice@phase7.test")
        self.register(bob, "bob@phase7.test")
        self.assertEqual(self.call(self.client(), "GET", "/api/ai/preferences")[0], 401)
        _, facets = self.call(alice, "GET", "/api/ai/preferences")
        color = facets["colors"][0]
        payload = {"style": "toi_gian", "colors": [color], "budget_vnd": 1000000}
        self.assertEqual(self.call(alice, "PUT", "/api/ai/preferences", payload, csrf=False)[0], 403)
        self.assertEqual(self.call(alice, "PUT", "/api/ai/preferences", {**payload, "colors": ["made-up"]})[0], 400)
        self.assertEqual(self.call(alice, "PUT", "/api/ai/preferences", {**payload, "style": []})[0], 400)
        self.assertEqual(self.call(alice, "PUT", "/api/ai/preferences", payload)[0], 200)
        _, recommendations = self.call(alice, "GET", "/api/ai/recommendations")
        self.assertEqual(recommendations["mode"], "demo")
        self.assertTrue(recommendations["recommendations"])
        for item in recommendations["recommendations"]:
            self.assertLessEqual(item["product"]["price_vnd"], payload["budget_vnd"])
            self.assertGreater(item["product"]["stock"], 0)
            self.assertIn(str(item["product"]["price_vnd"]), item["explanation"])
        self.assertEqual(self.call(bob, "GET", "/api/ai/preferences")[1]["preferences"]["style"], "")
        self._stop(); self._start()
        self.assertEqual(self.call(alice, "GET", "/api/ai/preferences")[1]["preferences"], payload)

    def test_comparison_is_live_and_validated(self):
        guest = self.client()
        _, catalog = self.call(guest, "GET", "/api/catalog/products?page_size=3")
        ids = [product["id"] for product in catalog["products"][:3]]
        self.assertEqual(self.call(guest, "POST", "/api/ai/compare", {"product_ids": [ids[0], ids[0]]})[0], 400)
        self.assertEqual(self.call(guest, "POST", "/api/ai/compare", {"product_ids": [ids[0], 999999]})[0], 400)
        code, result = self.call(guest, "POST", "/api/ai/compare", {"product_ids": ids})
        self.assertEqual(code, 200, result)
        self.assertEqual(result["mode"], "demo")
        self.assertEqual([item["id"] for item in result["products"]], ids)
        self.assertTrue(result["analysis"])
        for product in result["products"]:
            _, detail = self.call(guest, "GET", "/api/catalog/products/" + product["slug"])
            self.assertEqual(product["stock"], sum(variant["stock"] for variant in detail["product"]["variants"]))
            self.assertEqual(product["available_variants"], [
                {"color": variant["color"], "size": variant["size"], "stock": variant["stock"]}
                for variant in detail["product"]["variants"] if variant["stock"] > 0])

    def test_chat_order_scope_and_rate_limit(self):
        alice, bob, guest = self.client(), self.client(), self.client()
        self.register(alice, "order-alice@phase7.test")
        self.register(bob, "order-bob@phase7.test")
        _, product = self.call(alice, "GET", "/api/catalog/products?page_size=1")
        _, detail = self.call(alice, "GET", "/api/catalog/products/" + product["products"][0]["slug"])
        variant = next(item for item in detail["product"]["variants"] if item["stock"])
        _, address = self.call(alice, "POST", "/api/account/addresses", {"recipient": "Khách COGU", "phone": "0901234567", "line1": "12 Nguyễn Huệ", "ward": "Bến Nghé", "district": "Quận 1", "city": "TP HCM", "note": "", "is_default": True})
        self.assertEqual(self.call(alice, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": 1})[0], 200)
        _, checkout = self.call(alice, "POST", "/api/checkout", {"address_id": address["address"]["id"], "payment_method": "cod", "idempotency_key": "phase7-order-123456"})
        reference = checkout["order"]["reference"]
        for client in (bob, guest):
            code, answer = self.call(client, "POST", "/api/ai/chat", {"message": "Đơn hàng của tôi thế nào?"})
            self.assertEqual(code, 200, answer)
            self.assertNotIn(reference, answer["answer"])
        code, answer = self.call(alice, "POST", "/api/ai/chat", {"message": "Đơn hàng của tôi thế nào?"})
        self.assertEqual(code, 200, answer)
        self.assertIn(reference, answer["answer"])
        self.assertEqual(answer["mode"], "demo")
        self.assertEqual(self.call(alice, "POST", "/api/ai/chat", {"message": "Đơn hàng của tôi"}, csrf=False)[0], 403)
        for _ in range(19):
            self.assertEqual(self.call(alice, "POST", "/api/ai/chat", {"message": "size áo"})[0], 200)
        self.assertEqual(self.call(alice, "POST", "/api/ai/chat", {"message": "size áo"})[0], 429)

    def test_configured_provider_can_select_only_known_evidence(self):
        class Provider(BaseHTTPRequestHandler):
            selected = "size"
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                request = json.loads(self.rfile.read(length))
                assert request["model"] == "local-test-model"
                content = json.dumps({"ids": [self.selected]})
                body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *_):
                pass
        provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        try:
            self._stop()
            with patch.dict(os.environ, {"COGU_LLM_URL": f"http://127.0.0.1:{provider.server_port}/v1/chat/completions", "COGU_LLM_MODEL": "local-test-model", "COGU_LLM_API_KEY": "local-test-key"}):
                self._start()
                guest = self.client()
                code, answer = self.call(guest, "POST", "/api/ai/chat", {"message": "Bảng size thế nào?"})
                self.assertEqual(code, 200, answer)
                self.assertEqual(answer["mode"], "provider")
                self.assertIn("tồn kho", answer["answer"])
                Provider.selected = "invented-fact"
                code, fallback = self.call(guest, "POST", "/api/ai/chat", {"message": "Bảng size thế nào?"})
                self.assertEqual(code, 200, fallback)
                self.assertEqual(fallback["mode"], "demo")
                self.assertNotIn("invented-fact", fallback["answer"])
        finally:
            provider.shutdown(); provider.server_close(); thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
