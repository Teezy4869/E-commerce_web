"""Apply the three-category catalogue update to an existing SQLite store.

Creates a SQLite backup first. Existing shirt, trouser and shoe records, stock,
customers and order snapshots are kept. Run after updating catalog_seed.json.
"""

import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.catalog_models import CATALOG_CATEGORIES  # noqa: E402
from data.catalog_repository import DEFAULT_DB, SEED  # noqa: E402


def sync(db_path=None, seed_path=SEED):
    target = Path(db_path or os.environ.get("COGU_CATALOG_DB") or DEFAULT_DB).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"Catalogue database not found: {target}")
    products = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    if len(products) != 38 or {item["category"] for item in products} != CATALOG_CATEGORIES:
        raise ValueError("Expected the 38-product, three-category catalogue seed.")

    backup_dir = target.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"{target.stem}-before-three-categories-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3"
    with closing(sqlite3.connect(target, timeout=15)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with closing(sqlite3.connect(backup_path)) as backup:
            db.backup(backup)
        try:
            db.execute("BEGIN IMMEDIATE")
            removed = db.execute("DELETE FROM products WHERE category NOT IN ('shirt', 'trousers', 'shoes')").rowcount
            added = 0
            for product in products:
                row = db.execute("SELECT slug FROM products WHERE id = ?", (product["id"],)).fetchone()
                if row:
                    if row[0] != product["slug"]:
                        raise ValueError(f"Product ID {product['id']} is already used by another product.")
                    continue
                if db.execute("SELECT 1 FROM products WHERE slug = ?", (product["slug"],)).fetchone():
                    raise ValueError(f"Product slug {product['slug']} is already used by another ID.")
                db.execute("""INSERT INTO products
                    (id, slug, name_vi, description_vi, category, material, price_vnd, image, is_new, is_bestseller)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuple(product[key] for key in ("id", "slug", "name_vi", "description_vi", "category",
                                                    "material", "price_vnd", "image", "is_new", "is_bestseller")))
                db.executemany("INSERT INTO product_images(product_id, color, image, position) VALUES (?, ?, ?, ?)",
                               [(product["id"], image["color"], image["image"], index)
                                for index, image in enumerate(product["images"])])
                db.executemany("""INSERT INTO product_variants(id, product_id, sku, color, size, stock)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    [(variant["id"], product["id"], variant["sku"], variant["color"], variant["size"], variant["stock"])
                     for variant in product["variants"]])
                added += 1
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Catalogue update would violate a foreign key.")
            db.commit()
        except Exception:
            db.rollback()
            raise
        counts = dict(db.execute("SELECT category, COUNT(*) FROM products GROUP BY category"))
    return {"added": added, "removed": removed, "counts": counts, "backup": str(backup_path)}


if __name__ == "__main__":
    print(sync())
