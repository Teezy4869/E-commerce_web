# COGU Fashion: Phase 1 architecture audit

Audit date: 2026-10-15. This document records the Phase 1 code snapshot before the storefront redesign. See [CATALOG_ARCHITECTURE.md](CATALOG_ARCHITECTURE.md) for the Phase 3 SQLite catalogue, [COMMERCE_ARCHITECTURE.md](COMMERCE_ARCHITECTURE.md) for the Phase 4 purchase flow, and [PHASE_PROGRESS.md](PHASE_PROGRESS.md) for current progress.

## Runtime and dependency flow

```text
run_ui.py -> presentation/web_server.py -> main.build_system()
                                         |
                                         +-> presentation/SearchUI, VoiceInput, ImageUpload
                                         |       -> application/QueryService, SpeechService,
                                         |          ImageService, SearchService, RankingService
                                         |                 -> data/ProductRepository, OrderRepository,
                                         |                    VectorIndex -> dataset/*.json
                                         +-> web/index.html, web/css/style.css, web/js/app.js
                                         +-> images/*

main.py -> same build_system() -> console demonstration
```

The three layers remain intact. `main.py` constructs the components and injects them into the HTTP handler. The HTTP handler is in Presentation and obtains repositories from the composition root for catalogue reads and the legacy order-list endpoint. Search flows go through Application services. Repositories load JSON at startup into memory; they do not write changes. `VectorIndex` computes cosine similarity over three-dimensional product embeddings with NumPy.

## Existing behavior

| Area | Current implementation | Limitation |
| --- | --- | --- |
| Text search | Keyword matching across product name, category, color and description; `RankingService` orders scores | English data and substring matching; no facets or pagination |
| Voice search | Browser Web Speech where available, then transcript is sent to `SpeechService` | Python service echoes a transcript; no server speech recognition |
| Image search | Sample image paths or direct 3D vectors; cosine similarity | Upload UI derives a vector from the **filename**, not image pixels |
| Order lookup | `SearchUI` -> `SearchService` -> `OrderRepository` | Legacy read-only demo; now requires administrator token in web API |
| Catalogue | Twelve JSON products, static photos | Prices are prototype USD amounts; no VND conversion or validated inventory |
| Orders | Three JSON sample orders | No account linkage, line items, transaction storage or payment integration |
| Frontend | One static HTML page, CSS and vanilla JavaScript | Current Luma search demo, not yet COGU storefront |

The original console order demonstration remains functional. No chatbot, product comparison, personalized recommendation, outfit preview, cart, checkout, account, or administration workflow exists yet.

## HTTP surface

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/`, `/index.html`, `/web/index.html` | Search demo page | Public |
| GET | `/css/*`, `/js/*`, `/web/*`, `/images/*` | Public static assets with extension and resolved-path checks | Public |
| GET | `/api/products` | Full product catalogue | Public |
| GET | `/api/system/info` | Layer and dataset metadata | Public |
| POST | `/api/search/text` | Keyword search | Public |
| POST | `/api/search/voice` | Transcript search | Public |
| POST | `/api/search/image` | Sample path or numeric-vector similarity search | Public |
| GET | `/api/orders` | Legacy full order list | `X-Admin-Token` |
| POST | `/api/search/order` | Legacy order lookup | `X-Admin-Token` |

`COGU_ADMIN_TOKEN` is read from the environment when the web server is built. Without it, order endpoints return 503; an absent or wrong token returns 403. The token is compared with `hmac.compare_digest`, and the frontend only sends it for order requests. It is a temporary administrator gate, not customer authentication. Run the demo on localhost; use HTTPS and proper session-based roles before any public deployment.

Static file requests are limited to the resolved `web/` and `images/` trees. Requests for source, `dataset/`, dot segments, backslashes, or symlinks outside those roots fail. Wildcard CORS has been removed. The server also sets `X-Content-Type-Options: nosniff` and `Referrer-Policy: same-origin`.

## Test and coverage audit

The repository's four original files use plain `test_*` functions with manual `__main__` calls. `unittest discover` finds none of those functions. Running the files directly executes **21 checks**: text 5, voice 4, image 7, ranking 5. There were no HTTP security, checkout, persistence or account tests. Phase 1 adds six `unittest` HTTP checks for the protected order APIs, static access, public text/voice/image search, invalid search inputs and fail-closed configuration.

## Remaining risks and incremental improvements

1. The shared administrator token is suitable only for a local demo. Add customer identity, password hashing, secure sessions, ownership checks and separate administrator roles before customer order history.
2. JSON datasets are loaded into memory and are not durable shopping storage. Add a transactional SQLite repository and migrations before cart or checkout.
3. Search input validation is partial. Enforce field length, vector dimensions, request limits, output error handling and rate limits consistently across endpoints.
4. The current upload UI implies visual recognition while it maps file names to synthetic vectors. Label it clearly until a real encoder is integrated.
5. Hardcoded product prices are USD-era prototype values. Curate a Vietnamese fashion catalogue with integer VND prices and real stock before enabling checkout.
6. A local HTTP server does not provide TLS, account sessions, CSRF defense, payments or production deployment controls. Add these as the matching features are implemented.
7. The UI currently uses English brand and sample data. COGU branding, Vietnamese copy and responsive storefront flows belong to the next implementation phase.

