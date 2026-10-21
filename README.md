# COGU Fashion Storefront Demo

# E-commerce_web

> Phase 8 is complete for the academic demonstration. COGU now includes AI Studio outfit previews using real catalogue selections and five preset body types, alongside the storefront, COD checkout, admin operations, multimodal search and grounded shopping assistant. Optional image generation uses product reference photos; the default run shows explicitly labeled sample images. See [feature status](docs/FEATURE_STATUS.md), [outfit preview architecture](docs/OUTFIT_PREVIEW.md), [roadmap](docs/ROADMAP.md), and [phase progress](docs/PHASE_PROGRESS.md).

## Phase 8 AI Studio and final demo

Run `python run_ui.py --no-browser`, then open `http://127.0.0.1:8080/studio`. Choose up to one shirt, one pair of trousers and one pair of shoes, select model gender (Nam/Nữ) and one of five body types, then choose **Tạo ảnh phối đồ**. The default image is a **DEMO sample for the selected model**, not a rendering of selected products. No personal photo is requested. Every result warns that simulated imagery does not guarantee actual fit.

Gemini image generation is available as another optional provider. Set `COGU_OUTFIT_PROVIDER=gemini` and `GEMINI_API_KEY` in the local `.env` or server environment; see [OUTFIT_PREVIEW.md](docs/OUTFIT_PREVIEW.md). A live Free Tier request returned HTTP 429 because image generation had zero available quota, so the site displayed a labeled DEMO sample.

For live generation, configure Gemini Interactions, OpenAI Images Edit or a compatible JSON image provider as described in [OUTFIT_PREVIEW.md](docs/OUTFIT_PREVIEW.md). [`.env.example`](.env.example) lists server variables; `run_ui.py` automatically reads a local `.env` file without replacing variables already set in the shell. Keep API keys only in `.env` or the shell, never in `.env.example`. The [instructor script](docs/INSTRUCTOR_DEMO.md) gives an eight-minute walkthrough. Run `python -m unittest discover -s tests -q` for the full test suite. For Studio browser QA, start a server on port 8765 using a **temporary** `COGU_CATALOG_DB`, set `COGU_BROWSER_QA_TEMP_DB=1` in the test terminal, and run `node tests/studio_browser_qa.mjs`.

## Phase 7 shopping assistant

On any customer page, open **Hỏi COGU** to ask about products, sizes, materials, COD and, after signing in, your own orders. On `/shop`, select two or three product cards and choose **So sánh ngay** for a live catalogue table and grounded analysis. On `/account#shopping-preferences`, save style, preferred colors and a VND budget to see in-stock recommendations. Answers, comparison analysis and recommendation explanations carry either an AI-provider or explicit **DEMO** label. The default installation needs no LLM account.

For provider setup, route details, privacy boundaries and limits, read [Phase 7 architecture](docs/SHOPPING_AI_ARCHITECTURE.md). Run `python -m unittest tests.test_shopping_ai -q` for the focused HTTP suite. For responsive browser QA, start a server on port 8765 with a **temporary** `COGU_CATALOG_DB`, set `COGU_BROWSER_QA_TEMP_DB=1` in the test terminal, and run `node tests/shopping_ai_browser_qa.mjs`.

## Web demonstration

Run `python run_ui.py --no-browser` from this directory, then visit `http://127.0.0.1:8080/` for the homepage, `/shop` for the catalogue, `/account` to register, and `/cart` to place a COD order. Select a size and color on a product page to add its exact variant. The order reference and private history are available at `/account#orders`. Text and voice-transcript search remain public. Image search defaults to clearly labeled DEMO samples; configure an image embedding API to enable content-based uploads. To enable the separate legacy administrator order demo in Demo Lab, set `COGU_ADMIN_TOKEN` before starting the server. COD orders are saved locally; no payment is collected online.

Customer extras: sign in to save a product to the wishlist, manage delivery addresses, change or remove exact-variant cart items, enter an active promotion code, and send a support request from `/account`. The account's **Đánh giá của tôi** section lists products ready for review after an eligible **completed purchase**; follow the product link to submit. A staff member must approve the review before it appears publicly with a verified-purchase badge. The default payment method is COD; order, payment and shipment statuses are tracked separately. Invalid promotion codes leave the previous cart totals and checkout usable.

