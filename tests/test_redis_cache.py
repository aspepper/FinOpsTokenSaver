import json
from typing import Optional

import pytest
from redis import RedisError

from finops_token_saver.infrastructure.redis_cache import RedisCacheStore


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttl_by_key: dict[str, int] = {}
        self.fail_get = False
        self.fail_set = False

    async def get(self, name: str) -> Optional[bytes]:
        if self.fail_get:
            raise RedisError("redis unavailable")
        return self.values.get(name)

    async def setex(self, name: str, time: int, value: str) -> None:
        if self.fail_set:
            raise RedisError("redis unavailable")
        self.ttl_by_key[name] = time
        self.values[name] = value.encode("utf-8")


@pytest.mark.anyio
async def test_redis_cache_preserves_response_body_round_trip() -> None:
    redis_client = FakeRedisClient()
    cache_store = RedisCacheStore(redis_client)
    response_body = {
        "id": "completion-1",
        "choices": [{"message": {"role": "assistant", "content": "pong"}}],
    }

    await cache_store.set("cache-key", response_body, ttl_seconds=60)
    cached_body = await cache_store.get("cache-key")

    assert cached_body == response_body
    assert redis_client.ttl_by_key == {"cache-key": 60}


@pytest.mark.anyio
async def test_redis_get_failure_is_treated_as_cache_miss() -> None:
    redis_client = FakeRedisClient()
    redis_client.fail_get = True
    cache_store = RedisCacheStore(redis_client)

    cached_body = await cache_store.get("cache-key")

    assert cached_body is None


@pytest.mark.anyio
async def test_invalid_cached_json_is_treated_as_cache_miss() -> None:
    redis_client = FakeRedisClient()
    redis_client.values["cache-key"] = b"not-json"
    cache_store = RedisCacheStore(redis_client)

    cached_body = await cache_store.get("cache-key")

    assert cached_body is None


@pytest.mark.anyio
async def test_redis_set_failure_does_not_raise() -> None:
    redis_client = FakeRedisClient()
    redis_client.fail_set = True
    cache_store = RedisCacheStore(redis_client)

    await cache_store.set("cache-key", {"id": "completion-1"}, ttl_seconds=60)

    assert redis_client.values == {}


@pytest.mark.anyio
async def test_redis_cache_does_not_store_items_above_max_size() -> None:
    redis_client = FakeRedisClient()
    cache_store = RedisCacheStore(redis_client, max_item_bytes=20)

    await cache_store.set("cache-key", {"content": "value larger than limit"}, ttl_seconds=60)

    assert redis_client.values == {}


@pytest.mark.anyio
async def test_redis_cache_rejects_non_positive_ttl() -> None:
    cache_store = RedisCacheStore(FakeRedisClient())

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        await cache_store.set("cache-key", {"id": "completion-1"}, ttl_seconds=0)


@pytest.mark.anyio
async def test_redis_cache_uses_compact_json_serialization() -> None:
    redis_client = FakeRedisClient()
    cache_store = RedisCacheStore(redis_client)
    response_body = {"choices": [{"message": {"content": "ola"}}]}

    await cache_store.set("cache-key", response_body, ttl_seconds=60)

    assert json.loads(redis_client.values["cache-key"].decode("utf-8")) == response_body
