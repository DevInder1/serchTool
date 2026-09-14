import urllib.parse

STORES = {
    "amazon": "Amazon.in",
    "flipkart": "Flipkart",
}

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
