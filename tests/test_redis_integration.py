from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest
from redis import RedisError
from redis.asyncio import Redis

from finops_token_saver.api.app import create_app
from finops_token_saver.domain.provider import ProviderResponse
from finops_token_saver.infrastructure.redis_cache import RedisCacheStore
from finops_token_saver.infrastructure.settings import AppSettings
from tests.fakes import FakeProviderClient

pytestmark = pytest.mark.integration

GATEWAY_TOKEN = "redis-integration-token"
PAYLOAD = {
    "model": "redis-integration-model",
    "messages": [{"role": "user", "content": "redis integration prompt"}],
    "temperature": 0,
}


@pytest.mark.anyio
async def test_real_redis_cache_miss_followed_by_cache_hit() -> None:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL is not configured; skipping real Redis integration smoke test")

    key_prefix = f"finops-token-saver:integration:{uuid4()}:"
    redis_client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    await _assert_redis_available(redis_client)
    await _cleanup_prefixed_keys(redis_client, key_prefix)

    provider_response = ProviderResponse(
        status_code=200,
        body={"id": "redis-integration-completion", "choices": []},
        provider="fake",
    )
    provider_client = FakeProviderClient(response=provider_response)
    app = create_app(
        settings=AppSettings.from_env({"GATEWAY_API_KEYS": GATEWAY_TOKEN}),
        provider_client=provider_client,
        cache_store=RedisCacheStore.from_url(redis_url, key_prefix=key_prefix),
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first_response = await _chat_completion(client)
            second_response = await _chat_completion(client)

        assert first_response.status_code == 200
        assert first_response.headers["x-cache-status"] == "MISS"
        assert second_response.status_code == 200
        assert second_response.headers["x-cache-status"] == "HIT"
        assert provider_client.requests == [PAYLOAD]
    finally:
        await _cleanup_prefixed_keys(redis_client, key_prefix)
        await redis_client.aclose()


async def _chat_completion(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {GATEWAY_TOKEN}"},
        json=PAYLOAD,
    )


async def _assert_redis_available(redis_client: Redis) -> None:
    try:
        await redis_client.ping()
    except RedisError as error:
        pytest.fail(
            f"Redis integration smoke could not connect to configured REDIS_URL: "
            f"{type(error).__name__}"
        )


async def _cleanup_prefixed_keys(redis_client: Redis, key_prefix: str) -> None:
    keys = [key async for key in redis_client.scan_iter(match=f"{key_prefix}*")]
    if keys:
        await redis_client.delete(*keys)
