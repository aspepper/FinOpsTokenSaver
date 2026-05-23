from __future__ import annotations

import asyncio
import os
import statistics
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from redis.asyncio import Redis

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from finops_token_saver.api.app import create_app  # noqa: E402
from finops_token_saver.application.provider import ProviderClient  # noqa: E402
from finops_token_saver.domain.provider import ProviderResponse  # noqa: E402
from finops_token_saver.infrastructure.redis_cache import RedisCacheStore  # noqa: E402
from finops_token_saver.infrastructure.settings import AppSettings  # noqa: E402

BENCHMARK_TOKEN = "benchmark-local-token"
DEFAULT_HIT_COUNT = 100
DEFAULT_WARMUP_HIT_COUNT = 5
PAYLOAD = {
    "model": "redis-benchmark-model",
    "messages": [{"role": "user", "content": "redis benchmark prompt"}],
    "temperature": 0,
}


class BenchmarkProviderClient(ProviderClient):
    def __init__(self) -> None:
        self.call_count = 0

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        self.call_count += 1
        return ProviderResponse(
            status_code=200,
            provider="benchmark",
            body={
                "id": "redis-benchmark-completion",
                "choices": [{"message": {"role": "assistant", "content": "benchmark-ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )


async def main() -> int:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("REDIS_URL is not configured; skipping Redis cache hit benchmark.")
        return 0

    hit_count = _positive_int_from_env("BENCHMARK_REQUESTS", DEFAULT_HIT_COUNT)
    warmup_hit_count = _positive_int_from_env("BENCHMARK_WARMUP_REQUESTS", DEFAULT_WARMUP_HIT_COUNT)
    environment_label = os.getenv("BENCHMARK_ENVIRONMENT", "unspecified")
    key_prefix = f"finops-token-saver:benchmark:{uuid4()}:"
    redis_client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    try:
        await redis_client.ping()
        await _cleanup_prefixed_keys(redis_client, key_prefix)

        provider_client = BenchmarkProviderClient()
        app = create_app(
            settings=AppSettings.from_env({"GATEWAY_API_KEYS": BENCHMARK_TOKEN}),
            provider_client=provider_client,
            cache_store=RedisCacheStore.from_url(redis_url, key_prefix=key_prefix),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first_response = await _chat_completion(client)
            _require_cache_status(first_response, "MISS", "initial warmup")
            for _ in range(warmup_hit_count):
                warmup_response = await _chat_completion(client)
                _require_cache_status(warmup_response, "HIT", "warmup hit")

            durations_ms = []
            for _ in range(hit_count):
                started_at = time.perf_counter()
                response = await _chat_completion(client)
                durations_ms.append((time.perf_counter() - started_at) * 1000)
                _require_cache_status(response, "HIT", "measured hit")

        _print_report(
            durations_ms=durations_ms,
            environment_label=environment_label,
            hit_count=hit_count,
            warmup_hit_count=warmup_hit_count,
            provider_call_count=provider_client.call_count,
        )
        return 0
    finally:
        await _cleanup_prefixed_keys(redis_client, key_prefix)
        await redis_client.aclose()


async def _chat_completion(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {BENCHMARK_TOKEN}"},
        json=PAYLOAD,
    )


def _require_cache_status(response: httpx.Response, expected_status: str, phase: str) -> None:
    cache_status = response.headers.get("x-cache-status")
    if response.status_code != 200 or cache_status != expected_status:
        raise RuntimeError(
            f"Unexpected response during {phase}: "
            f"status={response.status_code} x-cache-status={cache_status}"
        )


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer") from error
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer")
    return value


async def _cleanup_prefixed_keys(redis_client: Redis, key_prefix: str) -> None:
    keys = [key async for key in redis_client.scan_iter(match=f"{key_prefix}*")]
    if keys:
        await redis_client.delete(*keys)


def _print_report(
    durations_ms: list[float],
    environment_label: str,
    hit_count: int,
    warmup_hit_count: int,
    provider_call_count: int,
) -> None:
    sorted_durations = sorted(durations_ms)
    print("redis_cache_hit_benchmark=completed")
    print(f"environment={environment_label}")
    print(f"measured_hits={hit_count}")
    print(f"warmup_hits={warmup_hit_count}")
    print(f"provider_calls={provider_call_count}")
    print(f"mean_ms={statistics.fmean(durations_ms):.3f}")
    print(f"p50_ms={_percentile(sorted_durations, 50):.3f}")
    print(f"p95_ms={_percentile(sorted_durations, 95):.3f}")
    print(f"p99_ms={_percentile(sorted_durations, 99):.3f}")
    print("note=Use these numbers only for the environment identified above.")


def _percentile(sorted_values: list[float], percentile: int) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * percentile / 100
    lower_index = int(index)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = index - lower_index
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
