# COGU Fashion — instructor demonstration (about 8 minutes)

## Before the session

From the project directory, optionally set `COGU_CATALOG_DB` to a fresh SQLite path. Run `python scripts/seed_admin_demo.py` once for staff accounts and save the generated passwords. Start `python run_ui.py --no-browser`, then open `http://127.0.0.1:8080/`. No external AI key is needed for the default demonstration. Keep another browser tab ready at `/admin` if demonstrating operations.

## Walkthrough

1. **Homepage and architecture (45 seconds):** Show the responsive COGU storefront, category links and Demo Lab. Explain Presentation → Application → Data and the SQLite catalogue beside the original search fixtures.
2. **Search (75 seconds):** Search for `áo thun oversize` and `ao thun oversize`; show matching results. Use a Vietnamese voice transcript or the typed fallback. In image search, point to the explicit **DEMO** sample label unless an encoder has been configured.
3. **Catalogue and shopping (90 seconds):** Open `/shop`, filter by category, inspect a product's image gallery, colors, sizes and exact-variant stock. Sign in or register, add an exact variant to cart, choose an address and place one COD order. Show the unique reference and private order history. State that COD has not been paid online.
4. **AI shopping assistant (75 seconds):** Ask the floating chat about a product or your own order. Select two products in Shop and compare price, material, available colors/sizes and stock. On `/account#shopping-preferences`, save style, colors and a VND budget; show actual in-stock recommendations and their **DEMO** or provider label.
5. **AI Studio (75 seconds):** Open `/studio`, select one shirt, one pair of trousers and one pair of shoes, then choose model gender (Nam/Nữ) and one of the five body types. Generate the preview. In the default run, show the labeled sample and clearly explain that it **does not show the selected products**. Point to the product links and fit disclaimer. Explain that optional Gemini or another image provider receives catalogue reference photos, never personal photos.
6. **Store operations (60 seconds):** Sign in at `/admin` with a generated staff account. Show live stock/order panels and role-restricted actions. Explain that payment collection and delivery statuses are internal staff records; there is no external processor or carrier verification.

If live AI services are configured, first check `/api/search/capabilities`, `/api/ai/capabilities` and `/api/outfit/catalog` to see the modes reported by the server. Never describe sample previews or staff-recorded statuses as third-party verified results.
