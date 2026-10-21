# Phase 8 — AI Studio outfit preview

## Customer flow

`/studio` shows live, in-stock shirts, trousers and shoes from `CatalogRepository`. A customer can select **zero or one** item in each category and must choose at least one item overall. The model gender is Nam or Nữ; the five preset body types are Slim, Regular, Curvy / Plus-size, Tall and Petite. This model choice is not stored on a customer profile. No personal photo is requested. The server checks product IDs, category, stock, gender and body type again when the preview is requested. Product links lead to exact color/size availability on the detail page.

`application/outfit_preview_service.py` builds a prompt from actual product names and materials plus the chosen model gender and body type. Cloudflare FLUX receives text descriptions only; the other providers receive catalogue reference images. Customer photographs are not requested. The provider returns a PNG/JPEG/WebP image as base64; the server checks its signature and size before returning a data URL. Generated images are not stored in SQLite. The browser shows a progress indicator without claiming a completion percentage. If the provider is missing or fails, the API explicitly returns `mode: demo`, a reason, and a matching gender/body-type sample image. The sample **does not depict the selected products**. Every result includes the warning that AI imagery cannot guarantee fit, color or garment shape.

## Provider setup

### Free-tier image generation with Cloudflare

Cloudflare Workers AI offers 10,000 free Neurons per day on the Workers Free plan. The `@cf/black-forest-labs/flux-1-schnell` model uses only a small part of that daily allocation per image. It creates **real AI images from product names and materials**, but does **not** inspect the product photos, so its output may not match exact colors or garment details. AI Studio labels this mode “MÔ PHỎNG TỪ MÔ TẢ SẢN PHẨM”. If the quota is exhausted or a request fails, it displays an explicitly labeled sample image instead. See [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) and [model API](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/). Cloudflare can change the quota; check its pricing page before your demonstration.

