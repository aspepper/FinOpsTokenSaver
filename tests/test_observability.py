import logging

from fastapi.testclient import TestClient

from finops_token_saver.api.app import create_app
from finops_token_saver.domain.provider import ProviderRateLimitError, ProviderResponse
from finops_token_saver.infrastructure.settings import AppSettings
from tests.fakes import FakeProviderClient


def test_chat_success_includes_observability_headers() -> None:
    client = TestClient(
        create_app(
            _settings(),
            provider_client=FakeProviderClient(
                response=ProviderResponse(
                    status_code=200,
                    body={"id": "completion-1", "choices": []},
                    provider="fake",
                )
            ),
        )
    )

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-gateway-latency-ms"].isdigit()
    assert response.headers["x-cache-status"] == "BYPASS"
    assert response.headers["x-provider"] == "fake"
    assert response.headers["x-retry-count"] == "0"


def test_provider_error_includes_observability_headers() -> None:
    client = TestClient(
        create_app(
            _settings(),
            provider_client=FakeProviderClient(
                error=ProviderRateLimitError(
                    status_code=429,
                    error_type="rate_limit",
                    safe_message="Provider rate limit exceeded",
                    code="provider_rate_limit",
                )
            ),
        )
    )

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 429
    assert response.headers["x-request-id"]
    assert response.headers["x-gateway-latency-ms"].isdigit()
    assert response.headers["x-cache-status"] == "BYPASS"
    assert response.headers["x-provider"] == "unknown"
    assert response.headers["x-retry-count"] == "0"


def test_auth_error_includes_request_observability_headers() -> None:
    client = TestClient(create_app(_settings(), provider_client=FakeProviderClient()))

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer wrong-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 401
    assert response.headers["x-request-id"]
    assert response.headers["x-gateway-latency-ms"].isdigit()


def test_structured_request_log_excludes_prompt_and_secrets(caplog) -> None:
    token = "valid-token"
    sensitive_prompt = "complete sensitive prompt should not be logged"
    client = TestClient(create_app(_settings(), provider_client=FakeProviderClient()))

    with caplog.at_level(logging.INFO, logger="finops_token_saver.api"):
        response = client.post(
            "/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Request-Id": "request-from-client",
            },
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": sensitive_prompt}],
            },
        )

    record = next(item for item in caplog.records if item.message == "gateway_request")
    assert record.request_id == response.headers["x-request-id"] == "request-from-client"
    assert record.method == "POST"
    assert record.path == "/v1/chat/completions"
    assert record.status_code == 200
    assert record.cache_status == "BYPASS"
    assert record.retry_count == "0"
    assert isinstance(record.latency_ms, int)
    assert sensitive_prompt not in caplog.text
    assert token not in caplog.text


def _settings() -> AppSettings:
    return AppSettings.from_env({"GATEWAY_API_KEYS": "valid-token"})
