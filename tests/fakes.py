import time
from typing import Optional

from finops_token_saver.application.cache import CacheStore
from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import ProviderError, ProviderResponse


class InMemoryCacheStore(CacheStore):
    def __init__(self) -> None:
        self._items: dict[str, tuple[dict, float]] = {}
        self.ttl_seconds_by_key: dict[str, int] = {}

    async def get(self, key: str) -> Optional[dict]:
        item = self._items.get(key)
        if item is None:
            return None

        value, expires_at = item
        if expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None

        return value

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self.ttl_seconds_by_key[key] = ttl_seconds
        self._items[key] = (value, time.monotonic() + ttl_seconds)


class FakeProviderClient(ProviderClient):
    def __init__(
        self,
        response: Optional[ProviderResponse] = None,
        error: Optional[ProviderError] = None,
    ) -> None:
        self.requests: list[dict] = []
        self._response = response or ProviderResponse(
            status_code=200,
            body={"id": "fake-completion", "choices": []},
            provider="fake",
        )
        self._error = error

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        self.requests.append(payload)
        if self._error is not None:
            raise self._error
        return self._response
