"""Admin role, operations and customer-facing persistence checks through HTTP."""

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


PASSWORD = "DemoPassword123!"
ROLES = ("administrator", "manager", "sales", "warehouse", "support")


class AdminHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temporary.name, "admin.sqlite3"))
        self.environment = patch.dict(os.environ, {"COGU_CATALOG_DB": self.database})
        self.environment.start()
        self.start_server()
        for role in ROLES:
            self.server.RequestHandlerClass.admin_service.seed_staff(f"{role}@cogu.test", role.title(), role, PASSWORD)

    def start_server(self):
        self.server = create_web_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def tearDown(self):
        self.stop_server()
        self.environment.stop()
        self.temporary.cleanup()

    @staticmethod
    def client():
        return {"opener": urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())),
                "csrf": ""}

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
            with client["opener"].open(request, timeout=10) as response:
                status, payload = response.status, json.load(response)
        except urllib.error.HTTPError as error:
            status, payload = error.code, json.load(error)
        if "csrf_token" in payload:
            client["csrf"] = payload["csrf_token"]
        return status, payload

    def staff(self, role):
        client = self.client()
        status, payload = self.call(client, "POST", "/api/admin/login", {"email": f"{role}@cogu.test", "password": PASSWORD})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["staff"]["role"], role)
        return client

    def customer(self, email="customer@cogu.test"):
        client = self.client()
        status, payload = self.call(client, "POST", "/api/auth/register", {"email": email, "name": "COGU Customer", "password": PASSWORD})
        self.assertEqual(status, 201, payload)
        return client

    def test_role_boundaries_and_catalogue_promotion_operations(self):
        admin, manager, sales, warehouse, support = (self.staff(role) for role in ROLES)
        customer = self.customer()
        self.assertEqual(self.call(customer, "GET", "/api/admin/dashboard")[0], 401)
        self.assertEqual(self.call(customer, "POST", "/api/admin/products", {})[0], 401)
        self.assertEqual(self.call(support, "GET", "/api/admin/dashboard")[0], 403)
        self.assertEqual(self.call(support, "GET", "/api/admin/support")[0], 200)
        self.assertEqual(self.call(warehouse, "GET", "/api/admin/products")[0], 200)
        self.assertEqual(self.call(warehouse, "POST", "/api/admin/promotions", {})[0], 403)
        self.assertEqual(self.call(sales, "POST", "/api/admin/products", {})[0], 403)
        self.assertEqual(self.call(manager, "GET", "/api/admin/staff")[0], 403)
        self.assertEqual(self.call(admin, "GET", "/api/admin/staff")[0], 200)

        product_body = {"slug": "ao-thu-nghiem-quan-tri", "name_vi": "Áo thử nghiệm quản trị",
                        "description_vi": "Áo cotton dùng để kiểm tra hoạt động cửa hàng.",
                        "category": "shirt", "material": "Cotton", "price_vnd": 320000,
                        "image": "images/catalog-17.png", "is_new": True, "is_bestseller": False}
        self.assertEqual(self.call(admin, "POST", "/api/admin/products", product_body, csrf=False)[0], 403)
        status, result = self.call(admin, "POST", "/api/admin/products", product_body)
        self.assertEqual(status, 201, result)
        product_id = result["product"]["id"]
        self.assertEqual(self.call(customer, "GET", "/api/catalog/products/ao-thu-nghiem-quan-tri")[0], 200)
        _, search = self.call(customer, "POST", "/api/search/text", {"text": "thử nghiệm quản trị"})
        self.assertIn(product_id, [item["product"]["id"] for item in search["results"]])
        variant_body = {"sku": "COGU-ADMIN-001", "color": "Xanh rừng", "size": "M", "stock": 2}
        status, variant = self.call(warehouse, "POST", f"/api/admin/products/{product_id}/variants", variant_body)
        self.assertEqual(status, 201, variant)
        variant_id = variant["variant"]["id"]
        self.assertEqual(self.call(sales, "PUT", f"/api/admin/variants/{variant_id}/stock", {"stock": 8, "note": "Nhập thêm hàng"})[0], 403)
        self.assertEqual(self.call(warehouse, "PUT", f"/api/admin/variants/{variant_id}/stock", {"stock": 8, "note": "Nhập thêm hàng"})[0], 200)
        _, detail = self.call(customer, "GET", "/api/catalog/products/ao-thu-nghiem-quan-tri")
        self.assertEqual(detail["product"]["variants"][0]["stock"], 8)
        product_body["price_vnd"] = 350000
        self.assertEqual(self.call(manager, "PUT", f"/api/admin/products/{product_id}", product_body)[0], 200)
        self.assertEqual(self.call(customer, "GET", "/api/catalog/products/ao-thu-nghiem-quan-tri")[1]["product"]["price_vnd"], 350000)

        promo = {"code": "ADMIN15", "kind": "percent", "value": 15,
                 "max_discount_vnd": 50000, "min_subtotal_vnd": 100000, "active": True,
                 "usage_limit": 1, "starts_at": None, "ends_at": None, "description": "Giảm thử nghiệm"}
        self.assertEqual(self.call(sales, "POST", "/api/admin/promotions", promo)[0], 201)
        self.assertEqual(self.call(customer, "POST", "/api/cart", {"variant_id": variant_id, "quantity": 1})[0], 200)
        _, quote = self.call(customer, "GET", "/api/cart?promotion_code=ADMIN15")
        self.assertEqual(quote["cart"]["discount_vnd"], 50000)
        self.assertEqual(self.call(sales, "PUT", "/api/admin/promotions/ADMIN15", {**promo, "active": False})[0], 200)
        self.assertEqual(self.call(customer, "GET", "/api/cart?promotion_code=ADMIN15")[0], 400)
        self.assertEqual(self.call(sales, "PUT", "/api/admin/promotions/ADMIN15", promo)[0], 200)
        self.assertEqual(self.call(admin, "DELETE", f"/api/admin/products/{product_id}")[0], 200)
        self.assertEqual(self.call(customer, "GET", "/api/catalog/products/ao-thu-nghiem-quan-tri")[0], 404)
        self.assertEqual(self.call(customer, "GET", "/api/cart")[1]["cart"]["items"], [])

    def test_order_review_support_and_reports(self):
        admin, manager, sales, warehouse, support = (self.staff(role) for role in ROLES)
        customer = self.customer("buyer@cogu.test")
        _, address = self.call(customer, "POST", "/api/account/addresses", {"recipient": "Buyer", "phone": "0901234567",
            "line1": "12 Nguyen Hue", "ward": "Ben Nghe", "district": "Quan 1", "city": "TP HCM", "note": "", "is_default": True})
        address_id = address["address"]["id"]
        _, product = self.call(customer, "GET", "/api/catalog/products/ao-thun-oversize-essential")
        product_id = product["product"]["id"]
        variant = next(item for item in product["product"]["variants"] if item["stock"] >= 2)
        self.assertEqual(self.call(customer, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": 1})[0], 200)
        _, placed = self.call(customer, "POST", "/api/checkout", {"address_id": address_id, "payment_method": "cod",
            "promotion_code": "COGU10", "idempotency_key": "admin-order-test-123456"})
        ref = placed["order"]["reference"]
        self.assertEqual(self.call(customer, "GET", "/api/admin/orders")[0], 401)
        self.assertEqual(self.call(customer, "POST", "/api/account/reviews", {"product_id": product_id, "rating": 5, "comment": "Rất đẹp và vừa vặn."})[0], 403)
        self.assertEqual(self.call(support, "GET", "/api/admin/orders")[0], 200)
        self.assertEqual(self.call(support, "PUT", f"/api/admin/orders/{ref}/shipment", {"status": "packing", "note": "Đã bắt đầu đóng gói"})[0], 403)
        self.assertEqual(self.call(sales, "PUT", f"/api/admin/orders/{ref}/payment", {"status": "collected", "note": "Thu COD trực tiếp"})[0], 409)
        for state in ("packing", "shipped", "delivered"):
            status, result = self.call(warehouse, "PUT", f"/api/admin/orders/{ref}/shipment", {"status": state, "note": "Nhân viên cập nhật trạng thái", "tracking_reference": "INTERNAL-1"})
            self.assertEqual(status, 200, result)
        self.assertEqual(self.call(sales, "PUT", f"/api/admin/orders/{ref}/payment", {"status": "collected", "note": "Thu COD trực tiếp tại cửa"})[0], 200)
        self.assertEqual(self.call(sales, "PUT", f"/api/admin/orders/{ref}/status", {"status": "fulfilled", "note": "Đã đối soát đơn COD"})[0], 200)
        _, dashboard = self.call(manager, "GET", "/api/admin/dashboard")
        self.assertEqual(dashboard["dashboard"]["settled_revenue_vnd"], placed["order"]["total_vnd"])
        self.assertEqual(dashboard["dashboard"]["pending_cod_vnd"], 0)
        _, report = self.call(manager, "GET", "/api/admin/reports")
        self.assertEqual(report["reports"]["sales_by_day"][0]["settled_revenue_vnd"], placed["order"]["total_vnd"])
        self.assertEqual(self.call(customer, "GET", f"/api/account/orders/{ref}")[1]["order"]["payment_source"], "staff_recorded_cod")

        review_choices = self.call(customer, "GET", "/api/account/reviews")[1]["reviewable_products"]
        self.assertEqual([(item["id"], item["slug"]) for item in review_choices],
                         [(product_id, "ao-thun-oversize-essential")])

        status, review = self.call(customer, "POST", "/api/account/reviews", {"product_id": product_id, "rating": 5, "comment": "Rất đẹp và vừa vặn."})
        self.assertEqual(status, 201, review)
        self.assertEqual(review["review"]["status"], "pending")
        self.assertEqual(self.call(customer, "GET", "/api/account/reviews")[1]["reviewable_products"], [])
        self.assertEqual(self.call(customer, "GET", "/api/catalog/products/ao-thun-oversize-essential")[1]["reviews"], [])
        self.assertEqual(self.call(support, "PUT", f"/api/admin/reviews/{review['review']['id']}", {"status": "approved"})[0], 200)
        public_reviews = self.call(customer, "GET", "/api/catalog/products/ao-thun-oversize-essential")[1]["reviews"]
        self.assertEqual(public_reviews[0]["verified_purchase"], 1)
        self.assertEqual(self.call(customer, "POST", "/api/account/reviews", {"product_id": product_id, "rating": 4, "comment": "Lần nữa rất đẹp."})[0], 409)

        status, ticket = self.call(customer, "POST", "/api/account/support", {"subject": "Hỏi về đơn hàng", "message": "Tôi muốn hỏi về thời gian xử lý đơn."})
        self.assertEqual(status, 201, ticket)
        self.assertEqual(self.call(warehouse, "GET", "/api/admin/support")[0], 403)
        self.assertEqual(self.call(support, "PUT", f"/api/admin/support/{ticket['request']['id']}", {"status": "resolved", "response": "Đơn đã được xử lý trong hệ thống demo."})[0], 200)
        self.assertIn("Đơn đã được", self.call(customer, "GET", "/api/account/support")[1]["requests"][0]["response"])

        self.stop_server()
        self.start_server()
        self.assertEqual(self.call(customer, "GET", f"/api/account/orders/{ref}")[0], 200)
        self.assertEqual(self.call(customer, "GET", "/api/catalog/products/ao-thun-oversize-essential")[1]["reviews"][0]["rating"], 5)
        self.assertEqual(self.call(manager, "GET", "/api/admin/dashboard")[1]["dashboard"]["settled_revenue_vnd"], placed["order"]["total_vnd"])

    def test_cancel_restocks_and_staff_deactivation_revokes_access(self):
        admin, sales = self.staff("administrator"), self.staff("sales")
        customer = self.customer("cancel@cogu.test")
        _, address = self.call(customer, "POST", "/api/account/addresses", {"recipient": "Buyer", "phone": "0901234567",
            "line1": "12 Nguyen Hue", "ward": "Ben Nghe", "district": "Quan 1", "city": "TP HCM", "note": "", "is_default": True})
        _, product = self.call(customer, "GET", "/api/catalog/products/ao-thun-oversize-essential")
        variant = next(item for item in product["product"]["variants"] if item["stock"] >= 1)
        stock_before = variant["stock"]
        self.assertEqual(self.call(customer, "POST", "/api/cart", {"variant_id": variant["id"], "quantity": 1})[0], 200)
        _, placed = self.call(customer, "POST", "/api/checkout", {"address_id": address["address"]["id"],
            "payment_method": "cod", "promotion_code": "COGU10", "idempotency_key": "cancel-order-123456789"})
        ref = placed["order"]["reference"]
        self.assertEqual(self.call(sales, "PUT", f"/api/admin/orders/{ref}/status", {"status": "cancelled", "note": "Khách yêu cầu hủy đơn"})[0], 200)
        _, after = self.call(customer, "GET", "/api/catalog/products/ao-thun-oversize-essential")
        self.assertEqual(next(item for item in after["product"]["variants"] if item["id"] == variant["id"])["stock"], stock_before)
        _, history = self.call(customer, "GET", f"/api/account/orders/{ref}")
        self.assertEqual((history["order"]["order_status"], history["order"]["shipment_status"]), ("cancelled", "cancelled"))
        self.assertEqual(self.call(admin, "GET", "/api/admin/dashboard")[1]["dashboard"]["pending_cod_vnd"], 0)
        staff = self.call(admin, "GET", "/api/admin/staff")[1]["staff"]
        sales_id = next(item["id"] for item in staff if item["role"] == "sales")
        self.assertEqual(self.call(admin, "PUT", f"/api/admin/staff/{sales_id}", {"role": "sales", "active": False})[0], 200)
        self.assertEqual(self.call(sales, "GET", "/api/admin/orders")[0], 401)
        self.assertEqual(self.call(self.client(), "POST", "/api/admin/login", {"email": "sales@cogu.test", "password": PASSWORD})[0], 401)


if __name__ == "__main__":
    unittest.main()