1. Create a free Cloudflare account. In the dashboard, open **Workers AI → Use REST API → Create a Workers AI API Token**, then copy the Account ID. A manually created token needs **Workers AI - Read** and **Workers AI - Edit** permissions. Keep the account on **Workers Free** to avoid charges. See the [official setup guide](https://developers.cloudflare.com/workers-ai/get-started/rest-api/).
2. Put these values in the private `.env` next to `run_ui.py` (not `.env.example`):

   ```dotenv
   COGU_OUTFIT_PROVIDER=cloudflare
   CLOUDFLARE_ACCOUNT_ID=<32-character account ID>
   CLOUDFLARE_API_TOKEN=<server-side API token>
   ```

3. Remove or leave blank any `COGU_OUTFIT_PROVIDER_URL` override, restart `python run_ui.py --no-browser`, then choose an outfit in `/studio` and click **Tạo ảnh**. A successful request returns `mode: provider`; a failed request returns `mode: demo` with its reason. The Gemini key can stay in `.env` but is unused when `COGU_OUTFIT_PROVIDER=cloudflare`.

The Python backend calls Workers AI directly through its REST API; deploying a separate Worker is unnecessary. Keep `COGU_OUTFIT_PROVIDER_MODEL` and `COGU_OUTFIT_PROVIDER_API_KEY` blank to use the default FLUX model and `CLOUDFLARE_API_TOKEN`. `/api/outfit/catalog` exposes `uses_product_photos: false` for Cloudflare so the UI describes the input correctly. HTTP 401/403 produces a safe configuration notice; HTTP 429 produces a rate/quota notice. Neither provider response bodies nor tokens are exposed to customers. The private `.env` is excluded from Git.

### Live verification — 21 October 2026

Created the account-scoped `COGU AI Studio` token with Workers AI Read/Edit after user confirmation and configured the private local `.env`. Two live generation requests succeeded in Chrome at `http://127.0.0.1:8080/studio`. The final request used FLUX.1 schnell with eight diffusion steps and an explicit single-person composition; its generated image loaded at 1024 × 1024 with the description-based AI label. The preview now contains the full image instead of cropping it. Exact product colors and details remain approximate because no product photo is supplied to this model.

Validation: `python -m unittest tests.test_outfit_preview -q` passed all six tests, including the Cloudflare request/response contract, credential rejection and rate/quota fallback. JavaScript syntax and `git diff --check` passed. No credentials were committed. Local startup remains `python run_ui.py --no-browser`.

The current ChatGPT/Codex account cannot be used as a free API key for this site's live image requests. ChatGPT/Codex image tools can generate static sample assets during development; they do not grant a server-side image API quota. The existing OpenAI API mode requires separate API access and billing.

For Gemini image generation from the selected catalogue photos, obtain a Gemini API key and configure the server environment:

```powershell
$env:COGU_OUTFIT_PROVIDER = 'gemini'
$env:GEMINI_API_KEY = '<your server-side key>'
python run_ui.py --no-browser
```

Alternatively, put `COGU_OUTFIT_PROVIDER=gemini` and `GEMINI_API_KEY=...` in the local `.env` file next to `run_ui.py`; the launcher loads it at startup. `.env.example` is a public template and should contain no key. The local `.env` is excluded by `.gitignore`.

This uses Google's [Gemini Interactions image API](https://ai.google.dev/gemini-api/docs/image-generation) at `https://generativelanguage.googleapis.com/v1beta/interactions`, with the `gemini-nano-banana-2.1` default model. The server sends a text prompt and up to three catalogue reference images, requests JPEG output, and reads image content from `model_output` steps. `COGU_OUTFIT_PROVIDER_MODEL` can override the model. The key is never sent to the browser. Google's [pricing page](https://ai.google.dev/gemini-api/docs/pricing) lists image generation as unavailable on the Free Tier; a project with zero image-model quota returns HTTP 429 and the Studio falls back to a labeled DEMO sample. A live request with the local key on 16 October 2026 received this 429 response, so no real generated image was produced.

The default local demo needs no external credentials. For direct OpenAI image editing, set these variables in the server shell:

```powershell
$env:COGU_OUTFIT_PROVIDER = 'openai'
$env:OPENAI_API_KEY = '<your server-side key>'
$env:COGU_OUTFIT_PROVIDER_MODEL = 'gpt-image-2.5-sunburst'
python run_ui.py --no-browser
```

The server sends a multipart request with up to three `image[]` product references and a prompt to `https://api.openai.com/v1/images/edits`; it reads `data[0].b64_json` from the response. This follows the [official OpenAI Images Edit reference](https://developers.openai.com/api/reference/resources/images/methods/edit) and [image-generation guide](https://developers.openai.com/api/docs/guides/image-generation). The model can be changed with `COGU_OUTFIT_PROVIDER_MODEL`. Account access and billing eligibility depend on the provider; no live paid call was made during project verification. API credentials stay on the server.

For another image-generation service, set `COGU_OUTFIT_PROVIDER=json`, `COGU_OUTFIT_PROVIDER_URL` and `COGU_OUTFIT_PROVIDER_MODEL` (optional `COGU_OUTFIT_PROVIDER_API_KEY`). The URL must use HTTPS, except loopback HTTP for a local service. The service receives:

```json
{"model":"your-image-model","prompt":"...","body_type":"regular","gender":"male","reference_images":[{"category":"shirt","product_id":17,"mime_type":"image/png","image_base64":"..."}],"output_format":"png"}
```

It must respond with `{"image_base64":"...","mime_type":"image/png"}` where the image is valid PNG, JPEG or WebP content. Redirects are rejected. A local mock provider test verifies both the JSON contract and the OpenAI multipart contract. If the provider is unavailable or returns invalid image data, the API shows a labeled sample and a warning rather than claiming a generated preview.

## Endpoints and limits

| Route | Purpose |
| --- | --- |
| `GET /api/outfit/catalog` | Model genders, body types, live in-stock product choices, image-provider mode and fit disclaimer |
| `POST /api/outfit/preview` | Validate gender, body type and selected IDs, enforce signed-in CSRF, generate or return labeled sample |

The POST accepts at most 8 KB of JSON and is limited to three requests per minute per customer or client IP using the existing SQLite rate-window store. No photo-upload route exists. Product reference images are validated as local files within `images/`. A remote provider receives product imagery and prompt content but no personal photos or order data.

## Sample asset provenance

Ten sample photographs in `images/outfit-sample-{male,female}-{slim,regular,curvy,tall,petite}.png` are included. Five originals were generated for Phase 8 and reused where the subject matches; five additional gender/body-type combinations were generated with the built-in imagegen tool. They are intentionally generic and never represented as a preview of the selected COGU items. The original unqualified sample files remain for compatibility.

Shared prompt: *Photorealistic natural, full-body premium fashion editorial in an off-white and muted sage studio; simple cream button-up shirt, relaxed dark olive trousers and clean white low-top shoes; realistic garment texture and proportions, soft daylight, vertical portrait framing; no logos, text, watermark or interface; clearly a generic illustrative sample, not selected catalogue items or guaranteed fit.*

Subject variants: Slim — a naturally slender adult Vietnamese-looking woman; Regular — an adult Vietnamese-looking model with regular proportions; Curvy / Plus-size — a curvy adult Vietnamese-looking woman with realistic inclusive proportions; Tall — a tall adult Vietnamese-looking man with natural long-limbed proportions; Petite — a short-statured adult Vietnamese-looking woman with natural proportions.

## Verification

`tests/test_outfit_preview.py` checks both model genders and all five body types, live product/category validation, signed-in CSRF, request limits, sample labels, the JSON provider's product image bytes, the OpenAI multipart `image[]` contract, the Gemini Interactions request/response contract and invalid-provider fallback. `tests/studio_browser_qa.mjs` checks the storefront flow and responsive layouts at 1440, 820, 390 and 320 px against a disposable SQLite database.
