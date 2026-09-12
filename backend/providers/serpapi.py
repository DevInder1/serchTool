import os
import re
from typing import Optional

import httpx

from models import Listing, SearchRequest
from providers.base import Provider

_ENDPOINT = "https://serpapi.com/search.json"


def _parse_price(raw: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    if not raw:
        return None, None
    currency = None
    symbols = {"₹": "INR", "$": "USD", "£": "GBP", "€": "EUR"}
    for sym, code in symbols.items():
        if sym in raw:
            currency = code
            break
    match = re.search(r"[\d,]+(?:\.\d+)?", raw)
    if not match:
        return None, currency
    try:
        return float(match.group(0).replace(",", "")), currency
    except ValueError:
        return None, currency


class SerpApiProvider(Provider):
    name = "serpapi"

    def __init__(self) -> None:
        self.api_key = os.getenv("SERPAPI_KEY", "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(self, req: SearchRequest) -> list[Listing]:
        params = {
            "engine": "google_shopping",
            "q": f"{req.query} {req.location}",
            "location": req.location,
            "api_key": self.api_key,
            "num": min(req.limit, 60),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: list[Listing] = []
        for item in data.get("shopping_results", []):
            price, currency = _parse_price(item.get("price"))
            link = item.get("product_link") or item.get("link")
            if not link:
                continue
            results.append(
                Listing(
                    title=item.get("title", "Untitled"),
                    price=price,
                    currency=currency,
                    seller=item.get("source"),
                    location=req.location,
                    source="serpapi",
                    product_url=link,
                    image_url=item.get("thumbnail"),
                ).with_timestamp()
            )
        return results
