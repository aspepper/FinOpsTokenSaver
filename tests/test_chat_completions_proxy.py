from fastapi.testclient import TestClient

from finops_token_saver.api.app import create_app
from finops_token_saver.application.retrying_provider import RetryingProviderClient
from finops_token_saver.domain.provider import (
    ProviderError,
    ProviderRateLimitError,
    ProviderResponse,
)
from finops_token_saver.domain.retry_policy import RetryPolicy
from finops_token_saver.infrastructure.settings import AppSettings
from tests.fakes import FakeProviderClient, InMemoryCacheStore


def test_chat_completions_forwards_payload_and_preserves_provider_response() -> None:
    provider_response = ProviderResponse(
        status_code=200,
        body={"id": "completion-1", "choices": [{"message": {"content": "pong"}}]},
        provider="fake",
    )
    provider_client = FakeProviderClient(response=provider_response)
    client = TestClient(create_app(_settings(), provider_client=provider_client))
    payload = {"model": "test-model", "messages": [{"role": "user", "content": "ping"}]}

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == provider_response.body
    assert response.headers["x-cache-status"] == "BYPASS"
    assert response.headers["x-retry-count"] == "0"
    assert provider_client.requests == [payload]


def test_chat_completions_maps_provider_error_to_openai_like_error_contract() -> None:
    provider_error = ProviderRateLimitError(
        status_code=429,
        error_type="rate_limit",
        safe_message="Provider rate limit exceeded",
        code="provider_rate_limit",
    )
    provider_client = FakeProviderClient(error=provider_error)
    client = TestClient(create_app(_settings(), provider_client=provider_client))

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 429
    assert response.headers["x-cache-status"] == "BYPASS"
    assert response.json() == {
        "error": {
            "message": "Provider rate limit exceeded",
            "type": "rate_limit",
            "code": "provider_rate_limit",
        }
    }


def test_chat_completions_cache_miss_followed_by_cache_hit() -> None:
    provider_response = ProviderResponse(
        status_code=200,
        body={"id": "completion-1", "choices": [{"message": {"content": "pong"}}]},
        provider="fake",
    )
    provider_client = FakeProviderClient(response=provider_response)
    cache_store = InMemoryCacheStore()
    client = TestClient(
        create_app(
            _settings(),
            provider_client=provider_client,
            cache_store=cache_store,
        )
    )
    payload = {"model": "test-model", "messages": [{"role": "user", "content": "ping"}]}

    first_response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json=payload,
    )
    second_response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json=payload,
    )

    assert first_response.status_code == 200
    assert first_response.headers["x-cache-status"] == "MISS"
    assert first_response.headers["x-retry-count"] == "0"
    assert second_response.status_code == 200
    assert second_response.headers["x-cache-status"] == "HIT"
    assert second_response.headers["x-retry-count"] == "0"
    assert second_response.json() == provider_response.body
    assert provider_client.requests == [payload]
    assert list(cache_store.ttl_seconds_by_key.values()) == [43_200]


def test_chat_completions_returns_real_retry_count_after_provider_retry() -> None:
    provider_response = ProviderResponse(
        status_code=200,
        body={"id": "completion-1", "choices": []},
        provider="fake",
    )
    provider_client = FakeProviderClient(
        error_then_response=_provider_error(429),
        response=provider_response,
    )
    retrying_provider = RetryingProviderClient(
        provider_client=provider_client,
        retry_policy=RetryPolicy(max_attempts=2, jitter_seconds=0),
        sleep=_fake_sleep,
    )
    client = TestClient(create_app(_settings(), provider_client=retrying_provider))

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 200
    assert response.headers["x-retry-count"] == "1"
    assert len(provider_client.requests) == 2


def test_chat_completions_returns_real_retry_count_on_final_provider_error() -> None:
    retrying_provider = RetryingProviderClient(
        provider_client=FakeProviderClient(error=_provider_error(503)),
        retry_policy=RetryPolicy(max_attempts=2, jitter_seconds=0),
        sleep=_fake_sleep,
    )
    client = TestClient(create_app(_settings(), provider_client=retrying_provider))

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 503
    assert response.headers["x-retry-count"] == "1"


def _settings() -> AppSettings:
    return AppSettings.from_env({"GATEWAY_API_KEYS": "valid-token"})


async def _fake_sleep(delay_seconds: float) -> None:
    return None


def _provider_error(status_code: int) -> ProviderError:
    return ProviderError(
        status_code=status_code,
        error_type="provider_error",
        safe_message="Provider failed",
        code="provider_error",
    )
