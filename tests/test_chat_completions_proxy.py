from fastapi.testclient import TestClient

from finops_token_saver.api.app import create_app
from finops_token_saver.domain.provider import ProviderRateLimitError, ProviderResponse
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
    assert second_response.status_code == 200
    assert second_response.headers["x-cache-status"] == "HIT"
    assert second_response.json() == provider_response.body
    assert provider_client.requests == [payload]
    assert list(cache_store.ttl_seconds_by_key.values()) == [43_200]


def _settings() -> AppSettings:
    return AppSettings.from_env({"GATEWAY_API_KEYS": "valid-token"})
