# Phase progress

## Phase 1 — Audit and foundation: complete (2026-10-15)

### Audit result

- Inspected `run_ui.py`, `main.py`, `presentation/`, `application/`, `data/`, `web/`, `dataset/`, `images/`, `tests/`, the README and existing reports.
- Documented architecture, dependencies, all HTTP endpoints, component behavior, test gaps and remaining risks in [ARCHITECTURE.md](ARCHITECTURE.md).
- Recorded the approved-next-phase targets in [ROADMAP.md](ROADMAP.md). No storefront redesign, account system, shopping storage or AI provider was added in this phase.

### Foundation changes

- `presentation/web_server.py`: confined static serving to public asset roots, denied source and dataset paths, protected both order APIs with `COGU_ADMIN_TOKEN`, removed wildcard CORS, set safer response headers, bounded JSON bodies, rejected invalid input types and isolated handler configuration per server.
- `web/index.html`, `web/js/app.js`: kept the current search demo working; removed public order examples, added a password field for the local administrator demo, loaded the public catalogue independently and fetched orders only with the administrator token.
- `run_ui.py`, `README.md`: surfaced the order-token setup and linked the audit and verification instructions. Existing demo marketing claims and image-upload wording were corrected to describe the prototype honestly.
- `tests/test_web_security.py`: added HTTP regression coverage for static traversal, order access, public text/voice/image search, invalid input and missing token configuration.

### Regression baseline and verification

| Check | Before changes | After changes |
| --- | --- | --- |
| Existing direct-run search/ranking tests | 21/21 passed (text 5, voice 4, image 7, ranking 5) | 21/21 passed |
| `python -m unittest discover -s tests -v` | 0 discovered (legacy tests are plain functions) | 6 new HTTP tests discovered and passed |
| Python `compileall` | Not run for baseline | Passed |
| JavaScript `node --check web/js/app.js` | Not run for baseline | Passed |

Verification commands from the project root:

```powershell
python tests/test_text_search.py
python tests/test_voice_search.py
python tests/test_image_search.py
python tests/test_ranking.py
python -m unittest discover -s tests -p test_web_security.py -v
python -m compileall -q main.py run_ui.py application data presentation tests
node --check web/js/app.js
```

To verify the web UI locally, set a temporary administrator secret and launch the server:

```powershell
$env:COGU_ADMIN_TOKEN = 'choose-a-long-random-local-secret'
python run_ui.py --no-browser
```

Visit `http://127.0.0.1:8080/`. Public product, text, voice-transcript and image-vector search work without the secret. Open the Order tab, enter the secret, then search a sample order such as `O001`. With no secret configured, both order APIs return 503 and public search remains available. The secret is held in the password field only; it is not saved in browser storage.

## Phase 2 — COGU Fashion UI/UX redesign: complete (2026-10-16)

### Changed files

- `web/index.html`, `web/css/style.css`, `web/js/app.js`: replaced the Luma search dashboard with a responsive COGU Fashion homepage. Added sticky navigation, fashion hero, category links, editorial and promotional sections, curated new and featured products, full catalogue filters, product details, AI feature highlights, search studio and separate Demo Lab. All active controls have working behavior; future AI features are labelled as unavailable.
- `dataset/products.json`: added Vietnamese display names/descriptions, integer VND demo prices and curated collection flags while keeping the original English search fields and price values for compatibility. The featured collection is explicitly marked as editorial selection because the sample orders have no line items or sales history.
- `application/search_service.py`: indexed the new Vietnamese names and descriptions in keyword retrieval.
- `images/cogu-hero.png`, `images/cogu-editorial.png`: added two generated editorial photographs. Both were created with the built-in image generation tool. The hero prompt requested a wide sunlit courtyard fashion photograph with a model on the right and text space on the left; the editorial prompt requested two models in a warm studio wearing green and neutral everyday outfits. Both specified no text, logos or watermark.
- `run_ui.py`, `presentation/web_server.py`, `README.md`, `docs/ROADMAP.md`: updated the public COGU naming and setup documentation. The launcher now closes cleanly on Ctrl+C without calling `shutdown()` from the serving thread.
- `tests/test_storefront_data.py`, `tests/browser_qa.mjs`: added localized search/data checks and a repeatable Chrome browser smoke test across desktop, tablet and mobile.

### Functional scope

