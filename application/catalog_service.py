"""Catalogue query validation and use cases for the Presentation layer."""

from data.catalog_models import CATALOG_CATEGORIES


class CatalogService:
    SORTS = {"newest", "popular", "price_asc", "price_desc", "name"}
    CATEGORIES = CATALOG_CATEGORIES

    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _integer(value, name, low, high):
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer") from None
        if not low <= number <= high:
            raise ValueError(f"{name} must be between {low} and {high}")
        return number

    def list_products(self, params):
        def one(name):
            values = params.get(name, [])
            if len(values) > 1:
                raise ValueError(f"Repeated {name} parameter")
            return values[0].strip() if values else ""

        category, color, size, query = (one(name) for name in ("category", "color", "size", "q"))
        sort = one("sort") or "newest"
        if category and category not in self.CATEGORIES:
            raise ValueError("Unknown category")
        if sort not in self.SORTS:
            raise ValueError("Unknown sort order")
        if any(len(v) > 80 for v in (color, size, query)):
            raise ValueError("Filter is too long")
        page = self._integer(one("page") or 1, "page", 1, 10000)
        page_size = self._integer(one("page_size") or 12, "page_size", 1, 48)
        min_price = self._integer(one("min_price"), "min_price", 0, 1000000000) if one("min_price") else None
        max_price = self._integer(one("max_price"), "max_price", 0, 1000000000) if one("max_price") else None
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValueError("min_price cannot exceed max_price")
        total, products = self.repository.list_products(
            category=category or None, color=color or None, size=size or None,
            min_price=min_price, max_price=max_price, query=query or None,
            sort=sort, page=page, page_size=page_size)
        return {"products": products, "total": total, "page": page,
                "page_size": page_size, "pages": (total + page_size - 1) // page_size}
