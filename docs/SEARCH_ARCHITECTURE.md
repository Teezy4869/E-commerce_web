# Phase 6 multimodal search

The existing Presentation → Application → Data pipeline remains. `presentation/web_server.py` validates HTTP requests and preserves `/api/search/text`, `/api/search/voice` and `/api/search/image`. `application/search_service.py` retrieves and scores candidates; `application/ranking_service.py` orders them. The storefront displays all three modalities in one results section; technical pipeline JSON remains in Demo Lab.

## Text and voice

Text search folds Vietnamese accents and `đ`, tokenizes punctuation, removes a small list of request words, and weights matches in the name, category, colors, material, sizes and description. Full phrase matches in the name receive an additional boost. Filters accept `category`, `color`, `size`, `material`, `min_price` and `max_price`; values are validated on the server. The storefront exposes category, color, size and price controls, plus relevance and price sorting. Scores express a deterministic relevance rule, not a trained model.

The browser uses Web Speech recognition with `vi-VN` where available. It checks microphone permission when the browser exposes that state, reports permission and recognition errors, and leaves the transcript editable. Recognition never automatically submits a search. The user confirms the text by submitting the form. Browsers without speech recognition still use the typed-text form. The backend `VoiceInput` → `SpeechService` → `QueryService` → `SearchService` pipeline continues to accept `audio_input` for compatibility; that field contains a transcript. The backend does **not** receive audio bytes or perform speech recognition.

## Image modes

### Default: DEMO samples

No encoder is configured by default. The storefront and API explicitly say **DEMO — ẢNH MẪU**. The browser disables arbitrary uploads and offers only the three known sample images. `/api/search/image` rejects arbitrary `image_data` in this mode. It retains `image_vector` for the original API tests and technical demonstration, labeled as a demo vector. No filename-derived vector is generated for user uploads.

### Configured content encoder

Set the following environment variables before starting `run_ui.py`:

```powershell
$env:COGU_IMAGE_ENCODER_URL = 'https://your-encoder.example/embed'
$env:COGU_IMAGE_ENCODER_MODEL = 'your-versioned-image-model'
$env:COGU_IMAGE_ENCODER_API_KEY = 'your-secret' # optional for a local encoder
python run_ui.py --no-browser
```

The URL must use HTTPS, except a loopback HTTP endpoint for local testing. The configured service must accept a JSON `POST` with:

```json
{"model":"your-versioned-image-model","mime_type":"image/png","image_base64":"..."}
```

It must return a JSON object with a numeric, finite, nonzero image embedding:

```json
{"embedding":[0.12,0.34,0.56]}
```

Use an image model that produces vectors in the **same space and dimension** for both catalogue images and uploaded queries (for example a deployed CLIP image encoder). `application/visual_search.py` sends actual PNG, JPEG or WebP bytes to the configured API for every catalogue image and every query. `data/visual_embedding_repository.py` caches vectors in SQLite by encoder URL/model identity and image-content SHA-256, then `data/vector_index.py` ranks them by cosine similarity. Change the model identifier when encoder weights change so the cache is rebuilt. Product edits refresh the image index. Arbitrary uploaded images are accepted only in this mode, up to 5 MB; the server checks their file signatures instead of trusting the filename or browser MIME type.

If configuration or initial encoding fails, the server starts in clearly labeled DEMO mode. If the encoder fails during a query, the API returns an error instead of inventing a visual result. `/api/search/capabilities` reports the active mode and whether upload is enabled. When a remote encoder is used, image bytes are sent to that configured service; no remote service is contacted in default DEMO mode.

For public deployment with a paid encoder, add request rate limits and provider usage monitoring. This local demonstration does not include those controls.

## Verification

`tests/test_search_enhanced.py` checks Vietnamese folding/ranking/filters, voice transcript compatibility, DEMO restrictions and the content encoder contract against a local test API. It tests two different product images and verifies persistent embedding-cache reuse. `tests/search_browser_qa.mjs` checks editable Vietnamese microphone transcript, text filters, DEMO labeling and responsive results. Legacy search scripts and other storefront/commerce/admin tests remain in the regression suite.
