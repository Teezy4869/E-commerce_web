"""End-to-end HTTP regression for account, exact-variant cart and COD checkout."""

import http.cookiejar
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from presentation.web_server import create_web_server


class CommerceHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temporary.name, "shop.sqlite3"))
        self.environment = patch.dict(os.environ, {"COGU_CATALOG_DB": self.database})
        self.environment.start()
        self._start_server()

    def _start_server(self):
        self.server = create_web_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def tearDown(self):
        self._stop_server()
        self.environment.stop()
        self.temporary.cleanup()

    def client(self):
        return {"opener": urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())), "csrf": ""}

    def call(self, client, method, path, body=None, csrf=True):
        headers = {"Accept": "application/json"}
        if method != "GET":
            headers["Content-Type"] = "application/json"
            if csrf and client["csrf"]:
                headers["X-CSRF-Token"] = client["csrf"]
        request = urllib.request.Request(self.base + path,
            data=json.dumps(body or {}).encode("utf-8") if method != "GET" else None,
            headers=headers, method=method)
        try:
            with client["opener"].open(request, timeout=8) as response:
                status, payload = response.status, json.load(response)
        except urllib.error.HTTPError as error:
            status, payload = error.code, json.load(error)
        if "csrf_token" in payload:
            client["csrf"] = payload["csrf_token"]
        return status, payload

    def register(self, client, email):
        status, result = self.call(client, "POST", "/api/auth/register", {"email": email, "name": "Khách COGU", "password": "VerySecure123!"})
        self.assertEqual(status, 201, result)
        return result

    def test_complete_cod_journey_persists_and_is_customer_scoped(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        self.assertEqual(self.call(anonymous, "GET", "/api/account/orders")[0], 401)
        self.register(alice, "alice@example.test")
        self.register(bob, "bob@example.test")
        status, address = self.call(alice, "POST", "/api/account/addresses", {
            "recipient": "Nguyễn An", "phone": "0901234567", "line1": "12 Nguyễn Huệ",
            "ward": "Bến Nghé", "district": "Quận 1", "city": "TP HCM", "note": "", "is_default": True})
        self.assertEqual(status, 201, address)
        address_id = address["address"]["id"]
        self.assertEqual(self.call(bob, "PUT", f"/api/account/addresses/{address_id}", {
            "recipient": "Nguyễn An", "phone": "0901234567", "line1": "12 Nguyễn Huệ",
            "ward": "Bến Nghé", "district": "Quận 1", "city": "TP HCM", "note": "", "is_default": True})[0], 404)

        _, catalog = self.call(alice, "GET", "/api/catalog/products?page_size=1")
        product = catalog["products"][0]
        _, detail = self.call(alice, "GET", f"/api/catalog/products/{product['slug']}")
        variants = [item for item in detail["product"]["variants"] if item["stock"] >= 2]
        self.assertTrue(variants)
        variant = variants[0]
        initial_stock = variant["stock"]
        self.assertEqual(self.call(alice, "POST", "/api/account/wishlist", {"product_id": product["id"]})[0], 200)
        self.assertEqual(self.call(alice, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": 1}, csrf=False)[0], 403)
        self.assertEqual(self.call(alice, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": 1})[0], 200)
        self.assertEqual(self.call(alice, "PUT", "/api/cart", {"variant_id": variant["id"], "quantity": 2})[0], 200)
        _, quote = self.call(alice, "GET", "/api/cart?promotion_code=COGU10")
        cart = quote["cart"]
        self.assertEqual(cart["items"][0]["variant_id"], variant["id"])
        self.assertEqual(cart["items"][0]["quantity"], 2)
        self.assertEqual(cart["subtotal_vnd"], product["price_vnd"] * 2)
        self.assertEqual(cart["discount_vnd"], min(cart["subtotal_vnd"] // 10, 100000))
        self.assertEqual(cart["total_vnd"], cart["subtotal_vnd"] - cart["discount_vnd"] + cart["delivery_fee_vnd"])
        self.assertEqual(self.call(alice, "POST", "/api/checkout", {"address_id": address_id, "payment_method": "card", "idempotency_key": "checkout-request-abc-123"})[0], 400)
        checkout_body = {"address_id": address_id, "payment_method": "cod", "promotion_code": "COGU10", "idempotency_key": "checkout-request-abc-123", "total_vnd": 1}
        status, placed = self.call(alice, "POST", "/api/checkout", checkout_body)
        self.assertEqual(status, 201, placed)
        order = placed["order"]
        self.assertTrue(order["reference"].startswith("COGU-"))
        self.assertEqual((order["order_status"], order["payment_status"], order["shipment_status"]), ("confirmed", "pending_cod", "pending"))
        self.assertEqual(order["total_vnd"], cart["total_vnd"])
        self.assertEqual(order["items"][0]["variant_id"], variant["id"])
        self.assertEqual(self.call(alice, "GET", "/api/cart")[1]["cart"]["items"], [])
        _, after = self.call(alice, "GET", f"/api/catalog/products/{product['slug']}")
        self.assertEqual(next(item for item in after["product"]["variants"] if item["id"] == variant["id"])["stock"], initial_stock - 2)
        status, duplicate = self.call(alice, "POST", "/api/checkout", checkout_body)
        self.assertEqual(status, 200)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["order"]["reference"], order["reference"])
        self.assertEqual(self.call(alice, "POST", "/api/checkout", {**checkout_body, "promotion_code": "FREESHIP"})[0], 409)
        self.assertEqual(self.call(bob, "GET", f"/api/account/orders/{order['reference']}")[0], 404)
        self.assertEqual(self.call(bob, "GET", "/api/account/orders")[1]["orders"], [])
        _, after_retry = self.call(alice, "GET", f"/api/catalog/products/{product['slug']}")
        self.assertEqual(next(item for item in after_retry["product"]["variants"] if item["id"] == variant["id"])["stock"], initial_stock - 2)

        self._stop_server()
        self._start_server()
        status, history = self.call(alice, "GET", "/api/account/orders")
        self.assertEqual(status, 200)
        self.assertEqual([item["reference"] for item in history["orders"]], [order["reference"]])
        self.assertEqual(self.call(alice, "GET", f"/api/account/orders/{order['reference']}")[1]["order"]["total_vnd"], cart["total_vnd"])

    def test_stock_validation_and_authentication(self):
        user = self.client()
        self.register(user, "stock@example.test")
        _, product = self.call(user, "GET", "/api/catalog/products?page_size=1")
        slug = product["products"][0]["slug"]
        _, detail = self.call(user, "GET", f"/api/catalog/products/{slug}")
        variant = detail["product"]["variants"][0]
        other = next(item for item in detail["product"]["variants"] if item["id"] != variant["id"] and item["stock"] > 0)
        self.assertEqual(self.call(user, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": 11})[0], 400)
        self.assertEqual(self.call(user, "POST", "/api/cart", {"variant_id": 999999, "quantity": 1})[0], 404)
        self.assertEqual(self.call(user, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": min(10, variant["stock"] + 1)})[0], 409 if variant["stock"] < 10 else 200)
        self.assertEqual(self.call(user, "POST", "/api/cart", {"variant_id": other["id"], "quantity": 1})[0], 200)
        _, cart = self.call(user, "GET", "/api/cart")
        self.assertIn(other["id"], [item["variant_id"] for item in cart["cart"]["items"]])
        self.assertNotEqual(other["id"], variant["id"])
        status, updated = self.call(user, "PUT", "/api/account/profile", {"name": "Khách đã sửa", "phone": "0901234567"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["customer"]["name"], "Khách đã sửa")
        self.assertEqual(self.call(user, "POST", "/api/auth/logout")[0], 200)
        self.assertEqual(self.call(user, "GET", "/api/auth/me")[0], 401)
        self.assertEqual(self.call(user, "POST", "/api/auth/login", {"email": "stock@example.test", "password": "incorrect"})[0], 401)
        self.assertEqual(self.call(user, "POST", "/api/auth/login", {"email": "stock@example.test", "password": "VerySecure123!"})[0], 200)
        self.assertEqual(self.call(user, "GET", "/api/auth/me")[1]["customer"]["name"], "Khách đã sửa")
        self.assertIn(other["id"], [item["variant_id"] for item in self.call(user, "GET", "/api/cart")[1]["cart"]["items"]])


if __name__ == "__main__":
    unittest.main()
