import asyncio
import os

import store
from engine import perform_search
from models import SearchRequest

_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "24"))
_SCAN_SECONDS = 3600


async def check_watch(watch: dict) -> dict:
    req = SearchRequest(query=watch["product"], location=watch["location"], limit=40)
    resp = await perform_search(req, use_cache=False)

    priced = [r for r in resp.results if r.price is not None]
    priced.sort(key=lambda r: r.price)
    min_price = priced[0].price if priced else None
    currency = priced[0].currency if priced else None
    top = [
        {
            "title": r.title,
            "price": r.price,
            "currency": r.currency,
            "seller": r.seller,
            "source": r.source,
            "product_url": r.product_url,
        }
        for r in resp.results[:5]
    ]

    return store.add_snapshot(
        watch_id=watch["id"],
        min_price=min_price,
        currency=currency,
        priced_count=len(priced),
        total_count=resp.count,
        available=resp.count > 0,
        providers=resp.providers_used,
        top=top,
    )


async def check_all() -> int:
    count = 0
    for watch in store.list_watches():
        try:
            await check_watch(watch)
            count += 1
        except Exception:  # noqa: BLE001
            continue
    return count


async def scheduler_loop() -> None:
    import time

    while True:
        due_cutoff = _INTERVAL_HOURS * 3600
        for watch in store.list_watches():
            snaps = store.latest_snapshots(watch["id"], limit=1)
            last = snaps[0]["checked_at"] if snaps else None
            if last is None or (time.time() - last) >= due_cutoff:
                try:
                    await check_watch(watch)
                except Exception:  # noqa: BLE001
                    pass
        await asyncio.sleep(_SCAN_SECONDS)
