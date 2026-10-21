# Phase 4 commerce architecture

COGU keeps the existing three layers. `presentation/web_server.py` handles HTTP, cookie sessions and CSRF checks. `application/commerce_service.py` validates input, hashes passwords and calculates VND quotes. `data/commerce_repository.py` owns SQLite reads and writes. Catalogue rows remain in `data/catalog_repository.py`; the original JSON search fixtures and text, voice and image services are unchanged.

## Storage and lifecycle

The commerce tables live in the same SQLite file as `products` and `product_variants` (default `data/cogu_catalog.sqlite3`, configurable with `COGU_CATALOG_DB`). New tables are `customers`, `customer_sessions`, `delivery_addresses`, `wishlist_items`, `cart_items`, `customer_orders`, `customer_order_items`, `customer_payments`, `customer_shipments` and `checkout_requests`. Cart rows reference `product_variants.id`. Orders snapshot item prices, names, SKUs and delivery address so later catalogue or address changes do not rewrite history.

Checkout runs in one `BEGIN IMMEDIATE` transaction. It checks the customer address, fetches exact variant cart rows, recalculates prices from current product records, conditionally decrements stock, creates the order and separate payment/shipment records, records the idempotency key, and clears the cart. Any failure rolls back all writes. A retry with the same key and same address/payment/promotion returns the original order; reuse with different inputs is rejected. The order reference uses `COGU-YYYYMMDD-<12 random hex digits>` and a unique database constraint.

Order state begins `confirmed`, payment state `pending_cod`, and shipment state `pending`. The site accepts COD only. The order is persisted, while payment is **not verified or collected** online. Delivery is 30,000 VND below 1,500,000 VND after discount and free above it. The demo codes `COGU10` (10%, capped at 100,000 VND) and `FREESHIP` are seeded into the Phase 5 promotion table. Staff can manage additional codes; all codes are validated and calculated on the server. Other payment methods are rejected.

## Customer HTTP API

| Route | Method | Meaning |
| --- | --- | --- |
| `/api/auth/register`, `/api/auth/login` | POST | Create or enter an account; set session cookie |
| `/api/auth/me`, `/api/auth/logout` | GET, POST | Read session/CSRF token or revoke it |
| `/api/account/profile` | PUT | Change own name and phone |
| `/api/account/addresses` | GET, POST | List or add own addresses |
| `/api/account/addresses/{id}` | PUT, DELETE | Change or remove own address |
| `/api/account/wishlist` | GET, POST | List or save products |
| `/api/account/wishlist/{product_id}` | DELETE | Remove saved product |
| `/api/cart` | GET, POST, PUT | Get server quote, add exact variant, set quantity |
| `/api/cart/{variant_id}` | DELETE | Remove exact variant |
| `/api/checkout` | POST | Place or retry COD order |
| `/api/account/orders`, `/api/account/orders/{reference}` | GET | List or read only the signed-in customer's orders |

Authenticated writes require `X-CSRF-Token` from `/api/auth/me` or the login/register response. The session token is an opaque random value in an `HttpOnly; SameSite=Lax` cookie; only its SHA-256 hash is stored. Set `COGU_COOKIE_SECURE=1` when serving exclusively over HTTPS so the cookie also gets `Secure`. Passwords use PBKDF2-HMAC-SHA256 with a random per-user salt. Order and address queries always include `customer_id`. The legacy `/api/orders` and `/api/search/order` still require the separate `COGU_ADMIN_TOKEN` and access only the original sample order fixture.

## Frontend and limits

`/account` supports register, login, profile, addresses, wishlist and history. `/product` adds the chosen color/size variant to the cart. `/cart` updates quantity, applies demo promotions and submits COD. `/order?ref=...` reads the private saved confirmation. The site never claims a completed payment or shipment from these initial records.

This is a local demonstration. Phase 5 adds internal staff-recorded payment and shipment changes, without a payment provider or delivery carrier. It has no password reset, email verification or production rate limiting. Deploying publicly requires HTTPS, `COGU_COOKIE_SECURE=1`, backup/retention policy, abuse controls and operational proof for payment/shipment changes.
