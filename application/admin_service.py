"""Staff authentication, permissions, validation and store operation use cases."""

import hmac
import re
import secrets
import time
from datetime import date
from pathlib import Path

from application.commerce_service import CommerceService
from data.catalog_models import CATALOG_CATEGORIES
from data.commerce_repository import CommerceError


class AdminService:
    SESSION_SECONDS = 12 * 60 * 60
    ROLES = {"administrator", "sales", "warehouse", "support", "manager"}
    PERMISSIONS = {
        "administrator": {"dashboard", "reports", "products.read", "products.write", "variants.write",
                          "orders.read", "orders.write", "payments.write", "shipments.write",
                          "promotions.read", "promotions.write", "reviews.read", "reviews.write",
                          "support.read", "support.write", "staff.read", "staff.write"},
        "manager": {"dashboard", "reports", "products.read", "products.write", "variants.write",
                    "orders.read", "orders.write", "payments.write", "shipments.write",
                    "promotions.read", "promotions.write", "reviews.read", "reviews.write",
                    "support.read", "support.write"},
        "sales": {"dashboard", "reports", "products.read", "orders.read", "orders.write",
                  "payments.write", "promotions.read", "promotions.write"},
        "warehouse": {"dashboard", "reports", "products.read", "variants.write",
                      "orders.read", "shipments.write"},
        "support": {"orders.read", "products.read", "reviews.read", "reviews.write",
                    "support.read", "support.write"},
    }
    CATEGORIES = CATALOG_CATEGORIES
    IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}

    def __init__(self, repository, images_dir):
        self.repository = repository
        self.images_dir = Path(images_dir).resolve()

    @staticmethod
    def _string(value, label, low=1, high=240):
        return CommerceService._string(value, label, low, high)

    @staticmethod
    def _integer(value, label, low=0, high=1000000000):
        return CommerceService._integer(value, label, low, high)

    @staticmethod
    def _bool(value, label):
        if not isinstance(value, bool):
            raise CommerceError(f"{label} phải là true hoặc false.")
        return value

    @classmethod
    def permissions(cls, role):
        return sorted(cls.PERMISSIONS.get(role, set()))

    @classmethod
    def require(cls, session, permission):
        if permission not in cls.PERMISSIONS.get(session["role"], set()):
            raise CommerceError("Vai trò nhân viên không có quyền thực hiện thao tác này.", 403)

    @staticmethod
    def _token_hash(token):
        return CommerceService._token_hash(token)

    def seed_staff(self, email, name, role, password):
        if role not in self.ROLES:
            raise CommerceError("Vai trò không hợp lệ.")
        if not CommerceService.EMAIL.fullmatch(email) or not 5 <= len(email) <= 254:
            raise CommerceError("Email không hợp lệ.")
        name = self._string(name, "Tên nhân viên", 2, 80)
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise CommerceError("Mật khẩu nhân viên cần từ 12 đến 128 ký tự.")
        salt = secrets.token_hex(16)
        return self.repository.create_staff(email.lower(), name, role,
            CommerceService._hash_password(password, salt), salt)

    def create_staff(self, session, body):
        self.require(session, "staff.write")
        email = self._string(body.get("email"), "Email", 5, 254).lower()
        if not CommerceService.EMAIL.fullmatch(email):
            raise CommerceError("Email không hợp lệ.")
        name = self._string(body.get("name"), "Tên nhân viên", 2, 80)
        role = body.get("role")
        if role not in self.ROLES:
            raise CommerceError("Vai trò không hợp lệ.")
        password = body.get("password")
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise CommerceError("Mật khẩu nhân viên cần từ 12 đến 128 ký tự.")
        salt = secrets.token_hex(16)
        return self.repository.create_staff(email, name, role,
            CommerceService._hash_password(password, salt), salt, session["staff_id"])

    def update_staff(self, session, staff_id, body):
        self.require(session, "staff.write")
        role = body.get("role")
        if role not in self.ROLES:
            raise CommerceError("Vai trò không hợp lệ.")
        active = self._bool(body.get("active"), "active")
        return self.repository.update_staff(session["staff_id"], staff_id, role, active)

    def login(self, body):
        email = self._string(body.get("email"), "Email", 5, 254).lower()
        password = body.get("password")
        row = self.repository.find_staff_by_email(email)
        if not isinstance(password, str) or not row or not row["active"] or not hmac.compare_digest(
                CommerceService._hash_password(password, row["password_salt"]), row["password_hash"]):
            raise CommerceError("Thông tin đăng nhập nhân viên không đúng.", 401)
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        self.repository.create_staff_session(self._token_hash(token), row["id"], csrf,
                                             int(time.time()) + self.SESSION_SECONDS)
        return token, {"staff": {"id": row["id"], "email": row["email"], "name": row["name"],
                                  "role": row["role"]}, "permissions": self.permissions(row["role"]), "csrf_token": csrf}

    def session(self, token):
        if not token or len(token) > 200:
            return None
        try:
            return self.repository.get_staff_session(self._token_hash(token))
        except UnicodeEncodeError:
            return None

    def public_session(self, session):
        return {"staff": {"id": session["staff_id"], "email": session["email"],
                          "name": session["name"], "role": session["role"]},
                "permissions": self.permissions(session["role"]), "csrf_token": session["csrf_token"]}

    @staticmethod
    def require_csrf(session, supplied):
        if not supplied or not hmac.compare_digest(supplied, session["csrf_token"]):
            raise CommerceError("Phiên bảo mật nhân viên không hợp lệ.", 403)

    def logout(self, token):
        if token:
            self.repository.delete_staff_session(self._token_hash(token))

    def _image(self, value):
        path = self._string(value, "Đường dẫn ảnh", 7, 180)
        if not re.fullmatch(r"images/[A-Za-z0-9._-]+", path) or Path(path).suffix.lower() not in self.IMAGE_TYPES:
            raise CommerceError("Ảnh phải là tệp hợp lệ trong thư mục images/.")
        resolved = (self.images_dir / path.removeprefix("images/")).resolve()
        if not resolved.is_relative_to(self.images_dir) or not resolved.is_file():
            raise CommerceError("Không tìm thấy ảnh trong thư mục images/.")
        return path

    def product_fields(self, body):
        slug = self._string(body.get("slug"), "Slug", 2, 100).lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise CommerceError("Slug chỉ dùng chữ thường, số và dấu gạch nối.")
        category = body.get("category")
        if category not in self.CATEGORIES:
            raise CommerceError("Danh mục không hợp lệ.")
        return {"slug": slug, "name_vi": self._string(body.get("name_vi"), "Tên sản phẩm", 3, 120),
                "description_vi": self._string(body.get("description_vi"), "Mô tả", 10, 1000),
                "category": category, "material": self._string(body.get("material"), "Chất liệu", 2, 120),
                "price_vnd": self._integer(body.get("price_vnd"), "Giá VND", 1000, 1000000000),
                "image": self._image(body.get("image")),
                "is_new": self._bool(body.get("is_new"), "is_new"),
                "is_bestseller": self._bool(body.get("is_bestseller"), "is_bestseller")}

    def variant_fields(self, body):
        sku = self._string(body.get("sku"), "SKU", 3, 64).upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]+", sku):
            raise CommerceError("SKU chỉ dùng chữ, số, gạch nối hoặc gạch dưới.")
        return {"sku": sku, "color": self._string(body.get("color"), "Màu", 2, 80),
                "size": self._string(body.get("size"), "Kích cỡ", 1, 20),
                "stock": self._integer(body.get("stock"), "Tồn kho", 0, 100000)}

    @staticmethod
    def _date(value, label):
        if value in (None, ""):
            return None
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise CommerceError(f"{label} phải có dạng YYYY-MM-DD.")
        try:
            date.fromisoformat(value)
        except ValueError:
            raise CommerceError(f"{label} không hợp lệ.") from None
        return value

    def promotion_fields(self, body, code=None):
        target = code or self._string(body.get("code"), "Mã ưu đãi", 3, 20).upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,20}", target):
            raise CommerceError("Mã ưu đãi chỉ dùng chữ in hoa, số, gạch nối hoặc gạch dưới.")
        kind = body.get("kind")
        if kind not in ("percent", "amount", "free_shipping"):
            raise CommerceError("Loại ưu đãi không hợp lệ.")
        value = self._integer(body.get("value"), "Giá trị ưu đãi", 0, 1000000000)
        if kind == "percent" and not 1 <= value <= 100:
            raise CommerceError("Phần trăm giảm phải từ 1 đến 100.")
        if kind == "amount" and value < 1000:
            raise CommerceError("Giảm tiền cố định phải từ 1.000 VND.")
        if kind == "free_shipping" and value != 0:
            raise CommerceError("Mã miễn phí giao hàng phải có giá trị 0.")
        starts = self._date(body.get("starts_at"), "Ngày bắt đầu")
        ends = self._date(body.get("ends_at"), "Ngày kết thúc")
        if starts and ends and starts > ends:
            raise CommerceError("Ngày kết thúc phải sau ngày bắt đầu.")
        limit = body.get("usage_limit")
        return {"code": target, "kind": kind, "value": value,
                "max_discount_vnd": self._integer(body.get("max_discount_vnd", 0), "Giảm tối đa", 0, 1000000000),
                "min_subtotal_vnd": self._integer(body.get("min_subtotal_vnd", 0), "Đơn tối thiểu", 0, 1000000000),
                "active": self._bool(body.get("active"), "active"),
                "usage_limit": None if limit in (None, "") else self._integer(limit, "Giới hạn lượt", 1, 1000000000),
                "starts_at": starts, "ends_at": ends,
                "description": self._string(body.get("description", ""), "Mô tả ưu đãi", 0, 240)}

    def order_change(self, session, reference, kind, body):
        permission = {"status": "orders.write", "shipment": "shipments.write", "payment": "payments.write"}[kind]
        self.require(session, permission)
        if not re.fullmatch(r"COGU-\d{8}-[A-F0-9]{12}", reference):
            raise CommerceError("Mã đơn hàng không hợp lệ.", 404)
        note = self._string(body.get("note"), "Ghi chú xử lý", 8, 240)
        status = body.get("status")
        if kind == "status":
            return self.repository.set_order_status(session["staff_id"], reference, status, note)
        if kind == "shipment":
            tracking = self._string(body.get("tracking_reference", ""), "Mã vận đơn nội bộ", 0, 80)
            return self.repository.set_shipment_status(session["staff_id"], reference, status, note, tracking)
        return self.repository.set_payment_status(session["staff_id"], reference, status, note)

    def create_review(self, customer_id, body):
        product_id = self._integer(body.get("product_id"), "Mã sản phẩm", 1)
        rating = self._integer(body.get("rating"), "Số sao", 1, 5)
        comment = self._string(body.get("comment"), "Đánh giá", 10, 1000)
        return self.repository.create_review(customer_id, product_id, rating, comment)

    def moderate_review(self, session, review_id, body):
        self.require(session, "reviews.write")
        status = body.get("status")
        if status not in ("approved", "rejected", "pending"):
            raise CommerceError("Trạng thái đánh giá không hợp lệ.")
        return self.repository.moderate_review(session["staff_id"], review_id, status)

    def create_support_request(self, customer_id, body):
        subject = self._string(body.get("subject"), "Chủ đề", 5, 120)
        message = self._string(body.get("message"), "Nội dung", 10, 2000)
        return self.repository.create_support_request(customer_id, subject, message)

    def update_support(self, session, request_id, body):
        self.require(session, "support.write")
        status = body.get("status")
        if status not in ("open", "in_progress", "resolved"):
            raise CommerceError("Trạng thái hỗ trợ không hợp lệ.")
        response = self._string(body.get("response", ""), "Phản hồi", 0, 2000)
        if status == "resolved" and len(response) < 10:
            raise CommerceError("Cần phản hồi rõ ràng trước khi giải quyết yêu cầu.")
        return self.repository.update_support(session["staff_id"], request_id, status, response)
