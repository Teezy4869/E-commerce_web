"""Candidate retrieval for the original three search modalities."""

import re
import unicodedata


def fold_text(value):
    """Fold Vietnamese accents (including đ) and split punctuation consistently."""
    value = str(value).casefold().replace("đ", "d")
    value = "".join(char for char in unicodedata.normalize("NFD", value)
                    if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", value))


class SearchService:
    """Retrieve catalogue candidates; RankingService keeps final ordering."""

    STOP_WORDS = {"tim", "kiem", "cho", "toi", "muon", "mot", "loai", "va", "voi",
                  "find", "show", "me", "the", "a", "an", "please"}
    CATEGORY_NAMES = {
        "shirt": "ao ao thun shirt top tee",
        "trousers": "quan trousers pants jean jeans",
        "shoes": "giay shoes shoe sneaker sneakers",
        "bag": "tui tui xach bag handbag",
        "jacket": "ao khoac jacket coat",
        "watch": "dong ho watch watches",
    }
    CATEGORIES = frozenset(CATEGORY_NAMES)

    def __init__(self, product_repository, vector_index=None, order_repository=None):
        self.repository = product_repository
        self.vector_index = vector_index
        self.order_repository = order_repository

    @classmethod
    def validate_filters(cls, filters):
        if filters is None:
            return {}
        if not isinstance(filters, dict) or set(filters) - {"category", "color", "size", "material", "min_price", "max_price"}:
            raise ValueError("invalid search filters")
        result = {}
        for key in ("category", "color", "size", "material"):
            value = filters.get(key)
            if value is None or value == "":
                continue
            if not isinstance(value, str) or len(value.strip()) > 80:
                raise ValueError(f"invalid {key} filter")
            result[key] = value.strip()
        if "category" in result and result["category"] not in cls.CATEGORIES:
            raise ValueError("unknown category filter")
        for key in ("min_price", "max_price"):
            value = filters.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000000000:
                raise ValueError(f"invalid {key} filter")
            result[key] = value
        if result.get("min_price", 0) > result.get("max_price", 1000000000):
            raise ValueError("minimum price exceeds maximum price")
        return result

    @staticmethod
    def _matches_filters(product, filters):
        if filters.get("category") and product.get("category") != filters["category"]:
            return False
        if filters.get("color") and fold_text(filters["color"]) not in fold_text(" ".join(product.get("colors", [])) or product.get("color", "")):
            return False
        if filters.get("size") and fold_text(filters["size"]) not in {fold_text(v) for v in product.get("sizes", [])}:
            return False
        if filters.get("material") and fold_text(filters["material"]) not in fold_text(product.get("material", "")):
            return False
        price = product.get("price_vnd")
        if "min_price" in filters and (price is None or price < filters["min_price"]):
            return False
        if "max_price" in filters and (price is None or price > filters["max_price"]):
            return False
        return True

    def search(self, query):
        if not isinstance(query, dict):
            raise ValueError("query must be a dictionary")
        query_type = query.get("type")
        if query_type in ("text", "voice"):
            return self.search_text(query.get("query"), query.get("filters"))
        if query_type == "image":
            return self.search_image(query.get("embedding"), query.get("filters"))
        raise ValueError(f"unsupported query type: {query_type!r}")

    def search_text(self, query, filters=None):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("text query must be a non-empty string")
        if len(query) > 240:
            raise ValueError("text query is too long")
        filters = self.validate_filters(filters)
        normalized = fold_text(query)
        words = list(dict.fromkeys(word for word in normalized.split() if word not in self.STOP_WORDS))
        if not words:
            return []
        results = []
        for product in self.repository.all_products():
            if not self._matches_filters(product, filters):
                continue
            name = fold_text(" ".join((product.get("name", ""), product.get("name_vi", ""))))
            category = fold_text(self.CATEGORY_NAMES.get(product.get("category"), product.get("category", "")))
            color = fold_text(" ".join(product.get("colors", [])) + " " + str(product.get("color", "")))
            material = fold_text(product.get("material", ""))
            sizes = fold_text(" ".join(product.get("sizes", [])))
            description = fold_text(" ".join((product.get("description", ""), product.get("description_vi", ""))))
            fields = [(set(name.split()), 4), (set(category.split()), 3), (set(color.split()), 2),
                      (set(material.split()), 2), (set(sizes.split()), 2), (set(description.split()), 1)]
            term_scores = [max((weight for tokens, weight in fields if word in tokens), default=0) for word in words]
            matched = sum(score > 0 for score in term_scores)
            if not matched:
                continue
            if matched == 1 and len(words) > 1:
                score = 1
            else:
                score = sum(term_scores) + matched / len(words)
                if len(words) > 1 and normalized in name:
                    score += 6
            results.append((product, score))
        return sorted(results, key=lambda item: (-item[1], item[0].get("id", 0)))

    def search_image(self, query_embedding, filters=None):
        if self.vector_index is None:
            raise RuntimeError("image search requires a VectorIndex")
        filters = self.validate_filters(filters)
        results = []
        for product_id, similarity in self.vector_index.search_similar(query_embedding):
            product = self.repository.get_by_id(product_id)
            if product is not None and self._matches_filters(product, filters):
                results.append((product, similarity))
        return results

    def search_order(self, order_id):
        if self.order_repository is None:
            raise RuntimeError("order search requires an OrderRepository")
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("order_id must be a non-empty string")
        return self.order_repository.find_order(order_id.strip())
