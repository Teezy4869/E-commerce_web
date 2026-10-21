# Phase 7 — COGU shopping assistant

## Architecture and data boundaries

- **Presentation:** `presentation/web_server.py` exposes the AI endpoints; `web/js/shopping-ai.js` provides the floating chat and Shop comparison, while `web/js/account.js` manages preferences and recommendations.
- **Application:** `application/shopping_ai_service.py` validates inputs, retrieves live catalogue and owner-scoped order facts, ranks available products, and calls the optional LLM adapter.
- **Data:** `data/shopping_ai_repository.py` stores per-customer preferences and atomic rate-limit windows in the same SQLite database as the catalogue and accounts.

The LLM receives a small list of evidence IDs and their COGU facts. It returns only selected IDs; the server renders the factual answer/analysis/explanation from its own evidence strings. Unknown IDs, invalid JSON, network failures and missing configuration fall back to a clearly labeled deterministic **DEMO** mode. No free-form provider text is shown as verified store information. Prices, materials, colors, sizes and total stock are read from the current catalogue. Customers can ask about **their own** recent orders only after session authentication; other customers' orders and legacy admin order fixtures are never included. Staff-recorded COD and delivery states are explicitly described as internal demo records. A question about a missing exchange/return policy says that no policy has been published in this demo and points to account support.

## Configuration

Set these server environment variables to use an OpenAI-compatible **chat completions** endpoint:

```powershell
$env:COGU_LLM_URL = 'https://your-provider.example/v1/chat/completions'
$env:COGU_LLM_MODEL = 'your-model-id'
$env:COGU_LLM_API_KEY = 'your-server-side-key'
python run_ui.py --no-browser
```

The URL must be HTTPS, except HTTP on `127.0.0.1` or `localhost` for a local model. The adapter sends JSON with `model`, `temperature: 0`, `max_tokens` and two `messages`, using `Authorization: Bearer`. The provider must return `choices[0].message.content` containing JSON such as `{"ids":["size"]}`. The chosen IDs must match supplied evidence. The API key remains on the server and is never returned to the browser. The provider request has an 8-second timeout and a bounded response. With a remote provider, relevant product and authenticated order facts are sent to that provider; the chat UI discloses this.

`GET /api/ai/capabilities` reports configured or DEMO mode without revealing credentials. Runtime provider errors are handled per request with the DEMO label. A configured provider was verified using a local test server, not a live hosted model.

## API and authorization

| Route | Access | Behavior |
| --- | --- | --- |
| `POST /api/ai/chat` | Public; customer CSRF when signed in | `{"message":"..."}`; customer-owned order facts only for authenticated sessions |
| `POST /api/ai/compare` | Public; customer CSRF when signed in | `{"product_ids":[id,id]}`; exactly 2–3 distinct existing products |
| `GET /api/ai/preferences` | Customer session | Saved style, colors and budget, plus valid choices |
| `PUT /api/ai/preferences` | Customer session and CSRF | Validated style, up to five catalogue colors, budget 0–50,000,000 VND |
| `GET /api/ai/recommendations` | Customer session | Up to six in-stock products within budget, ranked by chosen colors, style terms and catalogue flags |

JSON writes are size-limited to 8 KB. Chat messages are capped at 400 characters. Rate windows are stored atomically in SQLite by customer ID or client IP: 20 chat requests/minute; 10 comparison or recommendation requests/minute. A limit breach returns HTTP 429. All recommendation explanations are assembled from actual product facts. A zero budget means no maximum; if no stocked product fits a set budget, the UI shows an empty result instead of inventing one.

## Verification

`tests/test_shopping_ai.py` checks preference persistence and isolation, input/CSRF validation, real catalogue comparison data, owner-scoped order answers, rate limiting, provider evidence selection and invalid-provider fallback. `tests/shopping_ai_browser_qa.mjs` checks the three shopping features and 1440, 820, 390 and 320 px layouts against a disposable SQLite database.
