"""SQLite-backed COGU catalogue; original search JSON remains an immutable fixture."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from data.catalog_models import CATALOG_CATEGORIES, Product, ProductVariant


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "cogu_catalog.sqlite3"
SEED = ROOT / "dataset" / "catalog_seed.json"


class CatalogRepository:
    def __init__(self, db_path=None, seed_path=SEED):
        self.db_path = Path(db_path or os.environ.get("COGU_CATALOG_DB") or DEFAULT_DB).resolve()
        self.seed_path = Path(seed_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL, description_vi TEXT NOT NULL,
                    category TEXT NOT NULL, material TEXT NOT NULL,
                    price_vnd INTEGER NOT NULL CHECK(price_vnd > 0),
                    image TEXT NOT NULL, is_new INTEGER NOT NULL DEFAULT 0,
                    is_bestseller INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS product_variants (
                    id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    sku TEXT NOT NULL UNIQUE, color TEXT NOT NULL, size TEXT NOT NULL,
                    stock INTEGER NOT NULL CHECK(stock >= 0),
                    UNIQUE(product_id, color, size)
                );
                CREATE TABLE IF NOT EXISTS product_images (
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    color TEXT NOT NULL, image TEXT NOT NULL, position INTEGER NOT NULL,
                    PRIMARY KEY(product_id, color, position)
                );
                CREATE INDEX IF NOT EXISTS idx_catalog_category_price ON products(category, price_vnd);
                CREATE INDEX IF NOT EXISTS idx_variant_filter ON product_variants(color, size, stock);
            """)
            if db.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
                return
            with self.seed_path.open(encoding="utf-8") as source:
                products = json.load(source)
            if not 30 <= len(products) <= 60:
                raise ValueError("Catalogue seed must contain 30–60 products")
            for raw in products:
                product = Product(**{key: raw[key] for key in Product.__dataclass_fields__})
                if (not product.slug or product.price_vnd <= 0 or not product.image.startswith("images/")
                        or product.category not in CATALOG_CATEGORIES):
                    raise ValueError(f"Invalid catalogue product {product.id}")
                db.execute("""INSERT INTO products
                    (id, slug, name_vi, description_vi, category, material, price_vnd, image, is_new, is_bestseller)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (product.id, product.slug, product.name_vi, product.description_vi,
                     product.category, product.material, product.price_vnd, product.image,
                     int(product.is_new), int(product.is_bestseller)))
                for position, image in enumerate(raw["images"]):
                    if not image["image"].startswith("images/"):
                        raise ValueError(f"Invalid image for {product.slug}")
                    db.execute("INSERT INTO product_images VALUES (?, ?, ?, ?)",
                               (product.id, image["color"], image["image"], position))
                for raw_variant in raw["variants"]:
                    variant = ProductVariant(id=raw_variant["id"], product_id=product.id,
                                             sku=raw_variant["sku"], color=raw_variant["color"],
                                             size=raw_variant["size"], stock=raw_variant["stock"])
                    if variant.stock < 0 or variant.size == "" or variant.color == "":
                        raise ValueError(f"Invalid variant {variant.sku}")
                    db.execute("""INSERT INTO product_variants
                        (id, product_id, sku, color, size, stock) VALUES (?, ?, ?, ?, ?, ?)""",
                        (variant.id, variant.product_id, variant.sku, variant.color, variant.size, variant.stock))

    def list_products(self, *, category=None, color=None, size=None, min_price=None,
                      max_price=None, query=None, sort="newest", page=1, page_size=12):
        conditions = []
        values = []
        if category:
            conditions.append("p.category = ?")
            values.append(category)
        if min_price is not None:
            conditions.append("p.price_vnd >= ?")
            values.append(min_price)
        if max_price is not None:
            conditions.append("p.price_vnd <= ?")
            values.append(max_price)
        if query:
            conditions.append("(p.name_vi LIKE ? OR p.description_vi LIKE ? OR p.material LIKE ?)")
            values.extend([f"%{query}%"] * 3)
        if color or size:
            variant_conditions = ["v.product_id = p.id"]
            if color:
                variant_conditions.append("v.color = ?")
                values.append(color)
            if size:
                variant_conditions.append("v.size = ?")
                values.append(size)
            conditions.append("EXISTS (SELECT 1 FROM product_variants v WHERE " + " AND ".join(variant_conditions) + ")")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order = {
            "newest": "p.id DESC", "price_asc": "p.price_vnd ASC, p.id DESC",
            "price_desc": "p.price_vnd DESC, p.id DESC", "name": "p.name_vi COLLATE NOCASE ASC",
            "popular": "p.is_bestseller DESC, p.id DESC",
        }[sort]
        with self._connect() as db:
            total = db.execute("SELECT COUNT(*) FROM products p" + where, values).fetchone()[0]
            rows = db.execute("SELECT p.* FROM products p" + where + f" ORDER BY {order} LIMIT ? OFFSET ?",
                              [*values, page_size, (page - 1) * page_size]).fetchall()
            return total, [self._summary(db, row) for row in rows]

    def _summary(self, db, row):
        item = dict(row)
        item["is_new"] = bool(item["is_new"])
        item["is_bestseller"] = bool(item["is_bestseller"])
        variants = db.execute("SELECT color, size, stock FROM product_variants WHERE product_id = ?", (item["id"],)).fetchall()
        item["colors"] = list(dict.fromkeys(v["color"] for v in variants))
        item["sizes"] = list(dict.fromkeys(v["size"] for v in variants))
        item["stock"] = sum(v["stock"] for v in variants)
        return item

    def get_product(self, slug):
        with self._connect() as db:
            row = db.execute("SELECT * FROM products WHERE slug = ?", (slug,)).fetchone()
            if row is None:
                return None
            item = self._summary(db, row)
            item["images"] = [dict(r) for r in db.execute(
                "SELECT color, image, position FROM product_images WHERE product_id = ? ORDER BY position", (item["id"],))]
            item["variants"] = [dict(r) for r in db.execute(
                "SELECT id, sku, color, size, stock FROM product_variants WHERE product_id = ? ORDER BY id", (item["id"],))]
            return item

    def get_variant(self, slug, color, size):
        with self._connect() as db:
            row = db.execute("""SELECT v.id, v.product_id, v.sku, v.color, v.size, v.stock
                FROM product_variants v JOIN products p ON p.id = v.product_id
                WHERE p.slug = ? AND v.color = ? AND v.size = ?""", (slug, color, size)).fetchone()
            return dict(row) if row else None

    def facets(self):
        with self._connect() as db:
            return {
                "categories": [dict(r) for r in db.execute("SELECT category, COUNT(*) AS count FROM products GROUP BY category ORDER BY category")],
                "colors": [r[0] for r in db.execute("SELECT DISTINCT color FROM product_variants ORDER BY color")],
                "sizes": [r[0] for r in db.execute("SELECT DISTINCT size FROM product_variants ORDER BY size")],
                "price_min": db.execute("SELECT MIN(price_vnd) FROM products").fetchone()[0],
                "price_max": db.execute("SELECT MAX(price_vnd) FROM products").fetchone()[0],
            }

    def related(self, slug, limit=4):
        with self._connect() as db:
            current = db.execute("SELECT id, category FROM products WHERE slug = ?", (slug,)).fetchone()
            if not current:
                return []
            rows = db.execute("SELECT * FROM products WHERE category = ? AND id != ? ORDER BY is_bestseller DESC, id DESC LIMIT ?",
                              (current["category"], current["id"], limit)).fetchall()
            return [self._summary(db, row) for row in rows]
