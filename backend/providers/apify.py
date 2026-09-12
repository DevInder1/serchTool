import json
import os
import re
from typing import Any, Optional

import httpx

from models import Listing, SearchRequest
from providers.base import Provider

_ENDPOINT = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
_DEFAULT_INPUT = '{"search": "{query}", "location": "{location}", "maxItems": {limit}}'
_SITES = ["olx", "facebook", "instagram", "quikr", "indiamart"]

_TITLE_KEYS = ["title", "name", "productName", "heading", "adTitle"]
_URL_KEYS = ["url", "link", "productUrl", "itemUrl", "adUrl", "permalink"]
_PRICE_KEYS = ["price", "priceValue", "amount", "price_value", "priceAmount"]
_CURRENCY_KEYS = ["currency", "priceCurrency", "currencyCode"]
_SELLER_KEYS = ["seller", "sellerName", "shopName", "source", "user", "username"]
_LOCATION_KEYS = ["location", "city", "address", "region", "area"]
_IMAGE_KEYS = ["image", "imageUrl", "thumbnail", "img", "mainImage", "displayUrl"]


def _first(item: dict, keys: list[str]) -> Optional[Any]:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


def _to_float(value: Any) -> Optional[float]:
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


class ApifyProvider(Provider):
    name = "apify"
    category = "data"

    def __init__(self) -> None:
        self.token = os.getenv("APIFY_TOKEN", "").strip()
        self.timeout = int(os.getenv("APIFY_TIMEOUT", "90"))
        self.input_template = os.getenv("APIFY_INPUT_TEMPLATE", _DEFAULT_INPUT)
        self.actors: dict[str, str] = {}
        for site in _SITES:
            actor = os.getenv(f"APIFY_{site.upper()}_ACTOR", "").strip()
            if actor:
                self.actors[site] = actor

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.actors)

    def _render_input(self, req: SearchRequest) -> dict:
        query = json.dumps(req.query)[1:-1]
        location = json.dumps(req.location)[1:-1]
        rendered = (
            self.input_template.replace("{query}", query)
            .replace("{location}", location)
            .replace("{limit}", str(int(req.limit)))
        )
        return json.loads(rendered)

    async def _run_actor(self, client: httpx.AsyncClient, actor: str, req: SearchRequest) -> list[dict]:
        resp = await client.post(
            _ENDPOINT.format(actor=actor),
            params={"token": self.token, "maxItems": req.limit},
            json=self._render_input(req),
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("items", []) if isinstance(data, dict) else []

    def _map(self, item: dict, site: str, req: SearchRequest) -> Optional[Listing]:
        if not isinstance(item, dict):
            return None
        title = _first(item, _TITLE_KEYS)
        url = _first(item, _URL_KEYS)
        if not title or not url:
            return None
        seller = _first(item, _SELLER_KEYS)
        location = _first(item, _LOCATION_KEYS)
        image = _first(item, _IMAGE_KEYS)
        return Listing(
            title=str(title),
            price=_to_float(_first(item, _PRICE_KEYS)),
            currency=_first(item, _CURRENCY_KEYS),
            seller=str(seller) if seller else None,
            location=str(location) if location else req.location,
            source=f"{site} (apify)",
            product_url=str(url),
            image_url=str(image) if image else None,
        ).with_timestamp()

    async def search(self, req: SearchRequest) -> list[Listing]:
        results: list[Listing] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for site, actor in self.actors.items():
                try:
                    items = await self._run_actor(client, actor, req)
                except Exception:  # noqa: BLE001
                    continue
                for item in items[: req.limit]:
                    listing = self._map(item, site, req)
                    if listing:
                        results.append(listing)
        return results
