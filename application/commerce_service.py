"""Customer identity, cart pricing and COD checkout use cases."""

import hashlib
import hmac
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from data.commerce_repository import CommerceError


class CommerceService:
    SESSION_SECONDS = 7 * 24 * 60 * 60
    EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    PHONE = re.compile(r"^(?:0\d{9}|\+84\d{9})$")

    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _string(value, label, minimum=1, maximum=120):
        if not isinstance(value, str):
            raise CommerceError(f"{label} không hợp lệ.")
        clean = value.strip()
        if not minimum <= len(clean) <= maximum:
            raise CommerceError(f"{label} phải dài từ {minimum} đến {maximum} ký tự.")
        return clean

    @staticmethod
    def _integer(value, label, low=1, high=2**31 - 1):
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise CommerceError(f"{label} không hợp lệ.")
        return value

    @classmethod
    def _phone(cls, value, optional=False):
        phone = cls._string(value, "Số điện thoại", 0 if optional else 10, 12).replace(" ", "")
        if phone or not optional:
            if not cls.PHONE.fullmatch(phone):
                raise CommerceError("Số điện thoại phải có 10 chữ số hoặc dạng +84.")
        return phone

    @staticmethod
    def _hash_password(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 310000).hex()

    @staticmethod
    def _token_hash(token):
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def _new_session(self, customer):
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        self.repository.create_session(self._token_hash(token), customer["id"], csrf,
                                       int(time.time()) + self.SESSION_SECONDS)
        return token, {"customer": customer, "csrf_token": csrf}

    def register(self, body):
        email = self._string(body.get("email"), "Email", 5, 254).lower()
        if not self.EMAIL.fullmatch(email):
            raise CommerceError("Email không hợp lệ.")
        name = self._string(body.get("name"), "Họ tên", 2, 80)
        password = body.get("password")
        if not isinstance(password, str) or not 10 <= len(password) <= 128:
            raise CommerceError("Mật khẩu cần từ 10 đến 128 ký tự.")
        salt = secrets.token_hex(16)
        customer = self.repository.create_customer(email, self._hash_password(password, salt), salt, name)
        return self._new_session(customer)

    def login(self, body):
        email = self._string(body.get("email"), "Email", 5, 254).lower()
        password = body.get("password")
        if not isinstance(password, str):
            raise CommerceError("Thông tin đăng nhập không đúng.", 401)
        row = self.repository.find_customer_by_email(email)
        if not row or not hmac.compare_digest(self._hash_password(password, row["password_salt"]), row["password_hash"]):
            raise CommerceError("Thông tin đăng nhập không đúng.", 401)
        customer = self.repository.get_customer(row["id"])
        return self._new_session(customer)

    def session(self, token):
        if not token or len(token) > 200:
            return None
        try:
            return self.repository.get_session(self._token_hash(token))
        except UnicodeEncodeError:
            return None

    @staticmethod
    def public_session(session):
        return {"customer": {"id": session["customer_id"], "email": session["email"],
                             "name": session["name"], "phone": session["phone"],
                             "created_at": session["created_at"]}, "csrf_token": session["csrf_token"]}

    @staticmethod
    def require_csrf(session, supplied):
        if not supplied or not hmac.compare_digest(supplied, session["csrf_token"]):
            raise CommerceError("Phiên bảo mật không hợp lệ. Hãy tải lại trang.", 403)

    def logout(self, token):
        if token:
            self.repository.delete_session(self._token_hash(token))

    def update_profile(self, customer_id, body):
        name = self._string(body.get("name"), "Họ tên", 2, 80)
        phone = self._phone(body.get("phone", ""), optional=True)
        return self.repository.update_customer(customer_id, name, phone)

    def save_address(self, customer_id, body, address_id=None):
        fields = {name: self._string(body.get(name), label, minimum, maximum) for name, label, minimum, maximum in (
            ("recipient", "Tên người nhận", 2, 80), ("line1", "Địa chỉ", 5, 160),
            ("ward", "Phường/xã", 2, 80), ("district", "Quận/huyện", 2, 80),
            ("city", "Tỉnh/thành phố", 2, 80))}
        fields["phone"] = self._phone(body.get("phone"))
        fields["note"] = self._string(body.get("note", ""), "Ghi chú", 0, 240)
        default = body.get("is_default", False)
        if not isinstance(default, bool):
            raise CommerceError("is_default phải là true hoặc false.")
        fields["is_default"] = default
        return self.repository.save_address(customer_id, fields, address_id)

    def set_wishlist(self, customer_id, body, wanted):
        product_id = self._integer(body.get("product_id"), "Mã sản phẩm")
        self.repository.set_wishlist(customer_id, product_id, wanted)
        return self.repository.list_wishlist(customer_id)

    def add_cart(self, customer_id, body):
        variant_id = self._integer(body.get("variant_id"), "Mã phiên bản")
        quantity = self._integer(body.get("quantity", 1), "Số lượng", 1, 10)
        self.repository.change_cart(customer_id, variant_id, quantity, add=True)
        return self.cart(customer_id)

    def set_cart(self, customer_id, body):
        variant_id = self._integer(body.get("variant_id"), "Mã phiên bản")
        quantity = self._integer(body.get("quantity"), "Số lượng", 0, 10)
        self.repository.change_cart(customer_id, variant_id, quantity)
        return self.cart(customer_id)

    def _promotion(self, code, promotion=None, subtotal=0):
        if not code:
            return None
        promotion = promotion if promotion is not None else self.repository.get_promotion(code)
        if not promotion or not promotion["active"]:
            raise CommerceError("Mã ưu đãi không hợp lệ hoặc đã ngừng áp dụng.")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if ((promotion["starts_at"] and now < promotion["starts_at"]) or
                (promotion["ends_at"] and now > promotion["ends_at"]) or
                (promotion["usage_limit"] is not None and promotion["used_count"] >= promotion["usage_limit"])):
            raise CommerceError("Mã ưu đãi đã hết hạn hoặc hết lượt sử dụng.")
        if subtotal < promotion["min_subtotal_vnd"]:
            raise CommerceError("Giỏ hàng chưa đạt mức tối thiểu của mã ưu đãi.")
        return promotion

    def calculate(self, items, promotion_code, promotion=None):
        code = promotion_code
        subtotal = sum(item["price_vnd"] * item["quantity"] for item in items)
        promo = self._promotion(code, promotion, subtotal)
        discount = 0
        if promo and promo["kind"] == "percent":
            discount = subtotal * promo["value"] // 100
            if promo["max_discount_vnd"]:
                discount = min(discount, promo["max_discount_vnd"])
        elif promo and promo["kind"] == "amount":
            discount = min(subtotal, promo["value"])
        delivery = 0 if not items or (promo and promo["kind"] == "free_shipping") or subtotal - discount >= 1500000 else 30000
        return {"subtotal_vnd": subtotal, "discount_vnd": discount,
                "delivery_fee_vnd": delivery, "total_vnd": subtotal - discount + delivery,
                "promotion_code": code,
                "promotion_description": promo["description"] if promo else ""}

    def cart(self, customer_id, promotion_code=""):
        items = self.repository.cart(customer_id)
        totals = self.calculate(items, promotion_code)
        for item in items:
            item["line_total_vnd"] = item["price_vnd"] * item["quantity"]
            item["available"] = item["stock"] >= item["quantity"]
        return {"items": items, **totals, "can_checkout": bool(items) and all(item["available"] for item in items),
                "payment_methods": ["cod"], "delivery_policy": "30.000 ₫; miễn phí từ 1.500.000 ₫ sau giảm giá"}

    def checkout(self, customer_id, body):
        address_id = self._integer(body.get("address_id"), "Địa chỉ giao hàng")
        method = body.get("payment_method")
        if method != "cod":
            raise CommerceError("Hiện chỉ hỗ trợ thanh toán khi nhận hàng (COD).")
        code = self._string(body.get("promotion_code", ""), "Mã ưu đãi", 0, 20).upper()
        key = self._string(body.get("idempotency_key"), "Mã xác nhận", 16, 128)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise CommerceError("Mã xác nhận không hợp lệ.")
        fingerprint = hashlib.sha256(f"{address_id}|cod|{code}".encode("utf-8")).hexdigest()
        reference = "COGU-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:12].upper()
        return self.repository.checkout(customer_id, address_id, key, fingerprint, code, self.calculate, reference)
