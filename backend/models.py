from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel


class Listing(BaseModel):
    title: str
    price: Optional[float] = None
    currency: Optional[str] = None
    seller: Optional[str] = None
    location: Optional[str] = None
    source: str
    product_url: str
    image_url: Optional[str] = None
    fetched_at: str = ""

    def with_timestamp(self) -> "Listing":
        self.fetched_at = datetime.now(timezone.utc).isoformat()
        return self


class SearchRequest(BaseModel):
    query: str
    location: str = "Bangalore, India"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sources: Optional[list[str]] = None
    limit: int = 40


class SearchResponse(BaseModel):
    query: str
    location: str
    count: int
    results: list[Listing]
    providers_used: list[str]
    errors: dict[str, str] = {}
