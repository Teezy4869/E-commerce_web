"""Catalogue-grounded simulated outfit previews with an explicit sample fallback."""

import base64
import binascii
import json
import os
import re
import secrets
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from application.visual_search import image_mime


class OutfitProviderError(RuntimeError):
    def __init__(self, message, code="unavailable"):
        super().__init__(message)
        self.code = code


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise OutfitProviderError("Image provider redirects are not supported.")


class OutfitImageProvider:
    """Configured JSON image-generation endpoint; no browser credential exposure."""

    def __init__(self):
        self.kind = os.environ.get("COGU_OUTFIT_PROVIDER", "json").strip().lower()
        self.url = os.environ.get("COGU_OUTFIT_PROVIDER_URL", "").strip()
        self.model = os.environ.get("COGU_OUTFIT_PROVIDER_MODEL", "").strip()
        self.key = os.environ.get("COGU_OUTFIT_PROVIDER_API_KEY", "").strip()
        if self.kind == "openai":
            self.url = self.url or "https://api.openai.com/v1/images/edits"
            self.model = self.model or "gpt-image-2.5-sunburst"
            self.key = self.key or os.environ.get("OPENAI_API_KEY", "").strip()
        elif self.kind == "gemini":
            self.url = self.url or "https://generativelanguage.googleapis.com/v1beta/interactions"
            self.model = self.model or "gemini-nano-banana-2.1"
            self.key = self.key or os.environ.get("GEMINI_API_KEY", "").strip()
        elif self.kind == "cloudflare":
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
            if not self.url and re.fullmatch(r"[a-fA-F0-9]{32}", account_id):
                self.url = ("https://api.cloudflare.com/client/v4/accounts/" + account_id +
                            "/ai/run/@cf/black-forest-labs/flux-1-schnell")
            self.model = self.model or "@cf/black-forest-labs/flux-1-schnell"
            self.key = self.key or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        self.uses_references = self.kind != "cloudflare"
        parsed = urlparse(self.url)
        self.enabled = bool(self.kind in ("json", "openai", "gemini", "cloudflare") and self.url and self.model and
            (self.kind == "json" or self.key) and len(self.model) <= 120 and parsed.hostname and
            (parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1")))
            and not parsed.username and not parsed.password and not parsed.fragment)

    @staticmethod
    def _multipart(prompt, model, references):
        boundary = "cogu-" + secrets.token_hex(12)
        chunks = []
        for name, value in (("model", model), ("prompt", prompt), ("size", "1024x1536"),
                            ("quality", "medium"), ("output_format", "png")):
            chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode("utf-8"))
        extensions = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
        for reference in references:
            mime = reference["mime_type"]
            content = base64.b64decode(reference["image_base64"], validate=True)
            filename = "cogu-%s.%s" % (reference["category"], extensions[mime])
            chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"image[]\"; filename=\"{filename}\"\r\n"
                           f"Content-Type: {mime}\r\n\r\n").encode("ascii") + content + b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode("ascii"))
        return b"".join(chunks), "multipart/form-data; boundary=" + boundary

    def generate(self, prompt, body_type, gender, references):
        if not self.enabled:
            raise OutfitProviderError("Image generation provider is not configured.")
        if self.kind == "openai":
            payload, content_type = self._multipart(prompt, self.model, references)
        elif self.kind == "gemini":
            parts = [{"type": "text", "text": prompt}]
            parts.extend({"type": "image", "mime_type": ref["mime_type"], "data": ref["image_base64"]}
                         for ref in references)
            payload = json.dumps({"model": self.model, "input": parts,
                                  "response_format": {"type": "image", "mime_type": "image/jpeg", "aspect_ratio": "2:3"}}).encode("utf-8")
            content_type = "application/json"
        elif self.kind == "cloudflare":
            payload = json.dumps({"prompt": prompt[:2048], "steps": 8}).encode("utf-8")
            content_type = "application/json"
        else:
            payload = json.dumps({"model": self.model, "prompt": prompt, "body_type": body_type,
                                  "gender": gender,
                                  "reference_images": references, "output_format": "png"}, ensure_ascii=False).encode("utf-8")
            content_type = "application/json"
        headers = {"Content-Type": content_type, "Accept": "application/json"}
        if self.kind == "gemini":
            headers["x-goog-api-key"] = self.key
        elif self.key:
            headers["Authorization"] = "Bearer " + self.key
        try:
            with build_opener(_NoRedirect).open(Request(self.url, data=payload, headers=headers, method="POST"), timeout=120) as response:
                if response.status != 200:
                    raise OutfitProviderError("Image provider returned an error.")
                raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise OutfitProviderError("Image provider response is too large.")
            result = json.loads(raw)
            if self.kind == "openai":
                encoded = result["data"][0]["b64_json"]
                claimed_mime = "image/png"
            elif self.kind == "gemini":
                if result.get("status") != "completed":
                    raise OutfitProviderError("Gemini did not complete image generation.")
                image_parts = [part for step in result.get("steps", []) if step.get("type") == "model_output"
                               for part in step.get("content", []) if part.get("type") == "image"]
                if not image_parts:
                    raise OutfitProviderError("Gemini returned no image.")
                encoded = image_parts[0]["data"]
                claimed_mime = image_parts[0].get("mime_type")
            elif self.kind == "cloudflare":
                if result.get("success") is not True:
                    raise OutfitProviderError("Cloudflare did not complete image generation.")
                encoded = result["result"]["image"]
                claimed_mime = None
            else:
                encoded = result["image_base64"]
                claimed_mime = result.get("mime_type")
            if not isinstance(encoded, str):
                raise OutfitProviderError("Image provider response has no image.")
            content = base64.b64decode(encoded, validate=True)
            mime = image_mime(content)
            if claimed_mime and claimed_mime != mime:
                raise OutfitProviderError("Image provider MIME type does not match image content.")
            return "data:%s;base64,%s" % (mime, base64.b64encode(content).decode("ascii"))
        except HTTPError as error:
            code = "credentials" if error.code in (401, 403) else "rate_limit" if error.code == 429 else "unavailable"
            error.close()
            raise OutfitProviderError("Image provider request failed.", code=code) from None
        except (OSError, ValueError, KeyError, TypeError, binascii.Error) as error:
            raise OutfitProviderError("Image generation provider is unavailable or returned an invalid image.") from error


