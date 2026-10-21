"""Typed catalogue records. Inventory belongs to a color/size SKU, not a product."""

from dataclasses import dataclass

CATALOG_CATEGORIES = frozenset({"shirt", "trousers", "shoes"})


@dataclass(frozen=True)
class Product:
    id: int
    slug: str
    name_vi: str
    description_vi: str
    category: str
    material: str
    price_vnd: int
    image: str
    is_new: bool = False
    is_bestseller: bool = False


@dataclass(frozen=True)
class ProductVariant:
    id: int
    product_id: int
    sku: str
    color: str
    size: str
    stock: int