The catalogue is seeded from `dataset/catalog_seed.json` into `data/cogu_catalog.sqlite3` on first use. The current shop has **38 products in three categories: Áo (11), Quần (12), Giày/dép (15)**. Set `COGU_CATALOG_DB` to another SQLite path to keep a separate catalogue database. An existing database is not reset at startup; run `python scripts/sync_catalog_scope.py` once to update a database created before the three-category change. That command makes a SQLite backup under `data/backups/`, removes off-scope shop products, and adds the 15 new items while keeping existing shirt/trouser/footwear stock and order snapshots. `dataset/products.json` remains the original 12-product fixture for the console demo and legacy tests; the storefront and web search use the current 38-product SQLite catalogue.

The original 21 checks run by executing the four legacy `tests/test_*.py` scripts listed below. Run the HTTP, catalogue and commerce checks with `python -m unittest discover -s tests -v`. To repeat desktop, tablet and mobile browser checks while the server runs on port 8765, use `node tests/browser_qa.mjs` (Chrome required). The full browser purchase journey is `tests/commerce_browser_qa.mjs`; run it against a server started with a temporary `COGU_CATALOG_DB` and set `COGU_BROWSER_QA_TEMP_DB=1` for that test process.

## Phase 6 search demonstration

Search the homepage for `áo thun oversize` or `ao thun oversize`; both rank the same product first. Use the result filters for category, color, size and VND price. On the voice tab, grant microphone permission in a supporting browser, speak Vietnamese, edit the transcript, then submit it. Typed text works when recognition is unavailable.

Image search shows **DEMO — ẢNH MẪU** until `COGU_IMAGE_ENCODER_URL` and `COGU_IMAGE_ENCODER_MODEL` are configured. In the storefront's DEMO mode, the visible shoe sample works; arbitrary uploads are disabled. The optional encoder endpoint receives real image bytes for both product images and uploaded queries, and returns vectors in one shared space. See [the API contract and setup](docs/SEARCH_ARCHITECTURE.md). The app does not infer image content from file names.

Run `python -m unittest discover -s tests -v` for the full server suite. Against a server using a temporary `COGU_CATALOG_DB` on port 8765, set `COGU_BROWSER_QA_TEMP_DB=1` and run `node tests/search_browser_qa.mjs` for the focused browser check.

## Phase 5 staff demonstration

Provision five local staff accounts once, then start the server and open `/admin`:

```powershell
python scripts/seed_admin_demo.py
python run_ui.py --no-browser
```

The provisioning script prints a unique generated password once for each of `admin@cogu.demo`, `sales@cogu.demo`, `warehouse@cogu.demo`, `support@cogu.demo` and `manager@cogu.demo`. Save them locally. Password hashes, not plaintext passwords, are stored in SQLite. Rerun with `--reset` to rotate those passwords and revoke existing sessions. Set `COGU_CATALOG_DB` before both commands to use an isolated demo database; the database is never reset by startup.

The dashboard supports catalogue and variant edits, stock adjustments with a required reason, order and shipment state transitions, staff-recorded COD collection, promotion codes, review moderation, support replies and sales/inventory reports. Customers can submit support requests from `/account` and reviews from a product page after a completed eligible purchase. Only approved reviews appear publicly. Staff accounts use a separate cookie and role permissions; a customer session cannot call `/api/admin`.

**Payment and delivery disclosure:** staff may record that COD was collected or an order was delivered in this local demo. These records are not provider or carrier confirmations. Revenue reports count staff-recorded, unrefunded COD collections only. No online payment method is offered.

Run `python -m unittest discover -s tests -v` for the server suite. Browser QA for the staff screen is `node tests/admin_browser_qa.mjs` against an isolated server on port 8765 with `COGU_BROWSER_QA_TEMP_DB=1`; see [the Phase 5 progress entry](docs/PHASE_PROGRESS.md) for the exact temporary account setup.

## Assignment 06 — Information System Analysis and Design

**Student:** Hoang Thanh Tung (B23DCVT447)  
**Class:** E23TTNT01-B  
**Instructor:** PGS.TS. Tran Dinh Que

