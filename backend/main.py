import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import store
import trending
from engine import ALL_PROVIDERS, perform_search
from models import SearchRequest, SearchResponse
from watcher import check_watch, scheduler_loop

app = FastAPI(title="Product Finder")

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class WatchCreate(BaseModel):
    product: str
    location: str = "Bangalore, India"


@app.on_event("startup")
async def _startup() -> None:
    store.init()
    asyncio.create_task(scheduler_loop())


@app.get("/api/providers")
def providers() -> dict:
    return {"providers": [{"name": p.name, "enabled": p.enabled} for p in ALL_PROVIDERS]}


@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    return await perform_search(req)


@app.get("/api/trending")
async def get_trending(geo: str = "IN") -> dict:
    try:
        items = await trending.fetch_trending(geo)
        return {"geo": geo.upper(), "regions": trending.REGIONS, "items": items}
    except Exception as exc:  # noqa: BLE001
        return {"geo": geo.upper(), "regions": trending.REGIONS, "items": [], "error": str(exc)}


def _watch_view(watch: dict) -> dict:
    snaps = store.latest_snapshots(watch["id"], limit=2)
    latest = snaps[0] if snaps else None
    previous = snaps[1] if len(snaps) > 1 else None
    change = None
    if latest and previous and latest["min_price"] is not None and previous["min_price"] is not None:
        change = round(latest["min_price"] - previous["min_price"], 2)
    return {**watch, "latest": latest, "previous_min_price": previous["min_price"] if previous else None, "change": change}


@app.get("/api/watches")
def get_watches() -> dict:
    return {"watches": [_watch_view(w) for w in store.list_watches()]}


@app.post("/api/watches")
async def create_watch(body: WatchCreate) -> dict:
    if not body.product.strip():
        raise HTTPException(status_code=400, detail="product is required")
    watch = store.add_watch(body.product, body.location)
    await check_watch(watch)
    return _watch_view(watch)


@app.post("/api/watches/{watch_id}/check")
async def run_check(watch_id: int) -> dict:
    watch = store.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="watch not found")
    await check_watch(watch)
    return _watch_view(watch)


@app.get("/api/watches/{watch_id}/history")
def watch_history(watch_id: int) -> dict:
    watch = store.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="watch not found")
    return {"watch": watch, "history": store.history(watch_id)}


@app.delete("/api/watches/{watch_id}")
def remove_watch(watch_id: int) -> dict:
    store.delete_watch(watch_id)
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=_STATIC_DIR), name="static")
