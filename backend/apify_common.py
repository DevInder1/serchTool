import os
import re
from typing import Any, Optional

import httpx

ENDPOINT = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"

TITLE_KEYS = ["title", "name", "productName", "heading", "adTitle"]
URL_KEYS = ["url", "link", "productUrl", "itemUrl", "adUrl", "permalink"]
PRICE_KEYS = ["price", "priceValue", "amount", "price_value", "priceAmount"]
CURRENCY_KEYS = ["currency", "priceCurrency", "currencyCode"]
SELLER_KEYS = ["seller", "sellerName", "shopName", "source", "user", "username", "brand"]
IMAGE_KEYS = ["image", "imageUrl", "thumbnail", "img", "mainImage", "displayUrl"]


def token() -> str:
    return os.getenv("APIFY_TOKEN", "").strip()


def timeout() -> int:
    return int(os.getenv("APIFY_TIMEOUT", "90"))


def first(item: dict, keys: list[str]) -> Optional[Any]:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[\d,]+(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


async def run_actor(client: httpx.AsyncClient, actor: str, payload: dict, limit: int) -> list[dict]:
    resp = await client.post(
        ENDPOINT.format(actor=actor),
        params={"token": token(), "maxItems": limit},
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("items", []) if isinstance(data, dict) else []


def map_item(item: dict) -> Optional[dict]:
    if not isinstance(item, dict):
        return None
    title = first(item, TITLE_KEYS)
    url = first(item, URL_KEYS)
    if not title or not url:
        return None
    seller = first(item, SELLER_KEYS)
    image = first(item, IMAGE_KEYS)
    return {
        "title": str(title),
        "price": to_float(first(item, PRICE_KEYS)),
        "currency": first(item, CURRENCY_KEYS),
        "seller": str(seller) if seller else None,
        "image": str(image) if image else None,
        "url": str(url),
    }
