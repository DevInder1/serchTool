import json
import os
import urllib.parse

import httpx

import apify_common

STORES = {
    "amazon": "Amazon.in",
    "flipkart": "Flipkart",
}

_DEFAULT_INPUT = '{"startUrls": [{"url": "{url}"}], "maxItems": {limit}}'

_CATEGORIES = [
    {"label": "Electronics", "amazon": "slug:electronics", "flipkart": "electronics"},
    {"label": "Mobiles", "amazon": "search:mobiles", "flipkart": "mobiles"},
    {"label": "Computers & Laptops", "amazon": "slug:computers", "flipkart": "laptops"},
    {"label": "Fashion", "amazon": "slug:apparel", "flipkart": "clothing"},
    {"label": "Home & Kitchen", "amazon": "slug:kitchen", "flipkart": "home kitchen"},
    {"label": "Beauty", "amazon": "slug:beauty", "flipkart": "beauty products"},
    {"label": "Toys & Baby", "amazon": "slug:toys", "flipkart": "toys"},
    {"label": "Sports & Fitness", "amazon": "slug:sports", "flipkart": "sports fitness"},
    {"label": "Books", "amazon": "slug:books", "flipkart": "books"},
]


def _amazon_url(spec: str) -> str:
    kind, _, value = spec.partition(":")
    if kind == "search":
        return f"https://www.amazon.in/s?k={urllib.parse.quote_plus(value)}&s=popularity-rank"
    return f"https://www.amazon.in/gp/bestsellers/{value}/"


def _flipkart_url(term: str) -> str:
    return f"https://www.flipkart.com/search?q={urllib.parse.quote_plus(term)}&sort=popularity"


def list_bestsellers(store: str = "amazon") -> list[dict]:
    store = store.lower()
    if store not in STORES:
        store = "amazon"
    items: list[dict] = []
    for cat in _CATEGORIES:
        url = _amazon_url(cat["amazon"]) if store == "amazon" else _flipkart_url(cat["flipkart"])
        items.append({"category": cat["label"], "store": store, "url": url})
    return items


def _category_url(store: str, category: str) -> str | None:
    for item in list_bestsellers(store):
        if item["category"].lower() == category.lower():
            return item["url"]
    return None


def store_actor(store: str) -> str:
    return os.getenv(f"APIFY_{store.upper()}_ACTOR", "").strip()


def is_live(store: str) -> bool:
    return bool(apify_common.token() and store_actor(store))


def live_stores() -> list[str]:
    return [s for s in STORES if is_live(s)]


def _render_input(url: str, limit: int) -> dict:
    template = os.getenv("APIFY_BESTSELLER_INPUT_TEMPLATE", _DEFAULT_INPUT)
    safe_url = json.dumps(url)[1:-1]
    rendered = template.replace("{url}", safe_url).replace("{limit}", str(int(limit)))
    return json.loads(rendered)


async def fetch_items(store: str, category: str, limit: int = 30) -> list[dict]:
    store = store.lower()
    actor = store_actor(store)
    url = _category_url(store, category)
    if not (apify_common.token() and actor and url):
        return []
    async with httpx.AsyncClient(timeout=apify_common.timeout()) as client:
        raw = await apify_common.run_actor(client, actor, _render_input(url, limit), limit)
    results: list[dict] = []
    for item in raw[:limit]:
        mapped = apify_common.map_item(item)
        if mapped:
            mapped["source"] = f"{STORES[store]} bestsellers"
            results.append(mapped)
    return results
