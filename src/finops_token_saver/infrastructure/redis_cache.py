import json
import logging
from typing import Optional, Protocol

from redis import RedisError
from redis.asyncio import Redis

from finops_token_saver.application.cache import CacheStore

DEFAULT_MAX_CACHE_ITEM_BYTES = 256 * 1024


class RedisClient(Protocol):
    async def get(self, name: str) -> Optional[bytes]:
        """Return the raw cached value for a key."""

    async def setex(self, name: str, time: int, value: str) -> object:
        """Store a value with an expiration time."""


class RedisCacheStore(CacheStore):
    def __init__(
        self,
        redis_client: RedisClient,
        max_item_bytes: int = DEFAULT_MAX_CACHE_ITEM_BYTES,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if max_item_bytes <= 0:
            raise ValueError("max_item_bytes must be positive")

        self._redis_client = redis_client
        self._max_item_bytes = max_item_bytes
        self._logger = logger or logging.getLogger(__name__)

    @classmethod
    def from_url(
        cls,
        redis_url: str,
        max_item_bytes: int = DEFAULT_MAX_CACHE_ITEM_BYTES,
    ) -> "RedisCacheStore":
        return cls(
            redis_client=Redis.from_url(redis_url, encoding="utf-8", decode_responses=False),
            max_item_bytes=max_item_bytes,
        )

    async def get(self, key: str) -> Optional[dict]:
        try:
            raw_value = await self._redis_client.get(key)
        except RedisError:
            self._log_cache_event("MISS")
            return None

        if raw_value is None:
            return None

        try:
            return json.loads(_decode_redis_value(raw_value))
        except (TypeError, ValueError, UnicodeDecodeError):
            self._log_cache_event("MISS")
            return None

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        serialized_value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if len(serialized_value.encode("utf-8")) > self._max_item_bytes:
            self._log_cache_event("SKIP")
            return

        try:
            await self._redis_client.setex(key, ttl_seconds, serialized_value)
        except RedisError:
            self._log_cache_event("SKIP")

    def _log_cache_event(self, status: str) -> None:
        self._logger.info(
            "redis_cache_event",
            extra={"cache_status": status, "request_id": None},
        )


def _decode_redis_value(raw_value: object) -> str:
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8")
    if isinstance(raw_value, str):
        return raw_value
    raise TypeError("Unsupported Redis value type")
