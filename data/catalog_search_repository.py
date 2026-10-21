"""Read-only adapter exposing SQLite products to the existing search services.

The original JSON ProductRepository and its test fixtures stay unchanged.
Image vectors for added catalogue items are deterministic category demo vectors;
they are not visual embeddings computed from image pixels.
"""


CATEGORY_VECTORS = {
    "shoes": [0.82, 0.14, 0.22],
    "shirt": [0.43, 0.13, 0.58],
    "trousers": [0.42, 0.15, 0.55],
}


class CatalogSearchRepository:
    def __init__(self, catalog_repository, legacy_repository):
        self.catalog = catalog_repository
        self.legacy = {item["id"]: item for item in legacy_repository.all_products()}
        self._by_id = {}

    def all_products(self):
        total, products = self.catalog.list_products(page_size=48)
        for page in range(2, (total + 47) // 48 + 1):
            _, more = self.catalog.list_products(page=page, page_size=48)
            products.extend(more)
        adapted = []
        for item in products:
            legacy = self.legacy.get(item["id"], {})
            adapted.append({
                **item,
                "name": legacy.get("name", item["name_vi"]),
                "description": legacy.get("description", item["description_vi"]),
                "color": " ".join(item["colors"]) + (" " + legacy["color"] if legacy else ""),
                "embedding": legacy.get("embedding", CATEGORY_VECTORS[item["category"]]),
            })
        self._by_id = {item["id"]: item for item in adapted}
        return adapted

    def get_by_id(self, product_id):
        if not self._by_id:
            self.all_products()
        return self._by_id.get(product_id)