class OutfitPreviewService:
    GENDERS = {"male": "Nam", "female": "Nữ"}
    BODY_TYPES = {"slim": "Slim", "regular": "Regular", "curvy": "Curvy / Plus-size",
                  "tall": "Tall", "petite": "Petite"}
    CATEGORIES = {"shirt": "Áo", "trousers": "Quần", "shoes": "Giày/dép"}
    DISCLAIMER = "Ảnh AI chỉ mô phỏng phong cách; không bảo đảm độ vừa vặn, màu sắc hay hình dáng thực tế. Hãy xem bảng cỡ và thông tin sản phẩm trước khi mua."

    def __init__(self, catalog, images_dir):
        self.catalog = catalog
        self.images_dir = Path(images_dir).resolve()
        self.provider = OutfitImageProvider()

    def available_products(self):
        result = {}
        for category in self.CATEGORIES:
            total, products = self.catalog.list_products(category=category, page_size=60)
            for page in range(2, (total + 59) // 60 + 1):
                products.extend(self.catalog.list_products(category=category, page=page, page_size=60)[1])
            result[category] = [product for product in products if product["stock"] > 0]
        return result

    @staticmethod
    def _selected_ids(body):
        if not isinstance(body, dict) or set(body) != {"body_type", "gender", "products"}:
            raise ValueError("Vui lòng chọn dáng người và sản phẩm hợp lệ.")
        chosen = body["products"]
        if not isinstance(chosen, dict) or any(key not in OutfitPreviewService.CATEGORIES for key in chosen):
            raise ValueError("Chỉ chọn tối đa một áo, một quần và một đôi giày.")
        selected = {key: value for key, value in chosen.items() if value is not None}
        if not selected or any(type(value) is not int or value < 1 for value in selected.values()):
            raise ValueError("Chọn ít nhất một sản phẩm hợp lệ.")
        if len(set(selected.values())) != len(selected):
            raise ValueError("Mỗi danh mục cần một sản phẩm khác nhau.")
        return selected

    def _reference(self, product):
        image = product["image"]
        if not isinstance(image, str) or not re.fullmatch(r"images/[A-Za-z0-9._-]+", image):
            raise OutfitProviderError("Catalogue contains an invalid product image.")
        path = (self.images_dir / image.removeprefix("images/")).resolve()
        if not path.is_relative_to(self.images_dir) or not path.is_file():
            raise OutfitProviderError("Product reference image is unavailable.")
        try:
            content = path.read_bytes()
            mime = image_mime(content)
        except (OSError, ValueError) as error:
            raise OutfitProviderError("Product reference image is unavailable or invalid.") from error
        return {"category": product["category"], "product_id": product["id"],
                "mime_type": mime, "image_base64": base64.b64encode(content).decode("ascii")}

    def preview(self, body):
        body_type = body.get("body_type") if isinstance(body, dict) else None
        gender = body.get("gender") if isinstance(body, dict) else None
        if not isinstance(body_type, str) or body_type not in self.BODY_TYPES:
            raise ValueError("Dáng người không hợp lệ.")
        if not isinstance(gender, str) or gender not in self.GENDERS:
            raise ValueError("Giới tính người mẫu không hợp lệ.")
        selected = self._selected_ids(body)
        available = self.available_products()
        products = []
        for category, product_id in selected.items():
            product = next((item for item in available[category] if item["id"] == product_id), None)
            if product is None:
                raise ValueError("Sản phẩm không tồn tại, sai danh mục hoặc đã hết hàng.")
            products.append(product)
        product_facts = [{key: product[key] for key in ("id", "slug", "name_vi", "category", "material", "price_vnd", "image", "stock")}
                         for product in products]
        if self.provider.enabled:
            prompt = ("Create a tasteful, photorealistic full-body fashion editorial image of one adult %s model with a %s body type. "
                      "Exactly ONE person centered in a single photograph, entire head and both shoes visible. "
                      "The person wears ALL selected items together as ONE outfit. No collage, comparison, extra people or floating clothing. "
                      "%s "
                      "Selected items: %s. For unselected garment categories, use neutral unbranded basics and do not imply those are COGU products. Do not imply the image guarantees fit. "
                      "Neutral off-white and sage studio, clear garment details, no text, logo or watermark." %
                      ({"male": "man", "female": "woman"}[gender], self.BODY_TYPES[body_type],
                       ("Use the supplied COGU product reference photos to depict the selected garments as faithfully as possible."
                        if self.provider.uses_references else "Illustrate the selected garment descriptions; no product photos are supplied."),
                       "; ".join("%s: %s, %s" %
                       (self.CATEGORIES[item["category"]], item["name_vi"], item["material"]) for item in products)))
            try:
                references = [self._reference(product) for product in products] if self.provider.uses_references else []
                image_url = self.provider.generate(prompt, body_type, gender, references)
                description_only = not self.provider.uses_references
                return {"mode": "provider", "label": ("ẢNH AI · MÔ PHỎNG TỪ MÔ TẢ SẢN PHẨM" if description_only
                        else "ẢNH AI · MÔ PHỎNG TỪ SẢN PHẨM ĐÃ CHỌN"),
                        "image_url": image_url, "body_type": body_type, "gender": gender, "products": product_facts,
                        "disclaimer": self.DISCLAIMER, "notice": ("Ảnh AI tạo từ tên và chất liệu sản phẩm; không dùng ảnh sản phẩm làm tham chiếu. Chi tiết có thể khác sản phẩm thật."
                        if description_only else "Ảnh được tạo bởi dịch vụ AI đã cấu hình; chi tiết có thể khác sản phẩm thật.")}
            except OutfitProviderError as error:
                notice = "Dịch vụ tạo ảnh hiện không khả dụng. Đang hiển thị ảnh mẫu của dáng người; ảnh không dùng sản phẩm đã chọn."
                if error.code == "rate_limit":
                    notice += " Dịch vụ AI đang giới hạn lượt tạo ảnh hoặc đã hết hạn mức; vui lòng thử lại sau."
                elif error.code == "credentials":
                    notice += " Cấu hình xác thực dịch vụ AI cần được quản trị viên kiểm tra."
        else:
            notice = "Ảnh mẫu của dáng người; ảnh không dùng sản phẩm đã chọn. Chưa cấu hình dịch vụ tạo ảnh."
        return {"mode": "demo", "label": "DEMO · ẢNH MẪU MINH HỌA",
                "image_url": "/images/outfit-sample-%s-%s.png" % (gender, body_type),
                "body_type": body_type, "gender": gender, "products": product_facts, "disclaimer": self.DISCLAIMER, "notice": notice}