---

## Project Description

A three-layer e-commerce demonstration with a persistent catalogue and the original multimodal search prototype:
- **Text search**: accent-insensitive Vietnamese attribute matching with weighted relevance and filters
- **Voice search**: browser Vietnamese recognition or editable typed transcript, followed by the text pipeline
- **Image search**: cosine similarity over vectors from one configured image-content encoder, or explicitly labeled DEMO sample vectors

The system follows a three-layer architecture:
```
Presentation -> Application/Intelligence -> Data
```

---

## Python Version

- Python 3.13+ (tested on 3.13.13)

## Required Packages

- `numpy` (for cosine similarity computation)

No other external packages are required.

## Installation

```bash
pip install numpy
```

---

## How to Run

### Demo Program
```bash
cd assignment06_code
python main.py
```

### Run All Tests
```bash
cd assignment06_code
python tests/test_text_search.py
python tests/test_voice_search.py
python tests/test_image_search.py
python tests/test_ranking.py
python -m unittest discover -s tests -v
```

---

## Project Directory Structure

```
assignment06/
|
+-- main.py                              # Entry point for demonstration
|
+-- presentation/                        # Presentation Layer
|   +-- __init__.py
|   +-- search_ui.py                     # Main interaction entry point
|   +-- voice_input.py                   # Voice input interaction
|   +-- image_upload.py                  # Image upload interaction
|   +-- search_result_view.py            # Result display
|
+-- application/                         # Application / Intelligence Layer
|   +-- __init__.py
|   +-- query_service.py                 # Common query representation
|   +-- speech_service.py                # Simulated speech-to-text
|   +-- image_service.py                 # Image embedding service
|   +-- search_service.py                # Candidate retrieval
|   +-- ranking_service.py               # Result ranking
|   +-- catalog_service.py               # Validated catalogue queries
|
+-- data/                                # Data Layer
|   +-- __init__.py
|   +-- product_repository.py            # Product data access
|   +-- order_repository.py              # Order data access
|   +-- vector_index.py                  # Embedding similarity search
|   +-- catalog_models.py                # Product and ProductVariant entities
|   +-- catalog_repository.py            # SQLite catalogue and stock
|   +-- catalog_search_repository.py     # Adapter for existing web search
|
+-- dataset/                             # Prototype data
|   +-- products.json                    # 12 products
|   +-- orders.json                      # 3 orders
|   +-- catalog_seed.json                # 38 products and 189 variants
|
+-- web/                                 # Homepage, Shop and Product Detail pages
+-- images/                              # Local product and editorial photographs
|
+-- tests/                               # Test suite
|   +-- test_text_search.py              # 4 text search tests
|   +-- test_voice_search.py             # 3 voice search tests
|   +-- test_image_search.py             # 5 image search tests
|   +-- test_ranking.py                  # 5 ranking tests
|
+-- results/                             # Demonstration results
|
+-- README.md                            # This file
```

---

## Example Commands

```bash
# Run the full demonstration
python main.py

# Run individual test suites
python tests/test_text_search.py
python tests/test_voice_search.py
python tests/test_image_search.py
python tests/test_ranking.py
```

---

## Validation

The current implementation has been executed and validated. The four test suites contain 21 tests in total, and all 21 passed. The full demonstration in `main.py` also completed successfully for Text, Voice, Image, and Order Search. Actual outputs are stored under `results/`.

## Limitations

1. **Speech recognition is simulated**: The SpeechService accepts pre-transcribed text, not real audio input.
2. **Image embeddings are artificial**: 3-dimensional artificial vectors are used instead of real image encoder output.
3. **Text search is keyword-based**: Simple word matching is used, not semantic or embedding-based search.
4. **Payments are COD only**: Order placement confirms the COD order and reserves stock, while payment stays pending until collection. No online payment provider or shipment carrier is connected.
5. **Catalogue photos and prices are illustrative**: The new catalogue is demonstration data, not live inventory or verified sales.
6. **Ranking is basic**: Score-based sorting without learned models, popularity, or business signals.
7. **Historical fixture remains small**: The original console and direct-run tests use 12 JSON products; web search and Shop use 30 SQLite products. The three original orders remain sample data.
