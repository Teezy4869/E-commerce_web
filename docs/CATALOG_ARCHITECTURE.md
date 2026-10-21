# Phase 3 catalogue architecture

The storefront catalogue is separate from the original 12-product multimodal search fixture. The original `dataset/products.json` and `data/ProductRepository` remain available for the Assignment 06 regression tests and console demo. The web search endpoints use a read-only `CatalogSearchRepository` adapter so text, voice and image search can find all 38 current shop products without replacing the original search services. The shop and product pages read the SQLite catalogue through the same three-layer structure:

```text
Presentation: web/shop.html, web/product.html, web/js/*, WebServer
    -> Application: CatalogService (query validation)
        -> Data: CatalogRepository (SQLite products, product_variants, product_images)
                 CatalogSearchRepository (search adapter)
```

`dataset/catalog_seed.json` has 38 curated products and 189 variant records: 11 shirts, 12 trousers and 15 footwear styles. The five original shoe items are mapped from the legacy fixture without changing it; jackets, bags and watches are not sold in the current catalogue. `scripts/build_catalog_seed.py` reproduces the seed. On first use, `CatalogRepository` creates `data/cogu_catalog.sqlite3` (or the path given by `COGU_CATALOG_DB`) and seeds it in a transaction. Reopening an existing database does not reset changed stock. For an existing pre-change database, `python scripts/sync_catalog_scope.py` creates a SQLite backup, removes off-scope products and inserts the 15 additions without resetting existing allowed products or order snapshots. Each request uses a fresh SQLite connection and closes it, which is safe for the threaded local HTTP server.

## Entities and inventory

- `Product`: id, URL slug, Vietnamese name and description, category, material, integer VND price, main image, editorial flags.
- `ProductVariant`: unique SKU and unique `(product_id, color, size)`, each with its own nonnegative stock quantity.
- `product_images`: ordered images associated with a product and color. The Essential tee has green and ivory product photos; selecting a color changes the gallery image.

Stock is always queried by exact slug, color and size. For example, the Essential tee has green M stock 7, green L stock 0 and ivory M stock 14. Product summary stock is the sum of its variants and is only for catalogue display.

## Public catalogue API

| Method and path | Response |
| --- | --- |
| `GET /api/catalog/products` | Paginated summaries with `total`, `page`, `page_size`, `pages`. Optional `q`, `category`, `color`, `size`, `min_price`, `max_price`, `sort`, `page`, `page_size`. |
| `GET /api/catalog/products/{slug}` | Product, ordered images, all variants and up to four related products in the same category. |
| `GET /api/catalog/stock?slug=...&color=...&size=...` | One exact variant record, including SKU and stock. |
| `GET /api/catalog/facets` | Categories, colors, sizes and price limits for filter controls. |

Sorting accepts `newest`, `popular` (editorially flagged), `price_asc`, `price_desc` and `name`. The server bounds pagination, numeric prices, filter length and allowed category/sort values. SQL values are parameterized; sort expressions come from an allowlist. The API exposes only product data, no customer or order records. The original `/api/products` response remains the 12-product fixture for compatibility; text/voice/image HTTP search now covers the 38-product catalogue. The adapter retains original English fields and vectors for matching legacy shoe products; image search uses a configured image-content encoder when available or clearly labeled deterministic sample mode by default.

## Pages and current scope

`/shop` provides category, color, size, price and text filters; sort order; and pagination. `/product?slug=...` provides the gallery, details, material, color/size selectors, size guidance, exact stock and related items. The homepage links to the shop and its original product modal links to full product details. Cards and the mobile navigation work with keyboard controls. No add-to-cart or payment action is claimed in Phase 3.

Images `images/catalog-13.png` through `catalog-45.png` and `catalog-17-ivory.png` were generated with the built-in image generation tool as matching studio product photographs on warm off-white backgrounds. Prompts specified the garment or footwear type and color, soft natural shadow, and no logo or text. Existing `store-product-*.webp` images continue to illustrate the legacy fixture, although only its shoe items appear in the current shop. Generated product photos are illustrative and do not guarantee real-world materials or manufacturing details.
