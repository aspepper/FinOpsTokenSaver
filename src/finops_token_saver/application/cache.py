from typing import Optional, Protocol


class CacheStore(Protocol):
    async def get(self, key: str) -> Optional[dict]:
        """Return a cached response body when present."""

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        """Store a response body for a limited time."""
