import xml.etree.ElementTree as ET

import httpx

_FEED = "https://trends.google.com/trending/rss"
_NS = {"ht": "https://trends.google.com/trending/rss"}

REGIONS = {
    "IN": "India",
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "SG": "Singapore",
    "AE": "United Arab Emirates",
    "DE": "Germany",
    "JP": "Japan",
    "BR": "Brazil",
}


def _text(node, tag: str) -> str:
    found = node.find(tag, _NS)
    return found.text.strip() if found is not None and found.text else ""


async def fetch_trending(geo: str = "IN", limit: int = 20) -> list[dict]:
    geo = (geo or "IN").upper()
    if geo not in REGIONS:
        geo = "IN"
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = await client.get(_FEED, params={"geo": geo})
        resp.raise_for_status()
        root = ET.fromstring(resp.text)

    items: list[dict] = []
    for item in root.iter("item"):
        title = _text(item, "title")
        if not title:
            continue
        news = item.find("ht:news_item", _NS)
        items.append(
            {
                "query": title,
                "traffic": _text(item, "ht:approx_traffic"),
                "image": _text(item, "ht:picture"),
                "source": _text(item, "ht:picture_source"),
                "article_title": _text(news, "ht:news_item_title") if news is not None else "",
                "article_url": _text(news, "ht:news_item_url") if news is not None else "",
            }
        )
        if len(items) >= limit:
            break
    return items
