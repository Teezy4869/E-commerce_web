"""SQLite persistence for staff, catalogue operations and store workflows."""

import json
import sqlite3
import time

from data.commerce_repository import CommerceError, CommerceRepository


class AdminRepository(CommerceRepository):
    def __init__(self, db_path):
        super().__init__(db_path)
        self._initialize_admin()

    def _initialize_admin(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS staff_users (
                    id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN
                    ('administrator', 'sales', 'warehouse', 'support', 'manager')),
                    password_hash TEXT NOT NULL, password_salt TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS staff_sessions (
                    token_hash TEXT PRIMARY KEY, staff_id INTEGER NOT NULL REFERENCES staff_users(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL, expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS admin_audit (
                    id INTEGER PRIMARY KEY, staff_id INTEGER REFERENCES staff_users(id),
                    action TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit(id DESC);
                CREATE TABLE IF NOT EXISTS product_reviews (
                    id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    order_id INTEGER NOT NULL REFERENCES customer_orders(id),
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                    comment TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'approved', 'rejected')),
                    moderated_by INTEGER REFERENCES staff_users(id),
                    moderated_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(customer_id, product_id)
                );
                CREATE INDEX IF NOT EXISTS idx_reviews_status ON product_reviews(status, id DESC);
                CREATE TABLE IF NOT EXISTS support_requests (
                    id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
                    subject TEXT NOT NULL, message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open', 'in_progress', 'resolved')),
                    response TEXT NOT NULL DEFAULT '', handled_by INTEGER REFERENCES staff_users(id),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_support_status ON support_requests(status, id DESC);
                CREATE TABLE IF NOT EXISTS order_events (
                    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES customer_orders(id),
                    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
                    event_type TEXT NOT NULL, previous_value TEXT NOT NULL, new_value TEXT NOT NULL,
                    note TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'staff_recorded_demo',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
        with self._connect(write=True) as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(customer_payments)")}
            if "collected_at" not in columns:
                db.execute("ALTER TABLE customer_payments ADD COLUMN collected_at TEXT")
            if "recorded_by" not in columns:
                db.execute("ALTER TABLE customer_payments ADD COLUMN recorded_by INTEGER REFERENCES staff_users(id)")
            if "collection_note" not in columns:
                db.execute("ALTER TABLE customer_payments ADD COLUMN collection_note TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _audit(db, staff_id, action, target_type, target_id, details=None):
        db.execute("""INSERT INTO admin_audit(staff_id, action, target_type, target_id, details)
            VALUES (?, ?, ?, ?, ?)""", (staff_id, action, target_type, str(target_id), json.dumps(details or {}, ensure_ascii=False)))

    @staticmethod
    def _staff(row):
        return {key: row[key] for key in ("id", "email", "name", "role", "active", "created_at")} if row else None

    def create_staff(self, email, name, role, password_hash, salt, actor_id=None):
        with self._connect(write=True) as db:
            try:
                cursor = db.execute("""INSERT INTO staff_users(email, name, role, password_hash, password_salt)
                    VALUES (?, ?, ?, ?, ?)""", (email, name, role, password_hash, salt))
            except sqlite3.IntegrityError:
                raise CommerceError("Email nhân viên đã tồn tại.", 409) from None
            self._audit(db, actor_id, "staff.create", "staff", cursor.lastrowid, {"role": role})
            return self._staff(db.execute("SELECT * FROM staff_users WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def find_staff_by_email(self, email):
        with self._connect() as db:
            row = db.execute("SELECT * FROM staff_users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
            return dict(row) if row else None

    def reset_staff_password(self, email, password_hash, salt):
        with self._connect(write=True) as db:
            row = db.execute("SELECT id FROM staff_users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy nhân viên.", 404)
            db.execute("UPDATE staff_users SET password_hash = ?, password_salt = ? WHERE id = ?",
                       (password_hash, salt, row["id"]))
            db.execute("DELETE FROM staff_sessions WHERE staff_id = ?", (row["id"],))
            self._audit(db, None, "staff.password_reset_local", "staff", row["id"])

    def create_staff_session(self, token_hash, staff_id, csrf_token, expires_at):
        with self._connect(write=True) as db:
            db.execute("INSERT INTO staff_sessions VALUES (?, ?, ?, ?)", (token_hash, staff_id, csrf_token, expires_at))

    def get_staff_session(self, token_hash):
        with self._connect() as db:
            row = db.execute("""SELECT s.staff_id, s.csrf_token, s.expires_at, u.email, u.name, u.role, u.active
                FROM staff_sessions s JOIN staff_users u ON u.id = s.staff_id
                WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1""", (token_hash, int(time.time()))).fetchone()
            return dict(row) if row else None

    def delete_staff_session(self, token_hash):
        with self._connect(write=True) as db:
            db.execute("DELETE FROM staff_sessions WHERE token_hash = ?", (token_hash,))

    def list_staff(self):
        with self._connect() as db:
            return [self._staff(row) for row in db.execute("SELECT * FROM staff_users ORDER BY id")]

    def update_staff(self, actor_id, staff_id, role, active):
        with self._connect(write=True) as db:
            row = db.execute("SELECT * FROM staff_users WHERE id = ?", (staff_id,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy nhân viên.", 404)
            if staff_id == actor_id and (not active or role != "administrator"):
                raise CommerceError("Không thể tắt hoặc đổi vai trò tài khoản quản trị đang dùng.", 409)
            if row["role"] == "administrator" and (not active or role != "administrator"):
                count = db.execute("SELECT COUNT(*) FROM staff_users WHERE role = 'administrator' AND active = 1").fetchone()[0]
                if count <= 1:
                    raise CommerceError("Cần giữ ít nhất một quản trị viên hoạt động.", 409)
            db.execute("UPDATE staff_users SET role = ?, active = ? WHERE id = ?", (role, int(active), staff_id))
            if not active or role != row["role"]:
                db.execute("DELETE FROM staff_sessions WHERE staff_id = ?", (staff_id,))
            self._audit(db, actor_id, "staff.update", "staff", staff_id, {"role": role, "active": active})
            return self._staff(db.execute("SELECT * FROM staff_users WHERE id = ?", (staff_id,)).fetchone())

    def list_admin_products(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT p.*, COUNT(v.id) AS variant_count,
                COALESCE(SUM(v.stock), 0) AS stock, GROUP_CONCAT(v.sku, ' ') AS skus FROM products p
                LEFT JOIN product_variants v ON v.product_id = p.id
                GROUP BY p.id ORDER BY p.id DESC""")]

    def get_admin_product(self, product_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                return None
            product = dict(row)
            product["variants"] = [dict(v) for v in db.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY id", (product_id,))]
            product["images"] = [dict(v) for v in db.execute("SELECT color, image, position FROM product_images WHERE product_id = ? ORDER BY position", (product_id,))]
            return product

    def save_product(self, staff_id, fields, product_id=None):
        with self._connect(write=True) as db:
            created = product_id is None
            values = (fields["slug"], fields["name_vi"], fields["description_vi"], fields["category"],
                      fields["material"], fields["price_vnd"], fields["image"],
                      int(fields["is_new"]), int(fields["is_bestseller"]))
            try:
                if product_id is None:
                    cursor = db.execute("""INSERT INTO products
                        (slug, name_vi, description_vi, category, material, price_vnd, image, is_new, is_bestseller)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", values)
                    product_id = cursor.lastrowid
                    db.execute("INSERT INTO product_images VALUES (?, 'default', ?, 0)", (product_id, fields["image"]))
                else:
                    if not db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
                        raise CommerceError("Không tìm thấy sản phẩm.", 404)
                    db.execute("""UPDATE products SET slug=?, name_vi=?, description_vi=?, category=?, material=?,
                        price_vnd=?, image=?, is_new=?, is_bestseller=? WHERE id=?""", (*values, product_id))
                    db.execute("""INSERT INTO product_images(product_id, color, image, position)
                        VALUES (?, 'default', ?, 0) ON CONFLICT(product_id, color, position)
                        DO UPDATE SET image=excluded.image""", (product_id, fields["image"]))
            except sqlite3.IntegrityError:
                raise CommerceError("Slug sản phẩm đã tồn tại.", 409) from None
            self._audit(db, staff_id, "product.create" if created else "product.update", "product", product_id, fields)
        return self.get_admin_product(product_id)

    def delete_product(self, staff_id, product_id):
        with self._connect(write=True) as db:
            row = db.execute("SELECT slug FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy sản phẩm.", 404)
            db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self._audit(db, staff_id, "product.delete", "product", product_id, {"slug": row["slug"]})

    def save_variant(self, staff_id, product_id, fields, variant_id=None):
        with self._connect(write=True) as db:
            if not db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
                raise CommerceError("Không tìm thấy sản phẩm.", 404)
            values = (fields["sku"], fields["color"], fields["size"], fields["stock"])
            try:
                if variant_id is None:
                    cursor = db.execute("""INSERT INTO product_variants(product_id, sku, color, size, stock)
                        VALUES (?, ?, ?, ?, ?)""", (product_id, *values))
                    variant_id = cursor.lastrowid
                else:
                    if not db.execute("SELECT 1 FROM product_variants WHERE id = ? AND product_id = ?", (variant_id, product_id)).fetchone():
                        raise CommerceError("Không tìm thấy phiên bản.", 404)
                    db.execute("UPDATE product_variants SET sku=?, color=?, size=?, stock=? WHERE id=?", (*values, variant_id))
            except sqlite3.IntegrityError:
                raise CommerceError("SKU hoặc lựa chọn màu/cỡ đã tồn tại.", 409) from None
            self._audit(db, staff_id, "variant.save", "variant", variant_id, fields)
            return dict(db.execute("SELECT * FROM product_variants WHERE id = ?", (variant_id,)).fetchone())

    def set_stock(self, staff_id, variant_id, stock, note):
        with self._connect(write=True) as db:
            row = db.execute("SELECT * FROM product_variants WHERE id = ?", (variant_id,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy phiên bản.", 404)
            db.execute("UPDATE product_variants SET stock = ? WHERE id = ?", (stock, variant_id))
            self._audit(db, staff_id, "stock.set", "variant", variant_id, {"from": row["stock"], "to": stock, "note": note})
            return dict(db.execute("SELECT * FROM product_variants WHERE id = ?", (variant_id,)).fetchone())

    def delete_variant(self, staff_id, variant_id):
        with self._connect(write=True) as db:
            row = db.execute("SELECT * FROM product_variants WHERE id = ?", (variant_id,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy phiên bản.", 404)
            db.execute("DELETE FROM product_variants WHERE id = ?", (variant_id,))
            self._audit(db, staff_id, "variant.delete", "variant", variant_id, {"sku": row["sku"]})

    def list_promotions(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM promotion_codes ORDER BY created_at DESC, code")]

    def save_promotion(self, staff_id, fields, code=None):
        with self._connect(write=True) as db:
            if code is None:
                try:
                    db.execute("""INSERT INTO promotion_codes
                        (code, kind, value, max_discount_vnd, min_subtotal_vnd, active, usage_limit,
                         starts_at, ends_at, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (fields["code"], fields["kind"], fields["value"], fields["max_discount_vnd"],
                         fields["min_subtotal_vnd"], int(fields["active"]), fields["usage_limit"],
                         fields["starts_at"], fields["ends_at"], fields["description"]))
                except sqlite3.IntegrityError:
                    raise CommerceError("Mã ưu đãi đã tồn tại.", 409) from None
                code = fields["code"]
            else:
                if not db.execute("SELECT 1 FROM promotion_codes WHERE code = ?", (code,)).fetchone():
                    raise CommerceError("Không tìm thấy mã ưu đãi.", 404)
                db.execute("""UPDATE promotion_codes SET kind=?, value=?, max_discount_vnd=?,
                    min_subtotal_vnd=?, active=?, usage_limit=?, starts_at=?, ends_at=?, description=?
                    WHERE code=?""", (fields["kind"], fields["value"], fields["max_discount_vnd"],
                    fields["min_subtotal_vnd"], int(fields["active"]), fields["usage_limit"],
                    fields["starts_at"], fields["ends_at"], fields["description"], code))
            self._audit(db, staff_id, "promotion.save", "promotion", code, fields)
            return dict(db.execute("SELECT * FROM promotion_codes WHERE code = ?", (code,)).fetchone())

    def delete_promotion(self, staff_id, code):
        with self._connect(write=True) as db:
            changed = db.execute("DELETE FROM promotion_codes WHERE code = ?", (code,))
            if changed.rowcount != 1:
                raise CommerceError("Không tìm thấy mã ưu đãi.", 404)
            self._audit(db, staff_id, "promotion.delete", "promotion", code)

    @staticmethod
    def _admin_order(db, order_id):
        row = db.execute("SELECT customer_id FROM customer_orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return None
        result = CommerceRepository._order(db, row["customer_id"], order_id)
        customer = db.execute("SELECT email, name FROM customers WHERE id = ?", (row["customer_id"],)).fetchone()
        result["customer"] = dict(customer)
        result["events"] = [dict(event) for event in db.execute("""SELECT e.*, s.name AS staff_name
            FROM order_events e JOIN staff_users s ON s.id = e.staff_id
            WHERE e.order_id = ? ORDER BY e.id""", (order_id,))]
        payment = db.execute("SELECT collected_at, collection_note, recorded_by FROM customer_payments WHERE order_id = ?", (order_id,)).fetchone()
        result["payment_record"] = dict(payment)
        return result

    def list_admin_orders(self):
        with self._connect() as db:
            ids = [row[0] for row in db.execute("SELECT id FROM customer_orders ORDER BY id DESC LIMIT 300")]
            return [self._admin_order(db, order_id) for order_id in ids]

    def get_admin_order(self, reference):
        with self._connect() as db:
            row = db.execute("SELECT id FROM customer_orders WHERE reference = ?", (reference,)).fetchone()
            return self._admin_order(db, row["id"]) if row else None

    @staticmethod
    def _order_row(db, reference):
        row = db.execute("""SELECT o.*, p.payment_status, s.shipment_status
            FROM customer_orders o JOIN customer_payments p ON p.order_id = o.id
            JOIN customer_shipments s ON s.order_id = o.id WHERE o.reference = ?""", (reference,)).fetchone()
        if not row:
            raise CommerceError("Không tìm thấy đơn hàng.", 404)
        return row

    @staticmethod
    def _event(db, order_id, staff_id, kind, previous, new, note):
        db.execute("""INSERT INTO order_events(order_id, staff_id, event_type, previous_value, new_value, note)
            VALUES (?, ?, ?, ?, ?, ?)""", (order_id, staff_id, kind, previous, new, note))

    def set_order_status(self, staff_id, reference, status, note):
        with self._connect(write=True) as db:
            row = self._order_row(db, reference)
            old = row["order_status"]
            if old != "confirmed" or status not in ("cancelled", "fulfilled"):
                raise CommerceError("Chuyển trạng thái đơn hàng không hợp lệ.", 409)
            if status == "cancelled":
                if row["shipment_status"] not in ("pending", "packing") or row["payment_status"] != "pending_cod":
                    raise CommerceError("Chỉ có thể hủy đơn trước khi giao và trước khi thu COD.", 409)
                for item in db.execute("SELECT variant_id, quantity FROM customer_order_items WHERE order_id = ?", (row["id"],)):
                    db.execute("UPDATE product_variants SET stock = stock + ? WHERE id = ?", (item["quantity"], item["variant_id"]))
                db.execute("UPDATE customer_shipments SET shipment_status = 'cancelled' WHERE order_id = ?", (row["id"],))
                if row["promotion_code"]:
                    db.execute("UPDATE promotion_codes SET used_count = MAX(0, used_count - 1) WHERE code = ?", (row["promotion_code"],))
            elif row["shipment_status"] != "delivered" or row["payment_status"] != "collected":
                raise CommerceError("Chỉ hoàn tất đơn khi đã ghi nhận giao hàng và thu COD.", 409)
            db.execute("UPDATE customer_orders SET order_status = ? WHERE id = ?", (status, row["id"]))
            self._event(db, row["id"], staff_id, "order_status", old, status, note)
            self._audit(db, staff_id, "order.status", "order", reference, {"from": old, "to": status, "note": note})
        return self.get_admin_order(reference)

    def set_shipment_status(self, staff_id, reference, status, note, tracking_reference=""):
        next_states = {"pending": "packing", "packing": "shipped", "shipped": "delivered"}
        with self._connect(write=True) as db:
            row = self._order_row(db, reference)
            old = row["shipment_status"]
            if row["order_status"] != "confirmed" or next_states.get(old) != status:
                raise CommerceError("Chuyển trạng thái giao hàng không hợp lệ.", 409)
            db.execute("""UPDATE customer_shipments SET shipment_status = ?,
                tracking_reference = CASE WHEN ? = '' THEN tracking_reference ELSE ? END WHERE order_id = ?""",
                (status, tracking_reference, tracking_reference, row["id"]))
            self._event(db, row["id"], staff_id, "shipment_status", old, status, note)
            self._audit(db, staff_id, "shipment.status", "order", reference, {"from": old, "to": status, "note": note, "internal_reference": tracking_reference})
        return self.get_admin_order(reference)

    def set_payment_status(self, staff_id, reference, status, note):
        with self._connect(write=True) as db:
            row = self._order_row(db, reference)
            old = row["payment_status"]
            if status == "collected":
                if old != "pending_cod" or row["shipment_status"] != "delivered" or row["order_status"] != "confirmed":
                    raise CommerceError("Chỉ ghi nhận thu COD sau khi đã ghi nhận giao hàng.", 409)
                db.execute("""UPDATE customer_payments SET payment_status = 'collected',
                    collected_at = CURRENT_TIMESTAMP, recorded_by = ?, collection_note = ? WHERE order_id = ?""",
                    (staff_id, note, row["id"]))
            elif status == "refunded":
                if old != "collected":
                    raise CommerceError("Chỉ ghi nhận hoàn tiền cho khoản COD đã thu.", 409)
                db.execute("""UPDATE customer_payments SET payment_status = 'refunded',
                    recorded_by = ?, collection_note = ? WHERE order_id = ?""", (staff_id, note, row["id"]))
            else:
                raise CommerceError("Trạng thái thanh toán không hợp lệ.")
            self._event(db, row["id"], staff_id, "payment_status", old, status, note)
            self._audit(db, staff_id, "payment.status", "order", reference, {"from": old, "to": status, "note": note, "source": "staff_recorded_cod"})
        return self.get_admin_order(reference)

    def dashboard(self):
        with self._connect() as db:
            metrics = dict(db.execute("""SELECT COUNT(*) AS orders_total,
                SUM(CASE WHEN order_status = 'confirmed' THEN 1 ELSE 0 END) AS orders_active,
                SUM(CASE WHEN order_status = 'cancelled' THEN 1 ELSE 0 END) AS orders_cancelled
                FROM customer_orders""").fetchone())
            money = dict(db.execute("""SELECT
                COALESCE(SUM(CASE WHEN p.payment_status = 'collected' THEN p.amount_vnd ELSE 0 END), 0) AS settled_revenue_vnd,
                COALESCE(SUM(CASE WHEN p.payment_status = 'pending_cod' AND o.order_status != 'cancelled'
                    THEN p.amount_vnd ELSE 0 END), 0) AS pending_cod_vnd,
                SUM(CASE WHEN p.payment_status = 'pending_cod' AND o.order_status != 'cancelled'
                    THEN 1 ELSE 0 END) AS pending_payment_count
                FROM customer_payments p JOIN customer_orders o ON o.id = p.order_id""").fetchone())
            stock = dict(db.execute("""SELECT SUM(CASE WHEN stock BETWEEN 1 AND 5 THEN 1 ELSE 0 END) AS low_stock_variants,
                SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS sold_out_variants FROM product_variants""").fetchone())
            low = [dict(row) for row in db.execute("""SELECT v.id, v.sku, v.color, v.size, v.stock, p.name_vi, p.slug
                FROM product_variants v JOIN products p ON p.id = v.product_id WHERE v.stock <= 5
                ORDER BY v.stock, v.id LIMIT 20""")]
            counts = dict(db.execute("""SELECT
                (SELECT COUNT(*) FROM product_reviews WHERE status = 'pending') AS pending_reviews,
                (SELECT COUNT(*) FROM support_requests WHERE status != 'resolved') AS open_support""").fetchone())
            return {**metrics, **money, **stock, **counts, "low_stock": low,
                    "recent_orders": [self._admin_order(db, row["id"]) for row in db.execute("SELECT id FROM customer_orders ORDER BY id DESC LIMIT 6")]}

    def reports(self):
        with self._connect() as db:
            days = [dict(row) for row in db.execute("""SELECT date(o.created_at) AS day,
                COUNT(*) AS order_count,
                SUM(CASE WHEN o.order_status != 'cancelled' THEN o.total_vnd ELSE 0 END) AS placed_value_vnd,
                SUM(CASE WHEN p.payment_status = 'collected' THEN p.amount_vnd ELSE 0 END) AS settled_revenue_vnd
                FROM customer_orders o JOIN customer_payments p ON p.order_id = o.id
                GROUP BY date(o.created_at) ORDER BY day DESC LIMIT 30""")]
            top = [dict(row) for row in db.execute("""SELECT i.product_id, i.name_vi,
                SUM(i.quantity) AS units, SUM(i.line_total_vnd) AS placed_value_vnd
                FROM customer_order_items i JOIN customer_orders o ON o.id = i.order_id
                WHERE o.order_status != 'cancelled' GROUP BY i.product_id, i.name_vi
                ORDER BY units DESC LIMIT 10""")]
            inventory = [dict(row) for row in db.execute("""SELECT p.category, COUNT(DISTINCT p.id) AS products,
                COUNT(v.id) AS variants, COALESCE(SUM(v.stock), 0) AS units,
                COALESCE(SUM(v.stock * p.price_vnd), 0) AS inventory_value_vnd
                FROM products p LEFT JOIN product_variants v ON v.product_id = p.id
                GROUP BY p.category ORDER BY p.category""")]
            return {"sales_by_day": days, "top_products": top, "inventory_by_category": inventory,
                    "revenue_basis": "Staff-recorded COD collections still marked collected; no third-party verification."}

    def review_eligible_products(self, customer_id):
        with self._connect() as db:
            return [row[0] for row in db.execute("""SELECT DISTINCT i.product_id
                FROM customer_order_items i JOIN customer_orders o ON o.id = i.order_id
                JOIN customer_payments p ON p.order_id = o.id
                JOIN customer_shipments s ON s.order_id = o.id
                WHERE o.customer_id = ? AND o.order_status = 'fulfilled'
                AND p.payment_status = 'collected' AND s.shipment_status = 'delivered'""", (customer_id,))]

    def list_reviewable_products(self, customer_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT DISTINCT product.id, product.slug,
                product.name_vi, product.image FROM customer_order_items i
                JOIN customer_orders o ON o.id = i.order_id
                JOIN customer_payments payment ON payment.order_id = o.id
                JOIN customer_shipments shipment ON shipment.order_id = o.id
                JOIN products product ON product.id = i.product_id
                LEFT JOIN product_reviews review ON review.customer_id = o.customer_id
                    AND review.product_id = product.id
                WHERE o.customer_id = ? AND o.order_status = 'fulfilled'
                    AND payment.payment_status = 'collected'
                    AND shipment.shipment_status = 'delivered' AND review.id IS NULL
                ORDER BY product.id DESC""", (customer_id,))]

    def list_customer_reviews(self, customer_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT r.*, p.name_vi, p.slug FROM product_reviews r
                JOIN products p ON p.id = r.product_id WHERE r.customer_id = ? ORDER BY r.id DESC""", (customer_id,))]

    def create_review(self, customer_id, product_id, rating, comment):
        with self._connect(write=True) as db:
            row = db.execute("""SELECT o.id FROM customer_order_items i
                JOIN customer_orders o ON o.id = i.order_id
                JOIN customer_payments p ON p.order_id = o.id
                JOIN customer_shipments s ON s.order_id = o.id
                WHERE o.customer_id = ? AND i.product_id = ? AND o.order_status = 'fulfilled'
                AND p.payment_status = 'collected' AND s.shipment_status = 'delivered'
                ORDER BY o.id DESC LIMIT 1""", (customer_id, product_id)).fetchone()
            if not row:
                raise CommerceError("Chỉ có thể đánh giá sau khi đơn đã giao, thu COD và hoàn tất.", 403)
            try:
                cursor = db.execute("""INSERT INTO product_reviews(customer_id, product_id, order_id, rating, comment)
                    VALUES (?, ?, ?, ?, ?)""", (customer_id, product_id, row["id"], rating, comment))
            except sqlite3.IntegrityError:
                raise CommerceError("Bạn đã đánh giá sản phẩm này.", 409) from None
            return dict(db.execute("SELECT * FROM product_reviews WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def public_reviews(self, product_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT r.id, r.rating, r.comment, r.created_at,
                c.name AS customer_name, 1 AS verified_purchase FROM product_reviews r
                JOIN customers c ON c.id = r.customer_id WHERE r.product_id = ? AND r.status = 'approved'
                ORDER BY r.id DESC""", (product_id,))]

    def list_admin_reviews(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT r.*, c.name AS customer_name, c.email,
                p.name_vi, p.slug FROM product_reviews r
                JOIN customers c ON c.id = r.customer_id JOIN products p ON p.id = r.product_id
                ORDER BY CASE r.status WHEN 'pending' THEN 0 ELSE 1 END, r.id DESC LIMIT 300""")]

    def moderate_review(self, staff_id, review_id, status):
        with self._connect(write=True) as db:
            row = db.execute("SELECT status FROM product_reviews WHERE id = ?", (review_id,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy đánh giá.", 404)
            db.execute("""UPDATE product_reviews SET status = ?, moderated_by = ?,
                moderated_at = CURRENT_TIMESTAMP WHERE id = ?""", (status, staff_id, review_id))
            self._audit(db, staff_id, "review.moderate", "review", review_id, {"from": row["status"], "to": status})
            return dict(db.execute("SELECT * FROM product_reviews WHERE id = ?", (review_id,)).fetchone())

    def create_support_request(self, customer_id, subject, message):
        with self._connect(write=True) as db:
            cursor = db.execute("INSERT INTO support_requests(customer_id, subject, message) VALUES (?, ?, ?)",
                                (customer_id, subject, message))
            return dict(db.execute("SELECT * FROM support_requests WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def list_customer_support(self, customer_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM support_requests WHERE customer_id = ? ORDER BY id DESC", (customer_id,))]

    def list_admin_support(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT t.*, c.name AS customer_name, c.email FROM support_requests t
                JOIN customers c ON c.id = t.customer_id ORDER BY CASE t.status WHEN 'open' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END, t.id DESC LIMIT 300""")]

    def update_support(self, staff_id, request_id, status, response):
        with self._connect(write=True) as db:
            row = db.execute("SELECT status FROM support_requests WHERE id = ?", (request_id,)).fetchone()
            if not row:
                raise CommerceError("Không tìm thấy yêu cầu hỗ trợ.", 404)
            db.execute("""UPDATE support_requests SET status = ?, response = ?, handled_by = ?,
                updated_at = CURRENT_TIMESTAMP WHERE id = ?""", (status, response, staff_id, request_id))
            self._audit(db, staff_id, "support.update", "support", request_id, {"from": row["status"], "to": status})
            return dict(db.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,)).fetchone())
