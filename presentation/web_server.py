"""
Presentation Layer — WebServer
Assignment 06: Multimodal E-Commerce Search System.

Acts as a presentation boundary providing an interactive Web UI for:
1. Text Search (UC-02)
2. Voice Search (UC-03)
3. Image Search (UC-04)
4. Order Search (UC-05)

Coordinates with SearchUI without bypassing the three-layer architecture.
"""

import hmac
import json
import mimetypes
import os
import re
import sys
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = Path(BASE_DIR, "web").resolve()
IMAGES_DIR = Path(BASE_DIR, "images").resolve()
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from main import build_system
from application.catalog_service import CatalogService
from application.admin_service import AdminService
from application.commerce_service import CommerceService
from application.search_service import SearchService
from application.visual_search import EncoderError, configured_visual_search
from application.shopping_ai_service import ShoppingAIService
from application.outfit_preview_service import OutfitPreviewService
from data.catalog_repository import CatalogRepository
from data.admin_repository import AdminRepository
from data.commerce_repository import CommerceRepository, CommerceError
from data.catalog_search_repository import CatalogSearchRepository
from data.vector_index import VectorIndex
from data.shopping_ai_repository import ShoppingAIRepository


class MultimodalHTTPHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Multimodal Search Presentation Layer."""

    # System components (injected from server)
    search_ui = None
    result_view = None
    product_repository = None
    order_repository = None
    admin_token = None
    catalog_service = None
    commerce_service = None
    admin_service = None
    visual_search = None
    image_demo_reason = ""
    shopping_ai = None
    outfit_preview = None

    def _set_headers(self, content_type="application/json; charset=utf-8", status_code=200, extra_headers=None):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(status_code=405)

    def _send_json(self, data, status_code=200, headers=None):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._set_headers("application/json; charset=utf-8", status_code, headers)
        self.wfile.write(body)

    def _send_error(self, message, status_code=400):
        self._send_json({"status": "error", "message": str(message)}, status_code=status_code)

    def _read_json_body(self, max_bytes=1024 * 1024):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length < 0 or content_length > max_bytes:
                raise ValueError("JSON payload exceeds the request limit")
            if content_length == 0:
                return {}
            raw_data = self.rfile.read(content_length)
            body = json.loads(raw_data.decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("JSON payload must be an object")
            return body
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Invalid JSON payload: {exc}")

    def _require_admin(self):
        """Protect legacy order APIs until customer accounts exist."""
        if not self.admin_token:
            self._send_error("Order access is not configured on this server.", 503)
            return False
        supplied = self.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(supplied, self.admin_token):
            self._send_error("Administrator access required.", 403)
            return False
        return True

    @staticmethod
    def _static_file(url_path):
        """Resolve only public assets, rejecting traversal and symlink escapes."""
        decoded = unquote(url_path)
        if "\\" in decoded or "\x00" in decoded or any(
            part in (".", "..") for part in decoded.split("/")
        ):
            return None
        if decoded in ("/", "/index.html", "/web/index.html"):
            candidate = (WEB_DIR / "index.html").resolve()
            return candidate if candidate.is_relative_to(WEB_DIR) else None
        if decoded in ("/shop", "/shop.html", "/web/shop.html"):
            candidate = (WEB_DIR / "shop.html").resolve()
            return candidate if candidate.is_relative_to(WEB_DIR) else None
        if decoded in ("/studio", "/studio.html", "/web/studio.html"):
            candidate = (WEB_DIR / "studio.html").resolve()
            return candidate if candidate.is_relative_to(WEB_DIR) else None
        if decoded in ("/product", "/product.html", "/web/product.html"):
            candidate = (WEB_DIR / "product.html").resolve()
            return candidate if candidate.is_relative_to(WEB_DIR) else None
        if decoded in ("/admin", "/admin.html", "/web/admin.html"):
            candidate = (WEB_DIR / "admin.html").resolve()
            return candidate if candidate.is_relative_to(WEB_DIR) else None
        for name in ("account", "cart", "order"):
            if decoded in (f"/{name}", f"/{name}.html", f"/web/{name}.html"):
                candidate = (WEB_DIR / f"{name}.html").resolve()
                return candidate if candidate.is_relative_to(WEB_DIR) else None
        if decoded.startswith("/images/"):
            root = IMAGES_DIR
            relative = decoded[len("/images/"):]
            allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
        else:
            root = WEB_DIR
            relative = decoded[len("/web/"):] if decoded.startswith("/web/") else decoded.lstrip("/")
            allowed = {".css", ".js"}
        if not relative or Path(relative).suffix.lower() not in allowed:
            return None
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root):
            return None
        return candidate

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/admin/"):
            return self._admin_get(path)

        if path == "/api/ai/capabilities":
            return self._send_json({"status": "success", "mode": "provider" if self.shopping_ai.provider.enabled else "demo",
                "label": "AI được cấu hình" if self.shopping_ai.provider.enabled else "DEMO · quy tắc theo dữ liệu COGU"})
        if path == "/api/outfit/catalog":
            return self._send_json({"status": "success", "body_types": self.outfit_preview.BODY_TYPES,
                "genders": self.outfit_preview.GENDERS,
                "categories": self.outfit_preview.CATEGORIES, "products": self.outfit_preview.available_products(),
                "image_mode": "provider" if self.outfit_preview.provider.enabled else "demo",
                "disclaimer": self.outfit_preview.DISCLAIMER})
        if path == "/api/ai/preferences" or path == "/api/ai/recommendations":
            try:
                _, session = self._authenticated()
                customer_id = session["customer_id"]
                if path.endswith("preferences"):
                    return self._send_json({"status": "success", "preferences": self.shopping_ai.repository.preferences(customer_id),
                        "styles": self.shopping_ai.STYLES, "colors": self.shopping_ai.catalog.facets()["colors"]})
                if not self._ai_limit("recommendations", 10, customer_id):
                    return
                return self._send_json({"status": "success", **self.shopping_ai.recommendations(customer_id)})
            except CommerceError as error:
                return self._send_error(str(error), error.status)

        if path == "/api/search/capabilities":
            visual = self.visual_search
            return self._send_json({"status": "success", "image_mode": "encoder" if visual else "demo",
                "image_label": "TÌM THEO NỘI DUNG ẢNH" if visual else "DEMO — ẢNH MẪU",
                "image_notice": f"Ảnh truy vấn và ảnh sản phẩm dùng cùng bộ mã hóa {visual.encoder.model}." if visual else self.image_demo_reason,
                "upload_enabled": bool(visual)})

        if path == "/api/auth/me" or path == "/api/cart" or path.startswith("/api/account/"):
            return self._commerce_get(path, parsed)

        if path == "/api/catalog/products":
            try:
                result = self.catalog_service.list_products(parse_qs(parsed.query, keep_blank_values=True))
            except ValueError as error:
                return self._send_error(str(error), 400)
            return self._send_json({"status": "success", **result})

        if path == "/api/catalog/facets":
            return self._send_json({"status": "success", **self.catalog_service.repository.facets()})

        if path == "/api/promotions":
            return self._send_json({"status": "success", "promotions": self.commerce_service.repository.public_promotions()})

        if path == "/api/catalog/stock":
            params = parse_qs(parsed.query, keep_blank_values=True)
            if any(len(params.get(key, [])) != 1 for key in ("slug", "color", "size")):
                return self._send_error("slug, color and size are required once", 400)
            slug, color, size = (params[key][0] for key in ("slug", "color", "size"))
            if not re.fullmatch(r"[a-z0-9-]{1,100}", slug) or not color or not size or len(color) > 80 or len(size) > 20:
                return self._send_error("Invalid stock selection", 400)
            variant = self.catalog_service.repository.get_variant(slug, color, size)
            if variant is None:
                return self._send_error("Variant not found", 404)
            return self._send_json({"status": "success", "variant": variant})

        if path.startswith("/api/catalog/products/"):
            slug = path.removeprefix("/api/catalog/products/")
            if not re.fullmatch(r"[a-z0-9-]{1,100}", slug):
                return self._send_error("Product not found", 404)
            product = self.catalog_service.repository.get_product(slug)
            if product is None:
                return self._send_error("Product not found", 404)
            related = self.catalog_service.repository.related(slug)
            reviews = self.admin_service.repository.public_reviews(product["id"])
            return self._send_json({"status": "success", "product": product, "related": related, "reviews": reviews})

        # REST API Endpoints
        if path == "/api/products":
            products = self.product_repository.all_products()
            return self._send_json({"status": "success", "count": len(products), "products": products})

        if path == "/api/orders":
            if not self._require_admin():
                return
            orders = self.order_repository.all_orders()
            return self._send_json({"status": "success", "count": len(orders), "orders": orders})

        if path == "/api/system/info":
            return self._send_json({
                "status": "success",
                "system_name": "COGU Fashion Storefront Demo",
                "assignment": "Assignment 06 — Three-Layer Multimodal Architecture",
                "architecture": {
                    "layers": [
                        {
                            "name": "Presentation Layer",
                            "components": ["SearchUI", "VoiceInput", "ImageUpload", "SearchResultView", "WebServer", "Commerce HTTP routes", "Shopping AI HTTP routes", "Outfit Preview HTTP routes"],
                            "responsibility": "Captures user input and presents ranked results. Strictly separates UI from storage."
                        },
                        {
                            "name": "Application / Intelligence Layer",
                            "components": ["QueryService", "SpeechService", "ImageService", "VisualSearch", "SearchService", "RankingService", "CatalogService", "CommerceService", "ShoppingAIService", "OutfitPreviewService"],
                            "responsibility": "Constructs common query representations, carries out candidate retrieval, and performs score ranking."
                        },
                        {
                            "name": "Data Layer",
                            "components": ["ProductRepository", "CatalogRepository", "CatalogSearchRepository", "VisualEmbeddingRepository", "CommerceRepository", "ShoppingAIRepository", "OrderRepository", "VectorIndex"],
                            "responsibility": "Provides JSON search fixtures, SQLite catalogue and commerce persistence, and cosine vector index."
                        }
                    ]
                },
                "modalities": ["Text Search (UC-02)", "Voice Search (UC-03)", "Image Search (UC-04)", "Order Search (UC-05)"],
                "image_search_mode": "configured content encoder" if self.visual_search else "DEMO sample vectors",
                "outfit_preview_mode": "configured image provider" if self.outfit_preview.provider.enabled else "DEMO body-type samples",
                "dataset": {
                    "product_count": len(self.product_repository.all_products()),
                    "catalog_product_count": self.catalog_service.repository.list_products(page_size=1)[0],
                    "order_count": len(self.order_repository.all_orders()),
                    "sample_query_images": [
                        {"path": "images/query_shoes.jpg", "category": "shoes", "demo_embedding": [0.88, 0.12, 0.22]},
                        {"path": "images/query_bag.jpg", "category": "bag", "demo_embedding": [0.12, 0.22, 0.88]},
                        {"path": "images/query_watch.jpg", "category": "watch", "demo_embedding": [0.22, 0.82, 0.12]}
                    ]
                }
            })

        file_path = self._static_file(path)
        if file_path is not None and file_path.is_file():
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self._set_headers(content_type, 200)
                self.wfile.write(content)
            except OSError:
                self._send_error("Error reading file.", 500)
        else:
            self._send_error("Resource not found.", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/admin/"):
            return self._admin_write("POST", path)

        if path in ("/api/ai/chat", "/api/ai/compare"):
            return self._ai_post(path)
        if path == "/api/outfit/preview":
            return self._outfit_post()

        if self._commerce_path(path):
            return self._commerce_write("POST", path)

        if path == "/api/search/order" and not self._require_admin():
            return

        try:
            body = self._read_json_body(8 * 1024 * 1024 if path == "/api/search/image" else 1024 * 1024)
        except ValueError as err:
            return self._send_error(str(err), 400)

        # 1. TEXT SEARCH (UC-02)
        if path == "/api/search/text":
            text = body.get("text", "")
            if not isinstance(text, str) or not text.strip():
                return self._send_error("Search text cannot be empty.", 400)
            text = text.strip()

            try:
                filters = SearchService.validate_filters(body.get("filters"))
                # Capture architectural step outputs
                query_repr = self.search_ui.query_service.text_query(text, filters)
                candidates = self.search_ui.search_service.search(query_repr)
                ranked = self.search_ui.ranking_service.rank(candidates)

                return self._send_json({
                    "status": "success",
                    "modality": "text",
                    "input": text,
                    "pipeline": {
                        "step_1_input": {"component": "SearchUI", "input_type": "text", "raw_value": text},
                        "step_2_query": {"component": "QueryService", "method": "text_query", "representation": query_repr},
                        "step_3_retrieval": {
                            "component": "SearchService",
                            "method": "search_text (Vietnamese accent folding, attributes, filters and weighted relevance)",
                            "candidates_count": len(candidates)
                        },
                        "step_4_ranking": {"component": "RankingService", "method": "descending score ordering", "ranked_count": len(ranked)},
                        "step_5_presentation": {"component": "SearchResultView", "action": "display_ranked_results"}
                    },
                    "total_candidates": len(candidates),
                    "results": ranked
                })
            except ValueError as exc:
                return self._send_error(str(exc), 400)
            except Exception as exc:
                return self._send_error(f"Text search error: {exc}", 500)

        # 2. VOICE SEARCH (UC-03)
        if path == "/api/search/voice":
            audio_input = body.get("audio_input", "")
            if not isinstance(audio_input, str) or not audio_input.strip():
                return self._send_error("Voice audio input cannot be empty.", 400)
            audio_input = audio_input.strip()

            try:
                filters = SearchService.validate_filters(body.get("filters"))
                # Step 1: VoiceInput captures simulated audio / speech transcript
                transcribed = self.search_ui.voice_input.capture(audio_input)
                # Step 2: QueryService creates common query representation
                query_repr = self.search_ui.query_service.voice_query(transcribed, filters)
                # Step 3: SearchService retrieves candidate products
                candidates = self.search_ui.search_service.search(query_repr)
                # Step 4: RankingService orders candidates by score
                ranked = self.search_ui.ranking_service.rank(candidates)

                return self._send_json({
                    "status": "success",
                    "modality": "voice",
                    "input": audio_input,
                    "transcribed": transcribed,
                    "pipeline": {
                        "step_1_voice_capture": {"component": "VoiceInput", "action": "receive browser/manual transcript", "audio_input": audio_input},
                        "step_2_transcribe": {"component": "SpeechService", "action": "validate transcript (no backend audio recognition)", "transcript": transcribed},
                        "step_3_query": {"component": "QueryService", "method": "voice_query", "representation": query_repr},
                        "step_4_retrieval": {
                            "component": "SearchService",
                            "method": "search_text (accent folding, attributes, filters and weighted relevance)",
                            "candidates_count": len(candidates)
                        },
                        "step_5_ranking": {"component": "RankingService", "method": "descending score ordering", "ranked_count": len(ranked)},
                        "step_6_presentation": {"component": "SearchResultView", "action": "display_ranked_results"}
                    },
                    "total_candidates": len(candidates),
                    "results": ranked
                })
            except ValueError as exc:
                return self._send_error(str(exc), 400)
            except Exception as exc:
                return self._send_error(f"Voice search error: {exc}", 500)

        # 3. IMAGE SEARCH (UC-04)
        if path == "/api/search/image":
            image_path = body.get("image_path")
            image_vector = body.get("image_vector")
            image_data = body.get("image_data")

            try:
                filters = SearchService.validate_filters(body.get("filters"))
                if self.visual_search:
                    if image_vector is not None:
                        raise ValueError("Direct vectors are only available in DEMO sample mode.")
                    embedding = self.visual_search.query(image_path=image_path, image_data=image_data)
                    display_input = "Ảnh tải lên" if image_data is not None else image_path
                    mode = "encoder"
                    action = f"encode image bytes with {self.visual_search.encoder.model}"
                else:
                    if image_data is not None:
                        raise ValueError("DEMO mode only supports the three labeled sample images; uploads need a configured image encoder.")
                    if image_vector is not None:
                        target_input = image_vector
                        display_input = "Vector mẫu do API cung cấp"
                    elif image_path in ("images/query_shoes.jpg", "images/query_bag.jpg", "images/query_watch.jpg"):
                        target_input = image_path
                        display_input = image_path
                    else:
                        raise ValueError("DEMO mode only supports the three labeled sample images.")
                    embedding = self.search_ui.image_upload.upload(target_input)
                    mode = "demo"
                    action = "deterministic sample vector (DEMO; no image-content recognition)"
                # Step 2: QueryService creates common query representation
                query_repr = self.search_ui.query_service.image_query(embedding, filters)
                # Step 3: SearchService retrieves candidates via VectorIndex cosine similarity
                candidates = self.search_ui.search_service.search(query_repr)
                # Step 4: RankingService sorts candidates by similarity
                ranked = self.search_ui.ranking_service.rank(candidates)

                return self._send_json({
                    "status": "success",
                    "modality": "image",
                    "input": display_input,
                    "image_mode": mode,
                    "image_label": "TÌM THEO NỘI DUNG ẢNH" if mode == "encoder" else "DEMO — ẢNH MẪU",
                    "embedding": embedding,
                    "pipeline": {
                        "step_1_image_upload": {"component": "ImageUpload", "action": "read image bytes" if mode == "encoder" else "select sample vector", "image_input": display_input},
                        "step_2_image_service": {"component": "ImageService", "action": action, "embedding": embedding},
                        "step_3_query": {"component": "QueryService", "method": "image_query", "representation": query_repr},
                        "step_4_retrieval": {
                            "component": "SearchService + VectorIndex",
                            "method": "cosine vector similarity across all product embeddings",
                            "candidates_count": len(candidates)
                        },
                        "step_5_ranking": {"component": "RankingService", "method": "descending similarity score ordering", "ranked_count": len(ranked)},
                        "step_6_presentation": {"component": "SearchResultView", "action": "display_ranked_results"}
                    },
                    "total_candidates": len(candidates),
                    "results": ranked
                })
            except ValueError as exc:
                return self._send_error(str(exc), 400)
            except EncoderError:
                return self._send_error("Configured image encoder is unavailable; please retry later.", 502)
            except Exception:
                return self._send_error("Image search failed.", 500)

        # 4. ORDER SEARCH (UC-05)
        if path == "/api/search/order":
            order_id = body.get("order_id", "")
            if not isinstance(order_id, str) or not order_id.strip():
                return self._send_error("Order ID cannot be empty.", 400)
            order_id = order_id.strip()

            try:
                order = self.search_ui.order_search(order_id)
                return self._send_json({
                    "status": "success",
                    "modality": "order",
                    "order_id": order_id,
                    "order": order,
                    "found": order is not None,
                    "pipeline": {
                        "step_1_search_ui": {"component": "SearchUI", "action": "order_search", "order_id": order_id},
                        "step_2_search_service": {"component": "SearchService", "action": "search_order"},
                        "step_3_repository": {"component": "OrderRepository", "action": "find_order"}
                    }
                })
            except Exception as exc:
                return self._send_error(f"Order search error: {exc}", 500)

        # Unrecognized endpoint
        self._send_error(f"Invalid POST endpoint: {path}", 404)

    @staticmethod
    def _commerce_path(path):
        return path.startswith(("/api/auth/", "/api/account/")) or path == "/api/cart" or path.startswith("/api/cart/") or path == "/api/checkout"

    def _session_token(self):
        try:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            return cookie["cogu_session"].value if "cogu_session" in cookie else ""
        except Exception:
            return ""

    def _authenticated(self, csrf=False):
        token = self._session_token()
        session = self.commerce_service.session(token)
        if not session:
            raise CommerceError("Vui lòng đăng nhập để tiếp tục.", 401)
        if csrf:
            self.commerce_service.require_csrf(session, self.headers.get("X-CSRF-Token", ""))
        return token, session

    @staticmethod
    def _session_cookie(token, clear=False):
        value = f"cogu_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={0 if clear else 604800}"
        if os.environ.get("COGU_COOKIE_SECURE") == "1":
            value += "; Secure"
        return value

    def _commerce_get(self, path, parsed):
        try:
            _, session = self._authenticated()
            customer_id = session["customer_id"]
            repository = self.commerce_service.repository
            if path == "/api/auth/me":
                return self._send_json({"status": "success", **self.commerce_service.public_session(session)})
            if path == "/api/account/addresses":
                return self._send_json({"status": "success", "addresses": repository.list_addresses(customer_id)})
            if path == "/api/account/wishlist":
                return self._send_json({"status": "success", "products": repository.list_wishlist(customer_id)})
            if path == "/api/account/reviews":
                return self._send_json({"status": "success", "reviews": self.admin_service.repository.list_customer_reviews(customer_id),
                                        "eligible_product_ids": self.admin_service.repository.review_eligible_products(customer_id),
                                        "reviewable_products": self.admin_service.repository.list_reviewable_products(customer_id)})
            if path == "/api/account/support":
                return self._send_json({"status": "success", "requests": self.admin_service.repository.list_customer_support(customer_id)})
            if path == "/api/cart":
                params = parse_qs(parsed.query, keep_blank_values=True)
                codes = params.get("promotion_code", [""])
                if len(codes) != 1:
                    raise CommerceError("Mã ưu đãi không hợp lệ.")
                return self._send_json({"status": "success", "cart": self.commerce_service.cart(customer_id, codes[0])})
            if path == "/api/account/orders":
                return self._send_json({"status": "success", "orders": repository.list_orders(customer_id)})
            match = re.fullmatch(r"/api/account/orders/(COGU-\d{8}-[A-F0-9]{12})", path)
            if match:
                order = repository.get_order(customer_id, match.group(1))
                if order is None:
                    raise CommerceError("Không tìm thấy đơn hàng.", 404)
                return self._send_json({"status": "success", "order": order})
            raise CommerceError("Không tìm thấy tài nguyên.", 404)
        except CommerceError as error:
            return self._send_error(str(error), error.status)

    def do_PUT(self):
        path = urlparse(self.path).path
        if path.startswith("/api/admin/"):
            return self._admin_write("PUT", path)
        if path == "/api/ai/preferences":
            return self._ai_preferences_write()
        return self._commerce_write("PUT", path) if self._commerce_path(path) else self._send_error("Resource not found.", 404)

    def _ai_limit(self, feature, limit, customer_id=None):
        actor = "customer:%s" % customer_id if customer_id else "ip:%s" % self.client_address[0]
        if self.shopping_ai.repository.consume(actor, feature, limit):
            return True
        self._send_error("Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau một phút.", 429)
        return False

    def _ai_post(self, path):
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise CommerceError("Yêu cầu phải dùng JSON.", 415)
            session = self.commerce_service.session(self._session_token())
            customer_id = session["customer_id"] if session else None
            if session:
                self.commerce_service.require_csrf(session, self.headers.get("X-CSRF-Token", ""))
            feature = "chat" if path.endswith("chat") else "compare"
            if not self._ai_limit(feature, 20 if feature == "chat" else 10, customer_id):
                return
            body = self._read_json_body(8192)
            result = self.shopping_ai.chat(body.get("message"), customer_id) if feature == "chat" else self.shopping_ai.compare(body.get("product_ids"))
            return self._send_json({"status": "success", **result})
        except CommerceError as error:
            return self._send_error(str(error), error.status)
        except ValueError as error:
            return self._send_error(str(error), 400)

    def _ai_preferences_write(self):
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise CommerceError("Yêu cầu phải dùng JSON.", 415)
            _, session = self._authenticated(csrf=True)
            body = self._read_json_body(8192)
            preferences = self.shopping_ai.validate_preferences(body)
            return self._send_json({"status": "success", "preferences": self.shopping_ai.repository.save_preferences(session["customer_id"], preferences)})
        except CommerceError as error:
            return self._send_error(str(error), error.status)
        except ValueError as error:
            return self._send_error(str(error), 400)

    def _outfit_post(self):
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise CommerceError("Yêu cầu phải dùng JSON.", 415)
            session = self.commerce_service.session(self._session_token())
            customer_id = session["customer_id"] if session else None
            if session:
                self.commerce_service.require_csrf(session, self.headers.get("X-CSRF-Token", ""))
            if not self._ai_limit("outfit", 3, customer_id):
                return
            body = self._read_json_body(8192)
            return self._send_json({"status": "success", **self.outfit_preview.preview(body)})
        except CommerceError as error:
            return self._send_error(str(error), error.status)
        except ValueError as error:
            return self._send_error(str(error), 400)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/admin/"):
            return self._admin_write("DELETE", path)
        return self._commerce_write("DELETE", path) if self._commerce_path(path) else self._send_error("Resource not found.", 404)

    def _commerce_write(self, method, path):
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json" and method != "DELETE":
                raise CommerceError("Yêu cầu phải dùng JSON.", 415)
            body = self._read_json_body()
            service = self.commerce_service
            if method == "POST" and path in ("/api/auth/register", "/api/auth/login"):
                token, public = service.register(body) if path.endswith("register") else service.login(body)
                return self._send_json({"status": "success", **public}, 201 if path.endswith("register") else 200,
                                       {"Set-Cookie": self._session_cookie(token)})
            token, session = self._authenticated(csrf=True)
            customer_id = session["customer_id"]
            repository = service.repository
            if method == "POST" and path == "/api/auth/logout":
                service.logout(token)
                return self._send_json({"status": "success"}, headers={"Set-Cookie": self._session_cookie("", True)})
            if method == "PUT" and path == "/api/account/profile":
                return self._send_json({"status": "success", "customer": service.update_profile(customer_id, body)})
            if method == "POST" and path == "/api/account/addresses":
                return self._send_json({"status": "success", "address": service.save_address(customer_id, body)}, 201)
            match = re.fullmatch(r"/api/account/addresses/(\d+)", path)
            if match and method in ("PUT", "DELETE"):
                address_id = service._integer(int(match.group(1)), "Mã địa chỉ")
                if method == "PUT":
                    return self._send_json({"status": "success", "address": service.save_address(customer_id, body, address_id)})
                repository.delete_address(customer_id, address_id)
                return self._send_json({"status": "success"})
            if method == "POST" and path == "/api/account/wishlist":
                return self._send_json({"status": "success", "products": service.set_wishlist(customer_id, body, True)})
            if method == "POST" and path == "/api/account/reviews":
                return self._send_json({"status": "success", "review": self.admin_service.create_review(customer_id, body)}, 201)
            if method == "POST" and path == "/api/account/support":
                return self._send_json({"status": "success", "request": self.admin_service.create_support_request(customer_id, body)}, 201)
            match = re.fullmatch(r"/api/account/wishlist/(\d+)", path)
            if method == "DELETE" and match:
                return self._send_json({"status": "success", "products": service.set_wishlist(customer_id, {"product_id": int(match.group(1))}, False)})
            if method == "POST" and path == "/api/cart":
                return self._send_json({"status": "success", "cart": service.add_cart(customer_id, body)})
            if method == "PUT" and path == "/api/cart":
                return self._send_json({"status": "success", "cart": service.set_cart(customer_id, body)})
            match = re.fullmatch(r"/api/cart/(\d+)", path)
            if method == "DELETE" and match:
                return self._send_json({"status": "success", "cart": service.set_cart(customer_id, {"variant_id": int(match.group(1)), "quantity": 0})})
            if method == "POST" and path == "/api/checkout":
                order, duplicate = service.checkout(customer_id, body)
                return self._send_json({"status": "success", "order": order, "duplicate": duplicate}, 200 if duplicate else 201)
            raise CommerceError("Không tìm thấy tài nguyên.", 404)
        except CommerceError as error:
            return self._send_error(str(error), error.status)
        except ValueError as error:
            return self._send_error(str(error), 400)

    def _staff_token(self):
        try:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            return cookie["cogu_staff_session"].value if "cogu_staff_session" in cookie else ""
        except Exception:
            return ""

    @staticmethod
    def _staff_cookie(token, clear=False):
        value = f"cogu_staff_session={token}; HttpOnly; SameSite=Strict; Path=/api/admin; Max-Age={0 if clear else 43200}"
        if os.environ.get("COGU_COOKIE_SECURE") == "1":
            value += "; Secure"
        return value

    def _staff_authenticated(self, csrf=False):
        token = self._staff_token()
        session = self.admin_service.session(token)
        if not session:
            raise CommerceError("Vui lòng đăng nhập tài khoản nhân viên.", 401)
        if csrf:
            self.admin_service.require_csrf(session, self.headers.get("X-CSRF-Token", ""))
        return token, session

    @staticmethod
    def _admin_id(value):
        number = int(value)
        if number < 1 or number > 2**31 - 1:
            raise CommerceError("Mã bản ghi không hợp lệ.", 404)
        return number

    def _admin_get(self, path):
        try:
            _, session = self._staff_authenticated()
            service = self.admin_service
            repo = service.repository
            if path == "/api/admin/session":
                return self._send_json({"status": "success", **service.public_session(session)})
            routes = {
                "/api/admin/dashboard": ("dashboard", "dashboard", "dashboard"),
                "/api/admin/reports": ("reports", "reports", "reports"),
                "/api/admin/products": ("products.read", "products", "list_admin_products"),
                "/api/admin/orders": ("orders.read", "orders", "list_admin_orders"),
                "/api/admin/promotions": ("promotions.read", "promotions", "list_promotions"),
                "/api/admin/reviews": ("reviews.read", "reviews", "list_admin_reviews"),
                "/api/admin/support": ("support.read", "requests", "list_admin_support"),
                "/api/admin/staff": ("staff.read", "staff", "list_staff"),
            }
            if path in routes:
                permission, key, method = routes[path]
                service.require(session, permission)
                return self._send_json({"status": "success", key: getattr(repo, method)()})
            match = re.fullmatch(r"/api/admin/products/(\d+)", path)
            if match:
                service.require(session, "products.read")
                product = repo.get_admin_product(self._admin_id(match.group(1)))
                if product is None:
                    raise CommerceError("Không tìm thấy sản phẩm.", 404)
                return self._send_json({"status": "success", "product": product})
            match = re.fullmatch(r"/api/admin/orders/(COGU-\d{8}-[A-F0-9]{12})", path)
            if match:
                service.require(session, "orders.read")
                order = repo.get_admin_order(match.group(1))
                if order is None:
                    raise CommerceError("Không tìm thấy đơn hàng.", 404)
                return self._send_json({"status": "success", "order": order})
            raise CommerceError("Không tìm thấy tài nguyên quản trị.", 404)
        except CommerceError as error:
            return self._send_error(str(error), error.status)

    def _refresh_search_index(self):
        search_service = self.search_ui.search_service
        if self.visual_search:
            try:
                self.visual_search.refresh()
                search_service.repository.all_products()
                search_service.vector_index = self.visual_search.index
                return
            except (ValueError, EncoderError) as error:
                self.__class__.visual_search = None
                self.__class__.image_demo_reason = f"DEMO — bộ mã hóa ảnh không khả dụng ({error}). Chỉ dùng ảnh mẫu."
        search_service.vector_index = VectorIndex(search_service.repository)

    def _admin_write(self, method, path):
        try:
            if method != "DELETE" and self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise CommerceError("Yêu cầu quản trị phải dùng JSON.", 415)
            body = self._read_json_body()
            service = self.admin_service
            repo = service.repository
            if method == "POST" and path == "/api/admin/login":
                token, public = service.login(body)
                return self._send_json({"status": "success", **public}, headers={"Set-Cookie": self._staff_cookie(token)})
            token, session = self._staff_authenticated(csrf=True)
            staff_id = session["staff_id"]
            if method == "POST" and path == "/api/admin/logout":
                service.logout(token)
                return self._send_json({"status": "success"}, headers={"Set-Cookie": self._staff_cookie("", True)})
            if method == "POST" and path == "/api/admin/staff":
                return self._send_json({"status": "success", "staff": service.create_staff(session, body)}, 201)
            match = re.fullmatch(r"/api/admin/staff/(\d+)", path)
            if method == "PUT" and match:
                return self._send_json({"status": "success", "staff": service.update_staff(session, self._admin_id(match.group(1)), body)})
            if method == "POST" and path == "/api/admin/products":
                service.require(session, "products.write")
                product = repo.save_product(staff_id, service.product_fields(body))
                self._refresh_search_index()
                return self._send_json({"status": "success", "product": product}, 201)
            match = re.fullmatch(r"/api/admin/products/(\d+)", path)
            if match and method in ("PUT", "DELETE"):
                service.require(session, "products.write")
                product_id = self._admin_id(match.group(1))
                if method == "PUT":
                    product = repo.save_product(staff_id, service.product_fields(body), product_id)
                    self._refresh_search_index()
                    return self._send_json({"status": "success", "product": product})
                repo.delete_product(staff_id, product_id)
                self._refresh_search_index()
                return self._send_json({"status": "success"})
            match = re.fullmatch(r"/api/admin/products/(\d+)/variants", path)
            if method == "POST" and match:
                service.require(session, "variants.write")
                variant = repo.save_variant(staff_id, self._admin_id(match.group(1)), service.variant_fields(body))
                self._refresh_search_index()
                return self._send_json({"status": "success", "variant": variant}, 201)
            match = re.fullmatch(r"/api/admin/variants/(\d+)", path)
            if match and method in ("PUT", "DELETE"):
                service.require(session, "variants.write")
                variant_id = self._admin_id(match.group(1))
                if method == "DELETE":
                    repo.delete_variant(staff_id, variant_id)
                    self._refresh_search_index()
                    return self._send_json({"status": "success"})
                current = repo.variant(variant_id)
                if current is None:
                    raise CommerceError("Không tìm thấy phiên bản.", 404)
                variant = repo.save_variant(staff_id, current["product_id"], service.variant_fields(body), variant_id)
                self._refresh_search_index()
                return self._send_json({"status": "success", "variant": variant})
            match = re.fullmatch(r"/api/admin/variants/(\d+)/stock", path)
            if method == "PUT" and match:
                service.require(session, "variants.write")
                stock = service._integer(body.get("stock"), "Tồn kho", 0, 100000)
                note = service._string(body.get("note"), "Lý do cập nhật", 5, 240)
                variant = repo.set_stock(staff_id, self._admin_id(match.group(1)), stock, note)
                self._refresh_search_index()
                return self._send_json({"status": "success", "variant": variant})
            if method == "POST" and path == "/api/admin/promotions":
                service.require(session, "promotions.write")
                return self._send_json({"status": "success", "promotion": repo.save_promotion(staff_id, service.promotion_fields(body))}, 201)
            match = re.fullmatch(r"/api/admin/promotions/([A-Z0-9_-]{3,20})", path)
            if match and method in ("PUT", "DELETE"):
                service.require(session, "promotions.write")
                code = match.group(1)
                if method == "DELETE":
                    repo.delete_promotion(staff_id, code)
                    return self._send_json({"status": "success"})
                return self._send_json({"status": "success", "promotion": repo.save_promotion(staff_id, service.promotion_fields(body, code), code)})
            match = re.fullmatch(r"/api/admin/orders/(COGU-\d{8}-[A-F0-9]{12})/(status|shipment|payment)", path)
            if method == "PUT" and match:
                return self._send_json({"status": "success", "order": service.order_change(session, match.group(1), match.group(2), body)})
            match = re.fullmatch(r"/api/admin/reviews/(\d+)", path)
            if method == "PUT" and match:
                return self._send_json({"status": "success", "review": service.moderate_review(session, self._admin_id(match.group(1)), body)})
            match = re.fullmatch(r"/api/admin/support/(\d+)", path)
            if method == "PUT" and match:
                return self._send_json({"status": "success", "request": service.update_support(session, self._admin_id(match.group(1)), body)})
            raise CommerceError("Không tìm thấy tài nguyên quản trị.", 404)
        except CommerceError as error:
            return self._send_error(str(error), error.status)
        except ValueError as error:
            return self._send_error(str(error), 400)


def create_web_server(port=8080, host="127.0.0.1"):
    """Initialize system services and return configured HTTPServer instance."""
    search_ui, result_view, product_repository, order_repository = build_system()

    # A distinct handler class keeps per-server configuration isolated.
    class ConfiguredHandler(MultimodalHTTPHandler):
        pass

    ConfiguredHandler.search_ui = search_ui
    ConfiguredHandler.result_view = result_view
    ConfiguredHandler.product_repository = product_repository
    ConfiguredHandler.order_repository = order_repository
    ConfiguredHandler.admin_token = os.environ.get("COGU_ADMIN_TOKEN") or None
    catalog_repository = CatalogRepository()
    ConfiguredHandler.catalog_service = CatalogService(catalog_repository)
    ConfiguredHandler.commerce_service = CommerceService(CommerceRepository(catalog_repository.db_path))
    ConfiguredHandler.admin_service = AdminService(AdminRepository(catalog_repository.db_path), IMAGES_DIR)
    ConfiguredHandler.shopping_ai = ShoppingAIService(catalog_repository,
        ConfiguredHandler.commerce_service.repository, ShoppingAIRepository(catalog_repository.db_path))
    ConfiguredHandler.outfit_preview = OutfitPreviewService(catalog_repository, IMAGES_DIR)
    # Keep the legacy JSON endpoint/console fixture, but search all shop items on the web.
    catalog_search = CatalogSearchRepository(catalog_repository, product_repository)
    search_ui.search_service.repository = catalog_search
    visual, reason = configured_visual_search(catalog_repository, IMAGES_DIR)
    ConfiguredHandler.visual_search = visual
    ConfiguredHandler.image_demo_reason = reason
    search_ui.search_service.vector_index = visual.index if visual else VectorIndex(catalog_search)

    server = ThreadingHTTPServer((host, port), ConfiguredHandler)
    return server