Text, voice transcript and image-vector search still use their existing Python application services. Browser microphone recognition remains optional and depends on browser support. Uploaded image **pixels are not analyzed**; a demo vector is selected from the filename and disclosed in the UI. Product cards, categories, filters, details, sort order, search modes and mobile menu are interactive. Order lookup and listing remain protected in Demo Lab by `COGU_ADMIN_TOKEN`. Cart, checkout, account management and four additional AI integrations remain for later phases.

### Verification

| Check | Result |
| --- | --- |
| Original search/ranking scripts | 21/21 passed |
| `python -m unittest discover -s tests -v` | 8/8 passed (6 HTTP and 2 storefront data tests) |
| `node tests/browser_qa.mjs` against the local server | Passed at 1440×900, 820×1180, 390×844 and 320×720; no horizontal overflow; 12 cards loaded; category, Vietnamese text, voice, image, product details and mobile menu interactions passed |
| Python `compileall`, JavaScript `node --check`, console `main.py` | Passed |

To repeat browser verification from this directory:

```powershell
python run_ui.py --no-browser --port 8765
# In another terminal:
node tests/browser_qa.mjs
```

The optional browser check requires local Google Chrome. It writes screenshots to the operating system temporary directory. The generated page photographs are part of the local project under `images/`.

## Phase 3 — Fashion catalogue and product data: complete (2026-10-16)

### Changed files

- `data/catalog_models.py`, `data/catalog_repository.py`, `data/catalog_search_repository.py`, `application/catalog_service.py`: added typed Product and ProductVariant records, SQLite product/variant/image tables, exact SKU stock lookup, facets, related products, parameterized filters, allowlisted sorting and validated pagination. The search adapter lets existing text/voice/image services query all 30 shop products on the web.
- `dataset/catalog_seed.json`, `scripts/build_catalog_seed.py`, `data/cogu_catalog.sqlite3`: added a reproducible 30-product, 129-variant demonstration catalogue. The first 12 map from the original search fixture; `dataset/products.json` is preserved. Existing databases are not reseeded at startup. `COGU_CATALOG_DB` overrides the database path.
- `images/catalog-13.png`–`catalog-30.png`, `images/catalog-17-ivory.png`: added 19 generated studio product photographs matched to the listed garment or shoe and color. The image generation prompts requested the specific item, warm off-white background, realistic texture, soft shadow, and no logo or text. See [CATALOG_ARCHITECTURE.md](CATALOG_ARCHITECTURE.md) for data and image notes.
- `presentation/web_server.py`: added `/api/catalog/products`, `/api/catalog/products/{slug}`, `/api/catalog/stock`, `/api/catalog/facets` and safe `/shop` and `/product` page routes while retaining the original API and static-file restrictions.
- `web/shop.html`, `web/product.html`, `web/css/catalog.css`, `web/js/catalog-shared.js`, `web/js/shop.js`, `web/js/product.js`: added responsive catalogue and product pages with search/filter/sort/pagination, gallery, color/size selector, size guidance, live inventory status and related items.
- `web/index.html`, `web/js/app.js`, `run_ui.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`: linked the existing homepage to the full shop and product pages, kept the homepage's 12-product search collection clear, and updated launch and architecture documentation.
- `tests/test_catalog.py`, `tests/browser_qa.mjs`: added catalogue API, persistence, image, filter, validation and exact variant-stock checks; expanded browser checks to Shop and Product Detail at four viewports.

### Verification results

| Check | Result |
| --- | --- |
| Original direct-run text, voice, image and ranking checks | 21/21 passed |
| `python -m unittest discover -s tests -v` | 13/13 passed: 5 catalogue, 2 storefront data, 6 HTTP security |
| `node tests/browser_qa.mjs` | Passed at 1440×900, 820×1180, 390×844 and 320×720 for homepage, Shop and Product Detail. No horizontal overflow; new-product search result, filter, sort, pagination and size/color stock interactions passed. |
| `node --check` on four frontend scripts | Passed |
| `python -m compileall -q main.py run_ui.py application data presentation tests scripts` | Passed |

To verify Phase 3 from the project root:

```powershell
python run_ui.py --no-browser --port 8765
# In a second terminal:
node tests/browser_qa.mjs
python -m unittest discover -s tests -v
```

Open `http://127.0.0.1:8765/shop`, filter by Áo, and open **Áo thun oversize Essential**. Green M reports 7, green L reports sold out, and ivory M reports 14 with different SKUs. The shop data and stock are stored in SQLite. Cart, checkout, accounts and additional AI features remain outside Phase 3.

