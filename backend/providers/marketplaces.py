import urllib.parse

from models import Listing, SearchRequest
from providers.base import Provider


def _slug(text: str) -> str:
    return urllib.parse.quote(text.strip().lower().replace(" ", "-"))


def _qp(text: str) -> str:
    return urllib.parse.quote_plus(text.strip())


class MarketplacesProvider(Provider):
    name = "marketplaces"
    category = "links"

    async def search(self, req: SearchRequest) -> list[Listing]:
        product = req.query.strip()
        location = req.location.strip()
        with_loc = f"{product} {location}".strip()

        sites = [
            (
                "olx",
                "OLX India",
                f"https://www.olx.in/items/q-{_slug(product)}",
            ),
            (
                "quikr",
                "Quikr",
                f"https://www.quikr.com/search?q={_qp(with_loc)}",
            ),
            (
                "indiamart",
                "IndiaMART",
                f"https://dir.indiamart.com/search.mp?ss={_qp(product)}",
            ),
            (
                "facebook",
                "Facebook Marketplace",
                f"https://www.facebook.com/marketplace/search/?query={_qp(with_loc)}",
            ),
            (
                "instagram",
                "Instagram",
                f"https://www.instagram.com/explore/search/keyword/?q={_qp(product)}",
            ),
        ]

        return [
            Listing(
                title=f"Search {label} for “{product}” in {location}",
                price=None,
                currency=None,
                seller=label,
                location=location,
                source=src,
                product_url=url,
                image_url=None,
            ).with_timestamp()
            for src, label, url in sites
        ]
