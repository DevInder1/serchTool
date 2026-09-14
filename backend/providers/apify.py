import json
import os

import httpx

import apify_common
from models import Listing, SearchRequest
from providers.base import Provider

_DEFAULT_INPUT = '{"search": "{query}", "location": "{location}", "maxItems": {limit}}'
_SITES = ["olx", "facebook", "instagram", "quikr", "indiamart"]


class ApifyProvider(Provider):
    name = "apify"
    category = "data"

    def __init__(self) -> None:
        self.input_template = os.getenv("APIFY_INPUT_TEMPLATE", _DEFAULT_INPUT)
        self.actors: dict[str, str] = {}
        for site in _SITES:
            actor = os.getenv(f"APIFY_{site.upper()}_ACTOR", "").strip()
            if actor:
                self.actors[site] = actor

    @property
    def enabled(self) -> bool:
        return bool(apify_common.token() and self.actors)

    def _render_input(self, req: SearchRequest) -> dict:
        query = json.dumps(req.query)[1:-1]
        location = json.dumps(req.location)[1:-1]
        rendered = (
            self.input_template.replace("{query}", query)
            .replace("{location}", location)
            .replace("{limit}", str(int(req.limit)))
        )
        return json.loads(rendered)

    async def search(self, req: SearchRequest) -> list[Listing]:
        results: list[Listing] = []
        async with httpx.AsyncClient(timeout=apify_common.timeout()) as client:
            for site, actor in self.actors.items():
                try:
                    items = await apify_common.run_actor(client, actor, self._render_input(req), req.limit)
                except Exception:  # noqa: BLE001
                    continue
                for item in items[: req.limit]:
                    mapped = apify_common.map_item(item)
                    if mapped:
                        results.append(
                            Listing(
                                title=mapped["title"],
                                price=mapped["price"],
                                currency=mapped["currency"],
                                seller=mapped["seller"],
                                location=req.location,
                                source=f"{site} (apify)",
                                product_url=mapped["url"],
                                image_url=mapped["image"],
                            ).with_timestamp()
                        )
        return results
