"""Persistent customer, cart and order records in the catalogue SQLite database."""

import json
import sqlite3
import time
from contextlib import contextmanager


class CommerceError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class CommerceRepository:
    def __init__(self, db_path):
        self.db_path = db_path
        self._initialize()

    @contextmanager
    def _connect(self, write=False):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except Exception:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def _initialize(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL, password_salt TEXT NOT NULL,
                    name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS customer_sessions (
                    token_hash TEXT PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL, expires_at INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_customer ON customer_sessions(customer_id);
                CREATE TABLE IF NOT EXISTS delivery_addresses (
                    id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    recipient TEXT NOT NULL, phone TEXT NOT NULL, line1 TEXT NOT NULL,
                    ward TEXT NOT NULL, district TEXT NOT NULL, city TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '', is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_addresses_customer ON delivery_addresses(customer_id);
                CREATE TABLE IF NOT EXISTS wishlist_items (
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(customer_id, product_id)
                );
                CREATE TABLE IF NOT EXISTS cart_items (
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
                    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 10),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(customer_id, variant_id)
                );
                CREATE TABLE IF NOT EXISTS customer_orders (
                    id INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE,
                    customer_id INTEGER NOT NULL REFERENCES customers(id),
                    order_status TEXT NOT NULL CHECK(order_status IN ('confirmed', 'cancelled', 'fulfilled')),
                    subtotal_vnd INTEGER NOT NULL CHECK(subtotal_vnd >= 0),
                    discount_vnd INTEGER NOT NULL CHECK(discount_vnd >= 0),
                    delivery_fee_vnd INTEGER NOT NULL CHECK(delivery_fee_vnd >= 0),
                    total_vnd INTEGER NOT NULL CHECK(total_vnd >= 0),
                    promotion_code TEXT NOT NULL DEFAULT '', address_snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_orders_customer ON customer_orders(customer_id, id DESC);
                CREATE TABLE IF NOT EXISTS customer_order_items (
                    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES customer_orders(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL, variant_id INTEGER NOT NULL,
                    sku TEXT NOT NULL, name_vi TEXT NOT NULL, color TEXT NOT NULL, size TEXT NOT NULL,
                    image TEXT NOT NULL, unit_price_vnd INTEGER NOT NULL, quantity INTEGER NOT NULL,
                    line_total_vnd INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS customer_payments (
                    order_id INTEGER PRIMARY KEY REFERENCES customer_orders(id) ON DELETE CASCADE,
                    method TEXT NOT NULL CHECK(method = 'cod'),
                    payment_status TEXT NOT NULL CHECK(payment_status IN ('pending_cod', 'collected', 'failed', 'refunded')),
                    amount_vnd INTEGER NOT NULL, provider_reference TEXT
                );
                CREATE TABLE IF NOT EXISTS customer_shipments (
                    order_id INTEGER PRIMARY KEY REFERENCES customer_orders(id) ON DELETE CASCADE,
                    shipment_status TEXT NOT NULL CHECK(shipment_status IN ('pending', 'packing', 'shipped', 'delivered', 'cancelled')),
                    tracking_reference TEXT
                );
                CREATE TABLE IF NOT EXISTS checkout_requests (
                    customer_id INTEGER NOT NULL REFERENCES customers(id),
                    idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    order_id INTEGER NOT NULL REFERENCES customer_orders(id),
                    PRIMARY KEY(customer_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS promotion_codes (
                    code TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('percent', 'amount', 'free_shipping')),
                    value INTEGER NOT NULL CHECK(value >= 0), max_discount_vnd INTEGER NOT NULL DEFAULT 0,
                    min_subtotal_vnd INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
                    usage_limit INTEGER, used_count INTEGER NOT NULL DEFAULT 0,
                    starts_at TEXT, ends_at TEXT, description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
        with self._connect(write=True) as db:
            db.execute("""INSERT OR IGNORE INTO promotion_codes
                (code, kind, value, max_discount_vnd, description) VALUES
                ('COGU10', 'percent', 10, 100000, 'Giảm 10%, tối đa 100.000 ₫ (mã demo)'),
                ('FREESHIP', 'free_shipping', 0, 0, 'Miễn phí giao hàng (mã demo)')""")

    def get_promotion(self, code, db=None):
        def find(connection):
            row = connection.execute("SELECT * FROM promotion_codes WHERE code = ?", (code,)).fetchone()
            return dict(row) if row else None
        if db is not None:
            return find(db)
        with self._connect() as connection:
            return find(connection)

    def public_promotions(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT code, kind, value, max_discount_vnd,
                min_subtotal_vnd, description FROM promotion_codes
                WHERE active = 1 AND (starts_at IS NULL OR starts_at <= date('now'))
                AND (ends_at IS NULL OR ends_at >= date('now'))
                AND (usage_limit IS NULL OR used_count < usage_limit) ORDER BY code""")]

    @staticmethod
    def _customer(row):
        return {key: row[key] for key in ("id", "email", "name", "phone", "created_at")} if row else None

    def create_customer(self, email, password_hash, salt, name):
        with self._connect(write=True) as db:
            try:
                cursor = db.execute("INSERT INTO customers(email, password_hash, password_salt, name) VALUES (?, ?, ?, ?)",
                                    (email, password_hash, salt, name))
            except sqlite3.IntegrityError:
                raise CommerceError("Email này đã được đăng ký.", 409) from None
            return self._customer(db.execute("SELECT * FROM customers WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def find_customer_by_email(self, email):
        with self._connect() as db:
            row = db.execute("SELECT * FROM customers WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
            return dict(row) if row else None

    def get_customer(self, customer_id):
        with self._connect() as db:
            return self._customer(db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone())

    def update_customer(self, customer_id, name, phone):
        with self._connect(write=True) as db:
            db.execute("UPDATE customers SET name = ?, phone = ? WHERE id = ?", (name, phone, customer_id))
            return self._customer(db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone())

    def create_session(self, token_hash, customer_id, csrf_token, expires_at):
        with self._connect(write=True) as db:
            db.execute("INSERT INTO customer_sessions(token_hash, customer_id, csrf_token, expires_at) VALUES (?, ?, ?, ?)",
                       (token_hash, customer_id, csrf_token, expires_at))

    def get_session(self, token_hash):
        with self._connect() as db:
            row = db.execute("""SELECT s.customer_id, s.csrf_token, s.expires_at, c.email, c.name, c.phone, c.created_at
                FROM customer_sessions s JOIN customers c ON c.id = s.customer_id
                WHERE s.token_hash = ? AND s.expires_at > ?""", (token_hash, int(time.time()))).fetchone()
            return dict(row) if row else None

    def delete_session(self, token_hash):
        with self._connect(write=True) as db:
            db.execute("DELETE FROM customer_sessions WHERE token_hash = ?", (token_hash,))

    def list_addresses(self, customer_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT id, recipient, phone, line1, ward, district, city, note, is_default
                FROM delivery_addresses WHERE customer_id = ? ORDER BY is_default DESC, id DESC""", (customer_id,))]

    def get_address(self, customer_id, address_id, db=None):
        def find(connection):
            row = connection.execute("""SELECT id, recipient, phone, line1, ward, district, city, note, is_default
                FROM delivery_addresses WHERE id = ? AND customer_id = ?""", (address_id, customer_id)).fetchone()
            return dict(row) if row else None
        if db is not None:
            return find(db)
        with self._connect() as connection:
            return find(connection)

    def save_address(self, customer_id, fields, address_id=None):
        with self._connect(write=True) as db:
            current = self.get_address(customer_id, address_id, db) if address_id is not None else None
            if address_id is not None and not current:
                raise CommerceError("Không tìm thấy địa chỉ.", 404)
            count = db.execute("SELECT COUNT(*) FROM delivery_addresses WHERE customer_id = ?", (customer_id,)).fetchone()[0]
            is_default = int(fields.get("is_default", False) or (count == 0 and address_id is None))
            if is_default:
                db.execute("UPDATE delivery_addresses SET is_default = 0 WHERE customer_id = ?", (customer_id,))
            values = (fields["recipient"], fields["phone"], fields["line1"], fields["ward"],
                      fields["district"], fields["city"], fields["note"], is_default)
            if address_id is None:
                cursor = db.execute("""INSERT INTO delivery_addresses
                    (customer_id, recipient, phone, line1, ward, district, city, note, is_default)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (customer_id, *values))
                address_id = cursor.lastrowid
            else:
                db.execute("""UPDATE delivery_addresses SET recipient=?, phone=?, line1=?, ward=?, district=?, city=?, note=?, is_default=?
                    WHERE id=? AND customer_id=?""", (*values, address_id, customer_id))
            if not db.execute("SELECT 1 FROM delivery_addresses WHERE customer_id = ? AND is_default = 1", (customer_id,)).fetchone():
                db.execute("UPDATE delivery_addresses SET is_default = 1 WHERE id = ?", (address_id,))
            return self.get_address(customer_id, address_id, db)

    def delete_address(self, customer_id, address_id):
        with self._connect(write=True) as db:
            current = self.get_address(customer_id, address_id, db)
            if current is None:
                raise CommerceError("Không tìm thấy địa chỉ.", 404)
            db.execute("DELETE FROM delivery_addresses WHERE id = ? AND customer_id = ?", (address_id, customer_id))
            if current["is_default"]:
                row = db.execute("SELECT id FROM delivery_addresses WHERE customer_id = ? ORDER BY id DESC LIMIT 1", (customer_id,)).fetchone()
                if row:
                    db.execute("UPDATE delivery_addresses SET is_default = 1 WHERE id = ?", (row["id"],))

    def list_wishlist(self, customer_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute("""SELECT p.id, p.slug, p.name_vi, p.image, p.price_vnd
                FROM wishlist_items w JOIN products p ON p.id = w.product_id
                WHERE w.customer_id = ? ORDER BY w.created_at DESC, p.id DESC""", (customer_id,))]

    def set_wishlist(self, customer_id, product_id, wanted):
        with self._connect(write=True) as db:
            if not db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
                raise CommerceError("Không tìm thấy sản phẩm.", 404)
            if wanted:
                db.execute("INSERT OR IGNORE INTO wishlist_items(customer_id, product_id) VALUES (?, ?)", (customer_id, product_id))
            else:
                db.execute("DELETE FROM wishlist_items WHERE customer_id = ? AND product_id = ?", (customer_id, product_id))

    def variant(self, variant_id, db=None):
        def find(connection):
            row = connection.execute("""SELECT v.id AS variant_id, v.product_id, v.sku, v.color, v.size, v.stock,
                p.slug, p.name_vi, p.image, p.price_vnd
                FROM product_variants v JOIN products p ON p.id = v.product_id WHERE v.id = ?""", (variant_id,)).fetchone()
            return dict(row) if row else None
        if db is not None:
            return find(db)
        with self._connect() as connection:
            return find(connection)

    @staticmethod
    def _cart_rows(db, customer_id):
        return [dict(row) for row in db.execute("""SELECT c.variant_id, c.quantity, v.product_id, v.sku, v.color, v.size, v.stock,
            p.slug, p.name_vi, p.image, p.price_vnd
            FROM cart_items c JOIN product_variants v ON v.id = c.variant_id
            JOIN products p ON p.id = v.product_id WHERE c.customer_id = ? ORDER BY c.updated_at DESC, c.variant_id""", (customer_id,))]

    def cart(self, customer_id):
        with self._connect() as db:
            return self._cart_rows(db, customer_id)

    def change_cart(self, customer_id, variant_id, quantity, add=False):
        with self._connect(write=True) as db:
            variant = self.variant(variant_id, db)
            if variant is None:
                raise CommerceError("Không tìm thấy phiên bản sản phẩm.", 404)
            row = db.execute("SELECT quantity FROM cart_items WHERE customer_id = ? AND variant_id = ?",
                             (customer_id, variant_id)).fetchone()
            desired = (row["quantity"] if row else 0) + quantity if add else quantity
            if desired > 10:
                raise CommerceError("Tối đa 10 sản phẩm cho mỗi lựa chọn.")
            if desired > variant["stock"]:
                raise CommerceError("Số lượng vượt quá tồn kho hiện tại.", 409)
            if desired == 0:
                db.execute("DELETE FROM cart_items WHERE customer_id = ? AND variant_id = ?", (customer_id, variant_id))
            else:
                db.execute("""INSERT INTO cart_items(customer_id, variant_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(customer_id, variant_id) DO UPDATE SET quantity=excluded.quantity, updated_at=CURRENT_TIMESTAMP""",
                    (customer_id, variant_id, desired))

    def checkout(self, customer_id, address_id, idempotency_key, fingerprint, promotion_code, price_fn, reference):
        with self._connect(write=True) as db:
            prior = db.execute("""SELECT fingerprint, order_id FROM checkout_requests
                WHERE customer_id = ? AND idempotency_key = ?""", (customer_id, idempotency_key)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise CommerceError("Mã xác nhận đã được dùng cho yêu cầu khác.", 409)
                return self._order(db, customer_id, prior["order_id"]), True
            address = self.get_address(customer_id, address_id, db)
            if not address:
                raise CommerceError("Vui lòng chọn địa chỉ giao hàng của bạn.", 404)
            items = self._cart_rows(db, customer_id)
            if not items:
                raise CommerceError("Giỏ hàng đang trống.", 409)
            promotion = self.get_promotion(promotion_code, db) if promotion_code else None
            totals = price_fn(items, promotion_code, promotion)
            for item in items:
                changed = db.execute("""UPDATE product_variants SET stock = stock - ?
                    WHERE id = ? AND stock >= ?""", (item["quantity"], item["variant_id"], item["quantity"]))
                if changed.rowcount != 1:
                    raise CommerceError(f"{item['name_vi']} không còn đủ hàng.", 409)
            snapshot = json.dumps(address, ensure_ascii=False)
            cursor = db.execute("""INSERT INTO customer_orders
                (reference, customer_id, order_status, subtotal_vnd, discount_vnd, delivery_fee_vnd,
                 total_vnd, promotion_code, address_snapshot) VALUES (?, ?, 'confirmed', ?, ?, ?, ?, ?, ?)""",
                (reference, customer_id, totals["subtotal_vnd"], totals["discount_vnd"],
                 totals["delivery_fee_vnd"], totals["total_vnd"], promotion_code, snapshot))
            order_id = cursor.lastrowid
            db.executemany("""INSERT INTO customer_order_items
                (order_id, product_id, variant_id, sku, name_vi, color, size, image, unit_price_vnd, quantity, line_total_vnd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(order_id, item["product_id"], item["variant_id"], item["sku"], item["name_vi"],
                  item["color"], item["size"], item["image"], item["price_vnd"], item["quantity"],
                  item["price_vnd"] * item["quantity"]) for item in items])
            db.execute("INSERT INTO customer_payments(order_id, method, payment_status, amount_vnd) VALUES (?, 'cod', 'pending_cod', ?)",
                       (order_id, totals["total_vnd"]))
            db.execute("INSERT INTO customer_shipments(order_id, shipment_status) VALUES (?, 'pending')", (order_id,))
            db.execute("INSERT INTO checkout_requests(customer_id, idempotency_key, fingerprint, order_id) VALUES (?, ?, ?, ?)",
                       (customer_id, idempotency_key, fingerprint, order_id))
            if promotion_code:
                db.execute("UPDATE promotion_codes SET used_count = used_count + 1 WHERE code = ?", (promotion_code,))
            db.execute("DELETE FROM cart_items WHERE customer_id = ?", (customer_id,))
            return self._order(db, customer_id, order_id), False

    @staticmethod
    def _order(db, customer_id, order_id):
        row = db.execute("""SELECT o.*, p.method AS payment_method, p.payment_status,
            CASE WHEN p.payment_status IN ('collected', 'refunded') THEN 'staff_recorded_cod' ELSE NULL END AS payment_source,
            s.shipment_status, s.tracking_reference,
            CASE WHEN s.shipment_status IN ('packing', 'shipped', 'delivered') THEN 'staff_recorded_demo' ELSE NULL END AS shipment_source
            FROM customer_orders o JOIN customer_payments p ON p.order_id = o.id
            JOIN customer_shipments s ON s.order_id = o.id
            WHERE o.id = ? AND o.customer_id = ?""", (order_id, customer_id)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result.pop("customer_id")
        result["address"] = json.loads(result.pop("address_snapshot"))
        result["items"] = [dict(item) for item in db.execute("""SELECT product_id, variant_id, sku, name_vi, color, size,
            image, unit_price_vnd, quantity, line_total_vnd FROM customer_order_items WHERE order_id = ? ORDER BY id""", (order_id,))]
        return result

    def list_orders(self, customer_id):
        with self._connect() as db:
            ids = [row[0] for row in db.execute("SELECT id FROM customer_orders WHERE customer_id = ? ORDER BY id DESC", (customer_id,))]
            return [self._order(db, customer_id, order_id) for order_id in ids]

    def get_order(self, customer_id, reference):
        with self._connect() as db:
            row = db.execute("SELECT id FROM customer_orders WHERE customer_id = ? AND reference = ?",
                             (customer_id, reference)).fetchone()
            return self._order(db, customer_id, row["id"]) if row else None