## Phase 4 — Account, shopping cart and checkout: complete (2026-10-16)

### Changed files

- `data/commerce_repository.py`, `application/commerce_service.py`: added customer, session, address, wishlist, exact-variant cart, order, payment, shipment and idempotency storage in the catalogue SQLite database. Passwords are salted PBKDF2 hashes. The service validates customer input and calculates VND discounts, delivery and totals. Checkout atomically checks/decrements stock, snapshots order details, records a unique reference and clears the cart. COD remains pending collection.
- `presentation/web_server.py`, `run_ui.py`: added customer scoped JSON endpoints, cookie sessions, CSRF checks and safe `/account`, `/cart`, `/order` page routes. Legacy administrator sample order APIs and all search endpoints remain available under their previous rules.
- `web/account.html`, `web/cart.html`, `web/order.html`, `web/css/commerce.css`, `web/js/commerce.js`, `web/js/account.js`, `web/js/cart.js`, `web/js/order.js`: added responsive account management, address and wishlist controls, cart quantities, promotion quotes, COD checkout, confirmation and order history.
- `web/product.html`, `web/js/product.js`, `web/index.html`, `web/shop.html`: connected exact color/size variant selection to cart and wishlist, added account/cart navigation and corrected outdated shopping copy.
- `tests/test_commerce.py`, `tests/commerce_browser_qa.mjs`: added HTTP and browser purchase journeys. `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/COMMERCE_ARCHITECTURE.md` describe the current behavior and limits.

### Verification results

| Check | Result |
| --- | --- |
| Original direct-run text, voice, image and ranking checks | 21/21 passed |
| `python -m unittest discover -s tests -v` | 15/15 passed: 5 catalogue, 2 commerce, 2 storefront data, 6 HTTP security |
| `node tests/browser_qa.mjs` | Passed existing homepage, Shop, Product Detail and text/voice/image search at 1440×900, 820×1180, 390×844 and 320×720 |
| `node tests/commerce_browser_qa.mjs` with temporary SQLite DB | Passed browser registration, address creation, exact-variant add to cart, COD order, confirmation, private history and account/cart/order layout at the same four viewports; no horizontal overflow |
| Python `compileall` and JavaScript `node --check` | Passed |

To inspect the purchase flow: run `python run_ui.py --no-browser`, open `/account`, register, save an address, choose a color and size on `/product?slug=ao-thun-oversize-essential`, add it to the cart, then place a COD order at `/cart`. The `/order?ref=...` page shows the reference and separate order, payment and shipment states. `/account#orders` retains the order after restart. COD placement does not collect or verify payment.

To repeat the browser journey without modifying the main catalogue, run in one PowerShell terminal:

```powershell
$env:COGU_CATALOG_DB = Join-Path $env:TEMP ('cogu-phase4-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
python run_ui.py --no-browser --port 8765
```

Then in another terminal:

```powershell
$env:COGU_BROWSER_QA_TEMP_DB = '1'
node tests/commerce_browser_qa.mjs
python -m unittest discover -s tests -v
```

The browser test writes screenshots to the operating system temporary directory. Phase 4 is complete; additional AI features and production hardening remain in later phases.

## Phase 5 — Admin dashboard and store operations: complete (2026-10-16)

### Changed files

- `data/admin_repository.py`, `application/admin_service.py`: separate staff authentication, five-role authorization, input validation, catalogue/variant/stock management, order state transitions, audit events, reviews, support and reports in SQLite.
- `data/commerce_repository.py`, `application/commerce_service.py`: persisted promotion codes; transactional code eligibility and use counts at checkout; staff-recorded COD and shipment provenance in customer order responses.
- `presentation/web_server.py`, `data/catalog_search_repository.py`: protected admin API, customer review/support routes, public approved reviews and active promotions, refreshed search catalogue after edits. Existing multimodal and customer routes remain.
- `web/admin.html`, `web/css/admin.css`, `web/js/admin.js`: responsive separate operations interface, accessible staff sign-in, role-aware navigation, product/variant/stock/order/promotion/review/support/staff management and dashboard/reports.
- `web/account.html`, `web/js/account.js`, `web/product.html`, `web/js/product.js`, `web/cart.html`, `web/js/cart.js`, `web/order.html`, `web/js/order.js`: customer support and reviews, live promotions and explicit internal delivery/COD labels.
- `scripts/seed_admin_demo.py`: one-time generated credentials for five demo roles, with optional password rotation. `run_ui.py` prints the staff URL.
- `tests/test_admin.py`, `tests/admin_browser_qa.mjs`: role, persistence, checkout/order, review/support, dashboard/report and responsive browser checks. `README.md`, `docs/ROADMAP.md`, `docs/COMMERCE_ARCHITECTURE.md`, `docs/ADMIN_ARCHITECTURE.md` document the implementation.

