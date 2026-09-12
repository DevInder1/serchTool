# serchTool — Product Finder

A small web app that searches the web for **product listings and prices**, filtered by **location** (defaults to *Bangalore, India*, and you can change it to any city or country).

With zero setup it returns **real marketplace searches** (OLX, Facebook, Instagram, IndiaMART, Quikr) as one-click cards, and it layers in **priced product listings** the moment you add an API key. It never shows invented listings or placeholder images.

## Live demo

Run it locally — it's a single command and needs no API keys or hosting:

```bash
git clone https://github.com/DevInder1/serchTool && cd serchTool && ./run.sh
```

Then open **[http://localhost:8000](http://localhost:8000)** and search. Out of the box you get accurate deep-links into each Indian marketplace for your product; add a key (see below) to also get priced listings.

## Quick start

```bash
git clone https://github.com/DevInder1/serchTool
cd serchTool
./run.sh
```

Then open **http://localhost:8000**. Type a product, set a location, and search.

> On Windows, or if you prefer to run it manually:
> ```bash
> cd backend
> python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
> pip install -r requirements.txt
> uvicorn main:app --reload
> ```

## Priced listings (optional)

Out of the box the app shows only accurate results: real marketplace search links, plus any keyed providers. To also get priced product listings from Google Shopping, add a free [SerpAPI](https://serpapi.com/) key:

```bash
export SERPAPI_KEY="your_key_here"   # Windows: set SERPAPI_KEY=your_key_here
./run.sh
```

The app auto-detects the key and adds real priced results. No key = you still get the accurate marketplace search cards.

### Demo/sample data (off by default)

There is a `mock` provider that fabricates realistic-looking sample listings — useful only for previewing the UI. It is **disabled by default** so it never pollutes real searches. Turn it on explicitly if you want it:

```bash
export ENABLE_MOCK=1
./run.sh
```

## How it works

```
Browser (static/index.html)
        │  product + location + price filters
        ▼
FastAPI backend  ──►  Provider layer (runs in parallel)
        │                ├─ serpapi       (Google Shopping — real prices, needs key)
        │                ├─ apify         (real OLX/Facebook/Instagram listings, needs token)
        │                ├─ marketplaces  (OLX, Facebook, Instagram, IndiaMART, Quikr — free links)
        │                └─ mock          (sample data — off unless ENABLE_MOCK=1)
        │                      │
        │             normalize → dedupe → price filter → sort by price → cache 1h
        ▼
Results grid + CSV export
```

## Features

- Location selector (any city/country), default **Bangalore, India**
- Min/max **price** filters and source selection
- Results **sorted by price**, deduplicated across providers
- **CSV export** of the current results
- 1-hour in-memory cache per query
- Light/dark theme, responsive layout, single-file frontend (no build step)

## Add another source

Search providers are pluggable. To add one (eBay, Amazon, Bing, a marketplace, etc.):

1. Create `backend/providers/yourprovider.py` with a class extending `Provider` and implementing `async def search(self, req) -> list[Listing]`.
2. Add an `enabled` property (e.g. return `True` only when its API key is present).
3. Register an instance in the `_ALL_PROVIDERS` list in `backend/main.py`.

Each provider returns the shared `Listing` shape, so the frontend needs no changes.

## Indian marketplaces (OLX, Facebook, Instagram, IndiaMART, Quikr)

None of these sites offer a free (or public) product-search API, and scraping them
violates their Terms of Service and is actively blocked. Instead, the **`marketplaces`**
provider is free and ToS-safe: for each search it builds a **pre-filled deep-link** into
every site with your product and location baked into the URL. These appear as result cards
("Search OLX for … in Bangalore →") that open live results on each site in a new tab.

This is the honest, sustainable way to include them — you get one-click access to real
listings on every marketplace without running fragile scrapers that break and risk bans.
For genuine Instagram brand/creator data you would need the Instagram Graph API (business
accounts only), which is out of scope here.

### Real marketplace data via Apify (optional, keyed)

If you want actual listing *data* (title, price, seller) pulled back from OLX, Facebook, or
Instagram rather than just links, the **`apify`** provider fetches it through hosted
[Apify](https://apify.com/) actors. It stays disabled until you set a token **and** point it
at one or more actors:

```bash
export APIFY_TOKEN="your_apify_token"
export APIFY_OLX_ACTOR="username/olx-scraper-actor"          # pick actors from the Apify Store
export APIFY_FACEBOOK_ACTOR="username/facebook-marketplace-actor"
export APIFY_INSTAGRAM_ACTOR="apify/instagram-scraper"
./run.sh
```

Each configured actor runs in parallel per search; results are merged and normalized into the
shared `Listing` shape. Recognized sites: `olx`, `facebook`, `instagram`, `quikr`, `indiamart`
(via `APIFY_<SITE>_ACTOR`).

Because every actor takes a different input and returns a different schema, the provider is
built to adapt:

- **Input** — by default it sends `{"search": "<query>", "location": "<location>", "maxItems": <n>}`.
  Override the shape for a specific actor with `APIFY_INPUT_TEMPLATE` (a JSON string using the
  `{query}`, `{location}`, `{limit}` placeholders).
- **Output** — it flexibly maps common field names (`title`/`name`, `price`/`priceValue`,
  `url`/`link`, `thumbnail`/`image`, …). Items without a title and URL are skipped.
- `APIFY_TIMEOUT` (seconds, default 90) caps how long a run may take.

Apify actors are **paid/metered** and subject to each marketplace's own terms — you choose which
actors to run and are responsible for that usage. When no token is set, this provider is simply
absent and the free link-cards remain.

## API

`POST /api/search`
```json
{
  "query": "leather sofa",
  "location": "Bangalore, India",
  "min_price": null,
  "max_price": null,
  "sources": null,
  "limit": 40
}
```

`GET /api/providers` — lists providers and whether each is currently enabled.
