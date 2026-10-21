"""Phase 8 outfit catalogue, generation contract, ownership and fallback checks."""

import base64
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


ROOT = Path(__file__).resolve().parent.parent


class OutfitPreviewHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"COGU_CATALOG_DB": str(Path(self.temporary.name, "catalog.sqlite3")),
            "COGU_OUTFIT_PROVIDER": "json", "COGU_OUTFIT_PROVIDER_URL": "", "COGU_OUTFIT_PROVIDER_MODEL": "", "COGU_OUTFIT_PROVIDER_API_KEY": ""})
        self.environment.start()
        self._start()

    def _start(self):
        self.server = create_web_server(port=0)
        self.server.RequestHandlerClass.log_message = lambda *args: None
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def _stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=5)

    def tearDown(self):
        self._stop(); self.environment.stop(); self.temporary.cleanup()

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
            with client["opener"].open(request, timeout=50) as response:
                status, result = response.status, json.load(response)
        except urllib.error.HTTPError as error:
            status, result = error.code, json.load(error)
        if "csrf_token" in result:
            client["csrf"] = result["csrf_token"]
        return status, result

    def catalogue(self, client):
        code, result = self.call(client, "GET", "/api/outfit/catalog")
        self.assertEqual(code, 200, result)
        return result

    def test_demo_samples_and_current_catalogue(self):
        guest = self.client()
        catalog = self.catalogue(guest)
        self.assertEqual(catalog["image_mode"], "demo")
        self.assertEqual(set(catalog["body_types"]), {"slim", "regular", "curvy", "tall", "petite"})
        self.assertEqual(catalog["genders"], {"male": "Nam", "female": "Nữ"})
        self.assertEqual(set(catalog["products"]), {"shirt", "trousers", "shoes"})
        selected = {category: catalog["products"][category][0]["id"] for category in catalog["products"]}
        for category, products in catalog["products"].items():
            self.assertTrue(products)
            self.assertTrue(all(item["category"] == category and item["stock"] > 0 for item in products))
        for body_type in ("slim", "regular", "curvy"):
            code, preview = self.call(guest, "POST", "/api/outfit/preview", {"body_type": body_type, "gender": "male", "products": {"shirt": selected["shirt"]}})
            self.assertEqual(code, 200, preview)
            self.assertEqual(preview["mode"], "demo")
            self.assertEqual(preview["image_url"], f"/images/outfit-sample-male-{body_type}.png")
            self.assertEqual(preview["gender"], "male")
            self.assertIn("không dùng sản phẩm đã chọn", preview["notice"])
            self.assertIn("không bảo đảm độ vừa vặn", preview["disclaimer"])
            self.assertEqual(preview["products"][0]["id"], selected["shirt"])
        self.assertEqual(self.call(guest, "POST", "/api/outfit/preview", {"body_type": "petite", "gender": "male", "products": {"shirt": selected["shirt"]}})[0], 429)
        customer = self.client()
        self.assertEqual(self.call(customer, "POST", "/api/auth/register", {"email": "all-types@phase8.test", "name": "Studio User", "password": "StrongPassword123!"})[0], 201)
        for body_type in ("tall", "petite"):
            code, preview = self.call(customer, "POST", "/api/outfit/preview", {"body_type": body_type, "gender": "female", "products": {"shirt": selected["shirt"]}})
            self.assertEqual(code, 200, preview)
            self.assertEqual(preview["image_url"], f"/images/outfit-sample-female-{body_type}.png")
        for gender in catalog["genders"]:
            for body_type in catalog["body_types"]:
                path = f"/images/outfit-sample-{gender}-{body_type}.png"
                with guest["opener"].open(self.base + path, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.read(8).startswith(b"\x89PNG"))

    def test_categories_body_type_and_csrf_are_server_validated(self):
        guest, customer, second = self.client(), self.client(), self.client()
        catalog = self.catalogue(guest)
        shirt = catalog["products"]["shirt"][0]["id"]
        shoes = catalog["products"]["shoes"][0]["id"]
        invalid = [
            {"body_type": "unknown", "gender": "male", "products": {"shirt": shirt}},
            {"body_type": "regular", "gender": "unknown", "products": {"shirt": shirt}},
            {"body_type": "regular", "products": {"shirt": shirt}},
            {"body_type": "regular", "gender": "male", "products": {}},
            {"body_type": "regular", "gender": "male", "products": {"shirt": shoes}},
            {"body_type": "regular", "gender": "male", "products": {"shirt": 999999}},
            {"body_type": "regular", "gender": "male", "products": {"jacket": shirt}},
            {"body_type": "regular", "gender": "male", "products": {"shirt": True}},
        ]
        for body in invalid[:3]:
            code, _ = self.call(guest, "POST", "/api/outfit/preview", body)
            self.assertEqual(code, 400, body)
        self.assertEqual(self.call(customer, "POST", "/api/auth/register", {"email": "studio@phase8.test", "name": "Studio User", "password": "StrongPassword123!"})[0], 201)
        self.assertEqual(self.call(customer, "POST", "/api/outfit/preview", {"body_type": "regular", "gender": "male", "products": {"shoes": shoes}}, csrf=False)[0], 403)
        for body in invalid[3:6]:
            self.assertEqual(self.call(customer, "POST", "/api/outfit/preview", body)[0], 400, body)
        self.assertEqual(self.call(second, "POST", "/api/auth/register", {"email": "studio2@phase8.test", "name": "Studio User", "password": "StrongPassword123!"})[0], 201)
        for body in invalid[6:]:
            self.assertEqual(self.call(second, "POST", "/api/outfit/preview", body)[0], 400, body)
        code, result = self.call(second, "POST", "/api/outfit/preview", {"body_type": "regular", "gender": "female", "products": {"shoes": shoes}})
        self.assertEqual(code, 200, result)
        self.assertEqual(result["products"][0]["category"], "shoes")

    def test_configured_provider_receives_real_product_images_and_validates_output(self):
        class Provider(BaseHTTPRequestHandler):
            last = None
            auth = None
            valid = True
            def do_POST(self):
                Provider.last = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                Provider.auth = self.headers.get("Authorization")
                picture = (ROOT / "images" / "query_shoes.jpg").read_bytes() if Provider.valid else b"not-an-image"
                result = {"image_base64": base64.b64encode(picture).decode(), "mime_type": "image/jpeg"}
                raw = json.dumps(result).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def log_message(self, *_):
                pass
        provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        try:
            self._stop()
            with patch.dict(os.environ, {"COGU_OUTFIT_PROVIDER_URL": f"http://127.0.0.1:{provider.server_port}/generate",
                "COGU_OUTFIT_PROVIDER_MODEL": "local-test-image", "COGU_OUTFIT_PROVIDER_API_KEY": "test-only-secret"}):
                self._start()
                client = self.client(); catalog = self.catalogue(client)
                self.assertEqual(catalog["image_mode"], "provider")
                chosen = {category: catalog["products"][category][0]["id"] for category in catalog["products"]}
                code, result = self.call(client, "POST", "/api/outfit/preview", {"body_type": "curvy", "gender": "female", "products": chosen})
                self.assertEqual(code, 200, result)
                self.assertEqual(result["mode"], "provider")
                self.assertTrue(result["image_url"].startswith("data:image/jpeg;base64,"))
                self.assertEqual(Provider.last["model"], "local-test-image")
                self.assertEqual(Provider.auth, "Bearer test-only-secret")
                self.assertEqual(Provider.last["body_type"], "curvy")
                self.assertEqual(Provider.last["gender"], "female")
                self.assertEqual(len(Provider.last["reference_images"]), 3)
                for reference in Provider.last["reference_images"]:
                    product = next(item for item in result["products"] if item["id"] == reference["product_id"])
                    self.assertEqual(base64.b64decode(reference["image_base64"]), (ROOT / product["image"]).read_bytes())
                Provider.valid = False
                code, fallback = self.call(client, "POST", "/api/outfit/preview", {"body_type": "curvy", "gender": "female", "products": {"shirt": chosen["shirt"]}})
                self.assertEqual(code, 200, fallback)
                self.assertEqual(fallback["mode"], "demo")
                self.assertIn("không khả dụng", fallback["notice"])
        finally:
            provider.shutdown(); provider.server_close(); thread.join(timeout=5)

    def test_openai_images_edit_multipart_contract_with_local_server(self):
        class ImagesAPI(BaseHTTPRequestHandler):
            body = b""
            auth = None
            content_type = None
            def do_POST(self):
                ImagesAPI.body = self.rfile.read(int(self.headers["Content-Length"]))
                ImagesAPI.auth = self.headers.get("Authorization")
                ImagesAPI.content_type = self.headers.get("Content-Type")
                png = (ROOT / "images" / "outfit-sample-regular.png").read_bytes()
                result = json.dumps({"data": [{"b64_json": base64.b64encode(png).decode()}]}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(result))); self.end_headers(); self.wfile.write(result)
            def log_message(self, *_):
                pass
        provider = ThreadingHTTPServer(("127.0.0.1", 0), ImagesAPI)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        try:
            self._stop()
            with patch.dict(os.environ, {"COGU_OUTFIT_PROVIDER": "openai",
                "COGU_OUTFIT_PROVIDER_URL": f"http://127.0.0.1:{provider.server_port}/v1/images/edits",
                "COGU_OUTFIT_PROVIDER_MODEL": "", "COGU_OUTFIT_PROVIDER_API_KEY": "", "OPENAI_API_KEY": "local-test-key"}):
                self._start()
                client = self.client(); catalog = self.catalogue(client)
                selected = {category: catalog["products"][category][0]["id"] for category in catalog["products"]}
                code, result = self.call(client, "POST", "/api/outfit/preview", {"body_type": "tall", "gender": "male", "products": selected})
                self.assertEqual(code, 200, result)
                self.assertEqual(result["mode"], "provider")
                self.assertTrue(result["image_url"].startswith("data:image/png;base64,"))
                self.assertEqual(ImagesAPI.auth, "Bearer local-test-key")
                self.assertIn("multipart/form-data; boundary=", ImagesAPI.content_type)
                self.assertEqual(ImagesAPI.body.count(b'name="image[]"'), 3)
                self.assertIn(b"gpt-image-2.5-sunburst", ImagesAPI.body)
                self.assertIn("Tall".encode(), ImagesAPI.body)
        finally:
            provider.shutdown(); provider.server_close(); thread.join(timeout=5)

    def test_gemini_interactions_uses_reference_images_and_server_key(self):
        class GeminiAPI(BaseHTTPRequestHandler):
            payload = None
            key = None
            def do_POST(self):
                GeminiAPI.payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                GeminiAPI.key = self.headers.get("x-goog-api-key")
                jpeg = (ROOT / "images" / "query_shoes.jpg").read_bytes()
                result = {"status": "completed", "steps": [{"type": "model_output", "content": [
                    {"type": "image", "mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}]}]}
                raw = json.dumps(result).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def log_message(self, *_):
                pass
        provider = ThreadingHTTPServer(("127.0.0.1", 0), GeminiAPI)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        try:
            self._stop()
            with patch.dict(os.environ, {"COGU_OUTFIT_PROVIDER": "gemini",
                "COGU_OUTFIT_PROVIDER_URL": f"http://127.0.0.1:{provider.server_port}/v1beta/interactions",
                "COGU_OUTFIT_PROVIDER_MODEL": "", "COGU_OUTFIT_PROVIDER_API_KEY": "", "GEMINI_API_KEY": "local-test-key"}):
                self._start()
                client = self.client(); catalog = self.catalogue(client)
                self.assertEqual(catalog["image_mode"], "provider")
                selected = {category: catalog["products"][category][0]["id"] for category in catalog["products"]}
                code, result = self.call(client, "POST", "/api/outfit/preview", {"body_type": "regular", "gender": "female", "products": selected})
                self.assertEqual(code, 200, result)
                self.assertEqual(result["mode"], "provider")
                self.assertEqual(result["gender"], "female")
                self.assertTrue(result["image_url"].startswith("data:image/jpeg;base64,"))
                self.assertEqual(GeminiAPI.key, "local-test-key")
                self.assertEqual(GeminiAPI.payload["model"], "gemini-nano-banana-2.1")
                self.assertEqual(GeminiAPI.payload["response_format"]["type"], "image")
                self.assertEqual(GeminiAPI.payload["response_format"]["mime_type"], "image/jpeg")
                self.assertIn("adult woman", GeminiAPI.payload["input"][0]["text"])
                self.assertEqual(len(GeminiAPI.payload["input"]), 4)
                for part, product in zip(GeminiAPI.payload["input"][1:], result["products"]):
                    self.assertEqual(part["type"], "image")
                    self.assertEqual(base64.b64decode(part["data"]), (ROOT / product["image"]).read_bytes())
        finally:
            provider.shutdown(); provider.server_close(); thread.join(timeout=5)

    def test_cloudflare_free_tier_provider_uses_descriptions_and_labels_output(self):
        class CloudflareAPI(BaseHTTPRequestHandler):
            payload = None
            auth = None
            response_status = 200
            def do_POST(self):
                CloudflareAPI.payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                CloudflareAPI.auth = self.headers.get("Authorization")
                jpeg = (ROOT / "images" / "query_shoes.jpg").read_bytes()
                raw = json.dumps({"success": True, "result": {"image": base64.b64encode(jpeg).decode()}}).encode()
                self.send_response(CloudflareAPI.response_status); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def log_message(self, *_):
                pass
        provider = ThreadingHTTPServer(("127.0.0.1", 0), CloudflareAPI)
        thread = threading.Thread(target=provider.serve_forever, daemon=True); thread.start()
        try:
            self._stop()
            with patch.dict(os.environ, {"COGU_OUTFIT_PROVIDER": "cloudflare",
                "COGU_OUTFIT_PROVIDER_URL": f"http://127.0.0.1:{provider.server_port}/ai/run/flux-1-schnell",
                "COGU_OUTFIT_PROVIDER_MODEL": "", "COGU_OUTFIT_PROVIDER_API_KEY": "",
                "CLOUDFLARE_API_TOKEN": "local-test-token"}):
                self._start()
                client = self.client(); catalog = self.catalogue(client)
                self.assertEqual(catalog["image_mode"], "provider")
                self.assertFalse(catalog["uses_product_photos"])
                self.assertNotIn("local-test-token", json.dumps(catalog))
                chosen = {category: catalog["products"][category][0]["id"] for category in catalog["products"]}
                code, result = self.call(client, "POST", "/api/outfit/preview",
                    {"body_type": "regular", "gender": "female", "products": chosen})
                self.assertEqual(code, 200, result)
                self.assertEqual(result["mode"], "provider")
                self.assertIn("MÔ TẢ SẢN PHẨM", result["label"])
                self.assertIn("không dùng ảnh sản phẩm", result["notice"])
                self.assertTrue(result["image_url"].startswith("data:image/jpeg;base64,"))
                self.assertEqual(CloudflareAPI.auth, "Bearer local-test-token")
                self.assertEqual(CloudflareAPI.payload["steps"], 8)
                self.assertIn("Exactly ONE person", CloudflareAPI.payload["prompt"])
                self.assertIn("no product photos are supplied", CloudflareAPI.payload["prompt"])
                self.assertNotIn("reference_images", CloudflareAPI.payload)
                for status, message in ((429, "hết hạn mức"), (403, "xác thực")):
                    CloudflareAPI.response_status = status
                    code, fallback = self.call(client, "POST", "/api/outfit/preview",
                        {"body_type": "regular", "gender": "female", "products": chosen})
                    self.assertEqual(code, 200, fallback)
                    self.assertEqual(fallback["mode"], "demo")
                    self.assertIn(message, fallback["notice"])
                    self.assertNotIn("local-test-token", json.dumps(fallback))
        finally:
            provider.shutdown(); provider.server_close(); thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
