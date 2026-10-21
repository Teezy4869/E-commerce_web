# COGU Fashion — academic demonstration feature status

| Feature | Status in default local run | Source and limitation |
| --- | --- | --- |
| Storefront, Shop, detail pages, filters and variants | Working | SQLite catalogue; 38 seeded demo products across Áo (11), Quần (12), Giày/dép (15), editable by staff |
| Customer account, addresses, wishlist, cart, COD checkout and private order history | Working | Persistent SQLite; COD is payable on delivery, not an online verified payment |
| Admin dashboard, inventory, promotions, reviews, support and reports | Working after staff setup | Role permissions; staff-recorded collection/delivery are internal demo events |
| Vietnamese text search and voice transcript search | Working | Catalogue search; browser microphone recognition depends on browser permission/support |
| Image search | DEMO samples by default | Genuine content search requires a configured image encoder and shared product/query model |
| Shopping chatbot, comparison and recommendations | DEMO rules by default | Factual catalogue/customer data; optional configured LLM chooses server-approved evidence IDs |
| AI Studio outfit preview | DEMO model-gender and body-type samples by default | Optional Gemini, OpenAI or JSON image provider uses selected product photos; sample photos are unrelated to selected items |

Every preview warns that generated or sample imagery cannot guarantee fit, color or real garment appearance. No customer photograph is requested or stored. The default demo can be presented offline after local setup; optional third-party AI services are not required for the academic walkthrough.

## Release boundary

This is a local academic system, not a production commerce launch. The code has server-side validation, customer ownership checks, role permissions, CSRF for signed-in writes and limits for AI requests. Public deployment would also need operational HTTPS, secure cookie settings, backups, secret management, monitoring, stronger abuse controls and verified external payment/shipping integrations if those claims are desired.
