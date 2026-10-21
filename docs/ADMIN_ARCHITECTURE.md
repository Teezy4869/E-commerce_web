# Phase 5 admin and store operations

## Architecture and data

The original three layers remain: `presentation/web_server.py` serves `/admin`, its JSON API and customer endpoints; `application/admin_service.py` validates input and authorizes use cases; `data/admin_repository.py` persists changes in the same SQLite database as the catalogue and orders. The separate staff UI uses `web/admin.html`, `web/css/admin.css` and `web/js/admin.js`. Existing text, voice and image search services and the original JSON fixtures remain in place. Product mutations refresh the web search index; catalogue, cart and checkout reads use the updated SQLite rows.

The admin repository adds `staff_users`, `staff_sessions`, `admin_audit`, `product_reviews`, `support_requests`, `order_events` and payment recording fields. The commerce repository adds `promotion_codes` and seeds the prior `COGU10` and `FREESHIP` examples. Existing databases migrate on startup without deleting orders or customers. Product/variant, stock, promotion and order changes are stored with a staff audit entry. Customer reviews link to an eligible completed purchase and require staff approval before publication.

## Role policy

| Role | Allowed work |
| --- | --- |
| Administrator | All store operations and staff account/role management |
| Manager | Dashboard, reports and all store operations except staff accounts |
| Sales Staff | Dashboard and reports; read products/orders; update order and COD payment states; manage promotions |
| Warehouse Staff | Dashboard and reports; read products/orders; manage variants, stock and shipment states |
| Customer Support Staff | Read products/orders; moderate reviews; read and answer support requests |

The server checks permissions on every admin endpoint. The UI also hides unavailable actions for clarity. Customers have separate sessions and cannot enter `/api/admin/*`. A staff session uses an opaque cookie scoped to `/api/admin`, `HttpOnly`, `SameSite=Strict` and a 12-hour expiry; state-changing calls require a CSRF token. Set `COGU_COOKIE_SECURE=1` under HTTPS. Passwords use per-account salted PBKDF2 hashes. Deactivating a staff account revokes its sessions. No staff account or fixed password is created automatically: run `python scripts/seed_admin_demo.py` to provision five roles with generated passwords, and use `--reset` to rotate them.

## APIs and workflows

| API | Operations |
| --- | --- |
| `/api/admin/login`, `/session`, `/logout` | Staff login, current permissions and logout |
| `/api/admin/dashboard`, `/reports` | Current order/payment/stock counts, daily sales, top products and category inventory |
| `/api/admin/products`, `/products/{id}` | Product list, detail, create, update and delete |
| `/api/admin/products/{id}/variants`, `/variants/{id}`, `/variants/{id}/stock` | Color/size/SKU records; the dedicated stock-adjustment endpoint requires a reason |
| `/api/admin/orders`, `/orders/{reference}` | Order queue and details with state history |
| `/api/admin/orders/{reference}/status`, `/shipment`, `/payment` | Controlled order, delivery and staff-recorded COD transitions |
| `/api/admin/promotions`, `/promotions/{code}` | Percentage, amount and free-shipping codes with dates, limits and minimum spend |
| `/api/admin/reviews`, `/reviews/{id}` | Moderate verified-purchase reviews |
| `/api/admin/support`, `/support/{id}` | Read and answer customer support tickets |
| `/api/admin/staff`, `/staff/{id}` | Administrator-only account creation, role changes and deactivation |

Customers use `/api/account/reviews` and `/api/account/support` to see or submit only their own records; public product detail returns approved reviews only. `/api/promotions` lists currently usable promotions. The checkout transaction rechecks code eligibility and increments use count with the order, so a changed admin promotion affects cart quotes and checkout immediately.

Orders start confirmed, shipment pending and COD pending. Shipment advances pending → packing → shipped → delivered. Staff can record COD collection only after delivered, then mark the order fulfilled. Cancellation before shipment and collection restores exact variant stock and promotion usage. Order, payment and shipment remain separate records with staff event history. Reports label collected revenue as **staff-recorded COD**, excluding refunded payments. Carrier delivery, COD collection and refund updates are internal demo records, never third-party verified events.

This remains a local demonstration. Public deployment needs HTTPS, `COGU_COOKIE_SECURE=1`, login rate limiting, backups, staff password recovery and operational proof for real delivery or payment confirmation. Additional AI features belong to a later phase.
