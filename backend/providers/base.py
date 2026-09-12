from abc import ABC, abstractmethod

from models import Listing, SearchRequest


class Provider(ABC):
    name: str = "base"
    category: str = "data"

    @property
    def enabled(self) -> bool:
        return True

    @abstractmethod
    async def search(self, req: SearchRequest) -> list[Listing]:
        ...
