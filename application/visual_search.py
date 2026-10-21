"""Optional content-based image search backed by one configured embedding API."""

import base64
import binascii
import hashlib
import json
import math
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from data.vector_index import VectorIndex
from data.visual_embedding_repository import VisualEmbeddingRepository


class EncoderError(RuntimeError):
    pass


def image_mime(content):
    if not isinstance(content, bytes) or not 16 <= len(content) <= 5 * 1024 * 1024:
        raise ValueError("Image must be between 16 bytes and 5 MB.")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Only PNG, JPEG and WebP images are supported.")


class ImageEmbeddingAPI:
    """POST identical image bytes and model for catalogue and query images."""

    def __init__(self, url, model, api_key=""):
        parsed = urlparse(url)
        if not (parsed.scheme == "https" or
                (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1"))):
            raise ValueError("Image encoder URL must use HTTPS (or loopback HTTP).")
        if not parsed.netloc or parsed.username or parsed.password or not model or len(model) > 120:
            raise ValueError("Invalid image encoder configuration.")
        self.url = url
        self.model = model
        self.api_key = api_key
        self.identifier = hashlib.sha256(f"{url}\n{model}".encode()).hexdigest()

    def encode(self, content):
        mime = image_mime(content)
        payload = json.dumps({"model": self.model, "mime_type": mime,
                              "image_base64": base64.b64encode(content).decode("ascii")}).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with urlopen(Request(self.url, data=payload, headers=headers, method="POST"), timeout=15) as response:
                raw = response.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024:
                raise EncoderError("Image encoder returned an oversized response.")
            decoded = json.loads(raw)
            vector = decoded.get("embedding") if isinstance(decoded, dict) else None
            if not isinstance(vector, list) or not 3 <= len(vector) <= 4096 or any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in vector
            ):
                raise EncoderError("Image encoder returned an invalid embedding.")
            if not any(vector):
                raise EncoderError("Image encoder returned a zero embedding.")
            return [float(value) for value in vector]
        except (OSError, ValueError, KeyError) as error:
            raise EncoderError("Configured image encoder is unavailable or returned invalid data.") from error


class VisualSearch:
    SAMPLE_PATHS = frozenset({"images/query_shoes.jpg", "images/query_bag.jpg", "images/query_watch.jpg"})

    def __init__(self, catalog, images_dir, encoder, cache=None):
        self.catalog = catalog
        self.images_dir = Path(images_dir).resolve()
        self.encoder = encoder
        self.cache = cache or VisualEmbeddingRepository(catalog)
        self.index = None
        self.refresh()

    def _local_image(self, path):
        if not isinstance(path, str) or not re.fullmatch(r"images/[A-Za-z0-9._-]+", path):
            raise ValueError("Invalid local image path.")
        candidate = (self.images_dir / path.removeprefix("images/")).resolve()
        if not candidate.is_relative_to(self.images_dir) or not candidate.is_file():
            raise ValueError("Local image is unavailable.")
        content = candidate.read_bytes()
        image_mime(content)
        return content

    def _encode_cached(self, content):
        digest = hashlib.sha256(content).hexdigest()
        vector = self.cache.get(self.encoder.identifier, digest)
        if vector is None:
            vector = self.encoder.encode(content)
            self.cache.put(self.encoder.identifier, digest, vector)
        return vector

    def refresh(self):
        rows = []
        dimension = None
        page = 1
        while True:
            total, products = self.catalog.list_products(page=page, page_size=48)
            for product in products:
                embedding = self._encode_cached(self._local_image(product["image"]))
                if dimension is None:
                    dimension = len(embedding)
                elif len(embedding) != dimension:
                    raise EncoderError("Configured encoder returned inconsistent dimensions.")
                rows.append({"id": product["id"], "embedding": embedding})
            if page * 48 >= total:
                break
            page += 1
        self.index = VectorIndex(type("ImageRows", (), {"all_products": lambda _self: rows})())

    def query(self, image_path=None, image_data=None):
        if image_data is not None:
            if not isinstance(image_data, str) or len(image_data) > 7 * 1024 * 1024:
                raise ValueError("Image upload is too large.")
            try:
                content = base64.b64decode(image_data, validate=True)
            except (ValueError, binascii.Error) as error:
                raise ValueError("Image upload is not valid base64.") from error
        elif image_path in self.SAMPLE_PATHS:
            content = self._local_image(image_path)
        else:
            raise ValueError("Choose a sample image or upload an image.")
        image_mime(content)
        embedding = self._encode_cached(content)
        if self.index.dimension is not None and len(embedding) != self.index.dimension:
            raise EncoderError("Configured encoder returned a query with inconsistent dimensions.")
        return embedding


def configured_visual_search(catalog, images_dir):
    url = os.environ.get("COGU_IMAGE_ENCODER_URL", "").strip()
    model = os.environ.get("COGU_IMAGE_ENCODER_MODEL", "").strip()
    if not url and not model:
        return None, "DEMO — chỉ dùng ảnh mẫu; chưa có bộ mã hóa ảnh thật."
    try:
        if not url or not model:
            raise ValueError("Set both COGU_IMAGE_ENCODER_URL and COGU_IMAGE_ENCODER_MODEL.")
        encoder = ImageEmbeddingAPI(url, model, os.environ.get("COGU_IMAGE_ENCODER_API_KEY", ""))
        return VisualSearch(catalog, images_dir, encoder), ""
    except (ValueError, EncoderError) as error:
        return None, f"DEMO — bộ mã hóa ảnh chưa sẵn sàng ({error}). Chỉ dùng ảnh mẫu."