### Verification results

| Check | Result |
| --- | --- |
| Original direct-run text, voice, image and ranking checks | 21/21 passed |
| `python -m unittest discover -s tests -v` | 18/18 passed: 5 catalogue, 2 commerce, 3 admin, 2 storefront data, 6 HTTP security |
| Python `compileall`; JavaScript `node --check` | Passed; 12 JavaScript files checked |
| `node tests/browser_qa.mjs` | Passed original homepage, Shop, Product Detail and text/voice/image interactions at 1440×900, 820×1180, 390×844 and 320×720 |
| `node tests/commerce_browser_qa.mjs` | Passed customer purchase journey and responsive account/cart/order layouts against a temporary database |
| `node tests/admin_browser_qa.mjs` | Passed staff login, product/variant create, promotion create, customer API reflection, support-role navigation and desktop/tablet/mobile layouts at the same four viewport sizes with no horizontal overflow |
| `python scripts/seed_admin_demo.py --db <temporary DB>` and `--reset` | Both completed; five demo role accounts provisioned and rotated |

To inspect Phase 5 on the normal local database, run `python scripts/seed_admin_demo.py`, save its generated one-time passwords, then run `python run_ui.py --no-browser` and open `http://127.0.0.1:8080/admin`. Sign in with one of the five role emails printed by the script. Product and stock changes are immediately visible at `/shop` and `/product`; promotion changes affect `/cart` quotes. Customer reviews require a fulfilled, delivered order with staff-recorded COD collection, followed by moderator approval. Customers can open support requests from `/account`.

To repeat the admin browser test on a **temporary database**, start a server on port 8765 in one PowerShell terminal:

```powershell
$env:COGU_CATALOG_DB = Join-Path $env:TEMP ('cogu-phase5-qa-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
@'
from data.catalog_repository import CatalogRepository
from data.admin_repository import AdminRepository
from application.admin_service import AdminService
c = CatalogRepository()
a = AdminService(AdminRepository(c.db_path), 'images')
a.seed_staff('admin@cogu.test', 'Demo Admin', 'administrator', 'DemoPassword123!')
a.seed_staff('support@cogu.test', 'Demo Support', 'support', 'DemoPassword123!')
'@ | python -
python run_ui.py --no-browser --port 8765
```

Then in a second terminal:

```powershell
$env:COGU_BROWSER_QA_TEMP_DB = '1'
node tests/admin_browser_qa.mjs
```

This fixed browser-test password is confined to the disposable database. `tests/admin_browser_qa.mjs` writes screenshots to the operating system temporary directory. Phase 5 stops here; AI feature additions and production hardening are future work.


## Phase 6 — Multimodal search enhancement: complete (2026-10-16)

### Changed files

- `application/search_service.py`, `application/query_service.py`: Vietnamese accent folding, token-based attribute relevance, server-validated filters and shared text/voice/image query filters.
- `application/visual_search.py`, `data/visual_embedding_repository.py`: optional configured image-embedding API, content-byte validation, same encoder for catalogue/query images, SQLite content-hash cache and cosine index. Unconfigured or failed startup stays in clearly labeled DEMO sample mode.
- `presentation/web_server.py`: image capability endpoint, explicit DEMO/encoder response labels, bounded image uploads, configured encoder errors, preserved legacy search routes and refreshed product index after catalogue changes.
- `presentation/voice_input.py`, `application/speech_service.py`: kept transcript pipeline compatibility and removed Windows console logging that could fail on Vietnamese characters.
- `web/index.html`, `web/css/style.css`, `web/js/app.js`: unified filtered search results, Vietnamese microphone recognition with editable transcript and fallback, explicit image mode and content upload only with a configured encoder.
- `tests/test_search_enhanced.py`, `tests/search_browser_qa.mjs`: text, voice, image encoder and browser interaction checks. `README.md`, `docs/ROADMAP.md`, `docs/SEARCH_ARCHITECTURE.md` document setup and limits.

