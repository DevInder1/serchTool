import hashlib
import random

from models import Listing, SearchRequest
from providers.base import Provider

_SELLERS = [
    "Craftsmen Bazaar",
    "UrbanMart",
    "LocalHaus",
    "The Corner Store",
    "PrimeGoods",
    "Everyday Emporium",
]

_CURRENCY_BY_HINT = {
    "india": ("INR", 200, 8000),
    "united states": ("USD", 5, 200),
    "usa": ("USD", 5, 200),
    "uk": ("GBP", 5, 180),
    "united kingdom": ("GBP", 5, 180),
}


def _currency_for(location: str) -> tuple[str, float, float]:
    loc = location.lower()
    for hint, spec in _CURRENCY_BY_HINT.items():
        if hint in loc:
            return spec
    return ("USD", 5, 200)


class MockProvider(Provider):
    name = "mock"

    async def search(self, req: SearchRequest) -> list[Listing]:
        seed = int(hashlib.sha256(f"{req.query}|{req.location}".encode()).hexdigest(), 16) % (10**8)
        rng = random.Random(seed)
        currency, lo, hi = _currency_for(req.location)

        results: list[Listing] = []
        for i in range(min(req.limit, 24)):
            price = round(rng.uniform(lo, hi), 2)
            seller = rng.choice(_SELLERS)
            slug = req.query.strip().lower().replace(" ", "-") or "product"
            results.append(
                Listing(
                    title=f"{req.query.title()} — Model {chr(65 + i % 6)}{rng.randint(10, 99)}",
                    price=price,
                    currency=currency,
                    seller=seller,
                    location=req.location,
                    source="mock",
                    product_url=f"https://example.com/{slug}/{i}",
                    image_url=f"https://picsum.photos/seed/{seed + i}/300/200",
                ).with_timestamp()
            )
        return results
