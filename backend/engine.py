import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from models import Listing, SearchRequest, SearchResponse
from providers.apify import ApifyProvider
from providers.base import Provider
from providers.marketplaces import MarketplacesProvider
from providers.mock import MockProvider
from providers.serpapi import SerpApiProvider

ALL_PROVIDERS: list[Provider] = [
    SerpApiProvider(),
    ApifyProvider(),
    MarketplacesProvider(),
    MockProvider(),
]

_CACHE: dict[str, tuple[float, SearchResponse]] = {}
_CACHE_TTL = 3600


def select_providers(req: SearchRequest) -> list[Provider]:
    active = [p for p in ALL_PROVIDERS if p.enabled]
    if req.sources:
        wanted = {s.lower() for s in req.sources}
        return [p for p in active if p.name in wanted]

    links = [p for p in active if p.category == "links"]
    data = [p for p in active if p.category == "data"]
    real_data = [p for p in data if p.name != "mock"]
    chosen_data = real_data if real_data else data
    return chosen_data + links


def _dedupe(listings: list[Listing]) -> list[Listing]:
    seen: set[str] = set()
    out: list[Listing] = []
    for item in listings:
        key = f"{item.title.strip().lower()}|{(item.seller or '').strip().lower()}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _apply_price_filter(listings: list[Listing], req: SearchRequest) -> list[Listing]:
    def ok(item: Listing) -> bool:
        if item.price is None:
            return True
        if req.min_price is not None and item.price < req.min_price:
            return False
        if req.max_price is not None and item.price > req.max_price:
            return False
        return True

    return [i for i in listings if ok(i)]


async def perform_search(req: SearchRequest, use_cache: bool = True) -> SearchResponse:
    cache_key = req.model_dump_json()
    if use_cache:
        hit = _CACHE.get(cache_key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return hit[1]

    selected = select_providers(req)
    errors: dict[str, str] = {}

    async def run(p: Provider) -> list[Listing]:
        try:
            return await p.search(req)
        except Exception as exc:  # noqa: BLE001
            errors[p.name] = str(exc)
            return []

    gathered = await asyncio.gather(*(run(p) for p in selected))
    merged: list[Listing] = [item for batch in gathered for item in batch]
    merged = _apply_price_filter(_dedupe(merged), req)
    merged.sort(key=lambda i: (i.price is None, i.price or 0))
    merged = merged[: req.limit]

    resp = SearchResponse(
        query=req.query,
        location=req.location,
        count=len(merged),
        results=merged,
        providers_used=[p.name for p in selected],
        errors=errors,
    )
    _CACHE[cache_key] = (time.time(), resp)
    return resp