### Verification results

| Check | Result |
| --- | --- |
| Original direct-run text, voice, image and ranking checks | 21/21 passed |
| `python -m unittest discover -s tests -q` | 24/24 passed, including six new search tests and all admin/commerce/security tests |
| `node tests/browser_qa.mjs` | Passed original homepage, catalogue, product and search interactions at desktop, tablet, mobile and 320 px |
| `node tests/search_browser_qa.mjs` | Passed accent folding, category/size filters, editable voice transcript, explicit DEMO image mode and responsive result layouts at 1440, 820, 390 and 320 px with no horizontal overflow |
| Python `compileall` and JavaScript `node --check` | Passed |

To verify locally, start `python run_ui.py --no-browser`, open the homepage search, and compare `áo thun oversize` with `ao thun oversize`. The voice tab can accept an editable transcript even without microphone support. The default image tab accepts only three labeled samples. For actual image-content uploads, configure the encoder contract in `docs/SEARCH_ARCHITECTURE.md`; the automated test uses a local test encoder and confirms catalogue and uploaded images share that encoder.

For browser QA, run the server on port 8765 with a temporary `COGU_CATALOG_DB`, then set `COGU_BROWSER_QA_TEMP_DB=1` in the test terminal and run `node tests/search_browser_qa.mjs`. Phase 6 stops here.

## Phase 7 — AI shopping assistant: complete (2026-10-16)

### Changed files

- `application/shopping_ai_service.py`: grounded chat, factual comparison, in-stock recommendations, validated preferences and optional OpenAI-compatible LLM adapter. The provider selects evidence IDs; the server renders only current COGU facts. Invalid or unavailable provider responses use explicit DEMO fallback.
- `data/shopping_ai_repository.py`: SQLite preferences per customer and atomic rate-limit windows. `presentation/web_server.py` adds customer-scoped AI APIs, CSRF checks, request limits and owner-scoped order context.
- `web/js/shopping-ai.js`, `web/css/shopping-ai.css`, `web/js/shop.js`, `web/js/account.js` and the customer HTML pages: floating support chat, working 2–3 product comparison, saved preferences and personalized suggestions with loading/error labels. The homepage AI links now open working Phase 7 features.
- `tests/test_shopping_ai.py`, `tests/shopping_ai_browser_qa.mjs`: HTTP/provider/security and responsive interaction checks. `docs/SHOPPING_AI_ARCHITECTURE.md`, `docs/ROADMAP.md` and `README.md` document use and configuration.

### Verification results

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -q` | 28/28 passed, including four new AI HTTP tests; catalogue, commerce, admin, search and security regressions remain green |
| Original direct-run text, voice, image and ranking scripts | All passed (21 checks) |
| `node tests/browser_qa.mjs` | Passed homepage/search, Shop and product interactions at 1440, 820, 390 and 320 px; no horizontal overflow |
| `node tests/commerce_browser_qa.mjs` | Passed account, exact-variant cart, COD checkout and order history at four sizes |
| `node tests/shopping_ai_browser_qa.mjs` | Passed comparison, chat, saved preferences and recommendations at four sizes; no horizontal overflow |
| Python `compileall`, JavaScript `node --check` | Passed for changed files |

The default local run uses labeled deterministic DEMO responses. A local mock chat-completions provider was used to verify evidence-ID selection and rejection of invented IDs; no hosted LLM credentials were configured or claimed. To reproduce browser QA, start `python run_ui.py --no-browser --port 8765` with a disposable `COGU_CATALOG_DB`, set `COGU_BROWSER_QA_TEMP_DB=1` in the test terminal, then run `node tests/shopping_ai_browser_qa.mjs`. Screenshots are written to the OS temporary directory. Phase 7 stops here; outfit preview is outside this phase.

## Phase 8 — AI Outfit Preview and final integration: complete (2026-10-16)

### Changed files

- `application/outfit_preview_service.py`, `presentation/web_server.py`: validated outfit selection and five body types; live catalogue and in-stock checks; CSRF and three-request-per-minute rate limit; configured OpenAI Images Edit multipart or generic JSON image provider; validated image response and explicit sample fallback.
- `web/studio.html`, `web/css/studio.css`, `web/js/studio.js`: responsive AI Studio, real shirt/trousers/shoes choices, product detail links, visible progress and errors, body-type sample or provider preview, and fit disclaimer. Customer page navigation and homepage AI links now reach Studio; `run_ui.py` prints its URL.
- `images/outfit-sample-{slim,regular,curvy,tall,petite}.png`: five generated editorial sample photographs, clearly marked as unrelated to selected products.
- `tests/test_outfit_preview.py`, `tests/studio_browser_qa.mjs`: product/category/body-type validation, all sample modes, auth/CSRF/rate limit, both local mock provider contracts and responsive browser journey.
- `.env.example`, `README.md`, `docs/OUTFIT_PREVIEW.md`, `docs/FEATURE_STATUS.md`, `docs/INSTRUCTOR_DEMO.md`, `docs/ROADMAP.md`: provider setup, current feature modes, limitations and instructor walkthrough.

### Final verification results

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -q` | **32/32 passed**; all prior 28 tests plus four new outfit tests |
| Four original direct-run search/ranking scripts | **21/21 checks passed** |
| `node tests/browser_qa.mjs` and `node tests/search_browser_qa.mjs` | Passed storefront, catalogue and three search modes at 1440, 820, 390 and 320 px |
| `node tests/commerce_browser_qa.mjs` | Passed customer registration, exact-variant cart, COD checkout and private order history at four sizes |
| `node tests/shopping_ai_browser_qa.mjs` | Passed chat, comparison and recommendations at four sizes |
| `node tests/studio_browser_qa.mjs` | Passed catalogue choices, five body types, sample disclosure, result reset and Studio layout at four sizes |
| `node tests/admin_browser_qa.mjs` | Passed staff sign-in, catalogue/promotion operations, role-aware navigation and reports at four sizes |
| Python `compileall` and JavaScript `node --check` | Passed for changed files |

The provider paths were tested with local mock HTTP services. No paid hosted image generation was called. The default installation displays body-type sample photos with a **DEMO** label and explicitly states that the samples do not show selected products. To repeat Studio QA, start the server on port 8765 with a disposable `COGU_CATALOG_DB`, set `COGU_BROWSER_QA_TEMP_DB=1` in the test terminal, then run `node tests/studio_browser_qa.mjs`. Screenshots are saved to the OS temporary directory. Phase 8 stops here.

## Post-Phase 8 extension — Model gender and Gemini image API

- `web/studio.html`, `web/css/studio-gender.css`, `web/js/studio.js`: added accessible Nam/Nữ model selection. Changing gender resets the preview; submissions include gender and image descriptions reflect it.
- `application/outfit_preview_service.py`, `presentation/web_server.py`: validate gender on the server, add it to prompts/results and expose catalogue gender choices. Added a Gemini Interactions provider using server-side API keys and catalogue reference photos; missing or invalid provider output remains explicitly labeled DEMO.
- `images/outfit-sample-{male,female}-{slim,regular,curvy,tall,petite}.png`: ten gender/body-type sample assets. Five reuse existing Phase 8 images; five were generated for the missing combinations with a generic cream shirt, olive trousers, white shoes and neutral sage studio prompt. These samples are unrelated to selected catalogue items.
- `tests/test_outfit_preview.py`, `tests/studio_browser_qa.mjs`: added gender validation, all ten sample assets, Gemini local mock request/response test and browser gender switching.
- `.env.example`, `README.md`, `docs/OUTFIT_PREVIEW.md`, `docs/FEATURE_STATUS.md`, `docs/INSTRUCTOR_DEMO.md`: Gemini setup, model-choice instructions and DEMO limitations.

Verification on 16 October 2026: `python -m unittest tests.test_outfit_preview -q` **5/5 passed**; `python -m unittest discover -s tests -q` **33/33 passed**; `node tests/studio_browser_qa.mjs` **passed** on 1440, 820, 390 and 320 px with a disposable SQLite database. Gemini was tested against a local mock; no live hosted image-generation call was made.

### Local Gemini configuration and live check

`run_ui.py` now loads a private `.env` at startup without overriding shell variables; `.gitignore` excludes `.env`. The public `.env.example` remains empty. The user supplied a local key. A live Gemini request first exposed an unsupported PNG output setting, which was corrected to JPEG in `application/outfit_preview_service.py` and its local mock test. The subsequent live request reached Google but returned **HTTP 429**, reporting **zero Free Tier input tokens per minute** for `gemini-nano-banana-2.1`. No real image was returned; the customer interface correctly displayed a DEMO fallback. `python -m unittest tests.test_outfit_preview -q` passed **5/5** after the correction, and the complete suite passed **33/33** after the `.env` loader change.

## Store catalogue and purchase follow-up — three categories (2026-10-21)

- `scripts/build_catalog_seed.py`, `dataset/catalog_seed.json`, `images/catalog-31.png`–`images/catalog-45.png`: removed bags, watches and jackets from the sellable seed; added five shirts, five trousers and five footwear styles with matching illustrative product photos, VND prices, materials and size-specific stock. The current seed has **38 products and 189 variants**: Áo 11, Quần 12, Giày/dép 15. The original 12-product `dataset/products.json` remains unchanged for legacy demonstrations and tests.
- `data/catalog_models.py`, `data/catalog_repository.py`, `application/catalog_service.py`, `application/admin_service.py`, `data/catalog_search_repository.py`: one three-category allowlist now governs seeding, filtering, admin product writes and shop search. The legacy fixture endpoint remains available for regression tests, while the customer storefront and search read the current SQLite catalogue.
- `scripts/sync_catalog_scope.py`, `data/cogu_catalog.sqlite3`: updated the existing local store in one transaction after a SQLite backup under `data/backups/`. It removed seven off-scope items and inserted 15 new products without resetting allowed-product stock or historical order snapshots. Running it again adds/removes nothing. Off-scope wishlist and cart references are removed by existing foreign-key cascades.
- `web/index.html`, `web/shop.html`, `web/admin.html`, `web/studio.html`, `web/js/app.js`, `web/js/catalog-shared.js`, `web/js/admin.js`, `web/js/product.js`, `web/js/studio.js`, `web/css/style.css`, `application/outfit_preview_service.py`: customer and staff selectors now expose only Áo, Quần and Giày/dép. The homepage loads the live catalogue, displays a balanced 12-item selection, and keeps the technical search sample labeled DEMO. Shop cards, product details and Studio use current product IDs.
- `web/js/cart.js`: invalid promotion codes now restore the previous valid code and keep checkout usable. `data/admin_repository.py`, `presentation/web_server.py`, `web/account.html`, `web/js/account.js`, `web/css/commerce.css` list products eligible for a verified review directly in the customer account and link to each product's review section; already-reviewed products disappear from that list. `tests/test_catalog.py`, `tests/test_search_enhanced.py`, `tests/test_admin.py`, `tests/browser_qa.mjs`, `tests/search_browser_qa.mjs`, `tests/commerce_browser_qa.mjs` cover the catalogue, eligibility and promotion recovery.
- `README.md`, `docs/CATALOG_ARCHITECTURE.md`, `docs/FEATURE_STATUS.md`: current counts, migration instructions and purchase/review workflow.

### Verification

| Check | Result |
| --- | --- |
| SQLite `PRAGMA integrity_check`; current live category and variant counts | `ok`; 11 shirts, 12 trousers, 15 footwear styles, 189 variants |
| `python -m unittest discover -s tests -q` | **34/34 passed**; includes catalogue migration, cart/COD/idempotency, verified reviews, staff permissions, search and AI tests |
| `node tests/browser_qa.mjs`, `node tests/search_browser_qa.mjs` | Passed homepage, catalogue, product detail, all three search modes and responsive layouts at 1440, 820, 390 and 320 px |
| `node tests/commerce_browser_qa.mjs` | Passed registration, address, variant cart, invalid promotion recovery, COD checkout and private order history at four viewports |
| `node tests/admin_browser_qa.mjs`, `node tests/shopping_ai_browser_qa.mjs`, `node tests/studio_browser_qa.mjs` | Passed staff CRUD/promotion/roles, AI shopping features and Studio selection at four viewports using disposable databases |
| Python `compileall` and JavaScript `node --check` | Passed for changed source and browser QA files |

To verify the current store, run `python run_ui.py --no-browser`, visit `/shop` and filter each category; the expected totals are 11, 12 and 15. Open a product to select its size and color, add it to cart, and place a COD order. A review becomes available after staff complete an eligible order and appears publicly only after staff approval. For a separate database created before this update, run `python scripts/sync_catalog_scope.py` with the same `COGU_CATALOG_DB` setting before starting the server; the command creates a backup first.
