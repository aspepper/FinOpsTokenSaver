from __future__ import annotations

import httpx
import pytest

from finops_token_saver.domain.provider import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from finops_token_saver.infrastructure.provider import (
    OPENAI_CHAT_COMPLETIONS_URL,
    OPENAI_PROVIDER_NAME,
    OpenAIProviderClient,
)


class FakeHttpResponse:
    def __init__(self, status_code: int, body: dict | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class InvalidJsonResponse:
    status_code = 200

    def json(self) -> dict:
        raise ValueError("invalid json")


class FakeHttpClient:
    def __init__(
        self,
        response: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self.requests: list[dict] = []
        self._response = response or FakeHttpResponse(200, {"id": "completion-1"})
        self._error = error

    async def post(self, url: str, *, json: dict, headers: dict[str, str]) -> object:
        self.requests.append({"url": url, "json": json, "headers": headers})
        if self._error is not None:
            raise self._error
        return self._response


@pytest.mark.anyio
async def test_openai_provider_posts_payload_with_configured_key() -> None:
    http_client = FakeHttpClient(
        response=FakeHttpResponse(
            200,
            {"id": "completion-1", "choices": [{"message": {"content": "ok"}}]},
        )
    )
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=http_client,
    )
    payload = {"model": "gpt-test", "messages": [{"role": "user", "content": "ping"}]}

    response = await provider.create_chat_completion(payload)

    assert response.status_code == 200
    assert response.provider == OPENAI_PROVIDER_NAME
    assert response.body == {"id": "completion-1", "choices": [{"message": {"content": "ok"}}]}
    assert http_client.requests == [
        {
            "url": OPENAI_CHAT_COMPLETIONS_URL,
            "json": payload,
            "headers": {
                "Authorization": "Bearer provider-secret",
                "Content-Type": "application/json",
            },
        }
    ]


@pytest.mark.anyio
async def test_openai_provider_maps_authentication_error_without_exposing_secret() -> None:
    http_client = FakeHttpClient(
        response=FakeHttpResponse(401, {"error": {"message": "bad key provider-secret"}})
    )
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=http_client,
    )

    with pytest.raises(ProviderAuthenticationError) as error:
        await provider.create_chat_completion({"model": "gpt-test"})

    assert error.value.status_code == 401
    assert error.value.safe_message == "OpenAI authentication failed"
    assert "provider-secret" not in error.value.safe_message


@pytest.mark.anyio
async def test_openai_provider_maps_rate_limit_error() -> None:
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=FakeHttpClient(response=FakeHttpResponse(429)),
    )

    with pytest.raises(ProviderRateLimitError) as error:
        await provider.create_chat_completion({"model": "gpt-test"})

    assert error.value.status_code == 429
    assert error.value.error_type == "rate_limit"
    assert error.value.code == "provider_rate_limit"


@pytest.mark.anyio
async def test_openai_provider_maps_timeout_exception() -> None:
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=FakeHttpClient(error=httpx.TimeoutException("timed out")),
    )

    with pytest.raises(ProviderTimeoutError) as error:
        await provider.create_chat_completion({"model": "gpt-test"})

    assert error.value.status_code == 504
    assert error.value.safe_message == "OpenAI request timed out"


@pytest.mark.anyio
async def test_openai_provider_maps_network_error() -> None:
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=FakeHttpClient(error=httpx.ConnectError("connection failed")),
    )

    with pytest.raises(ProviderUnavailableError) as error:
        await provider.create_chat_completion({"model": "gpt-test"})

    assert error.value.status_code == 503
    assert error.value.safe_message == "OpenAI provider is unavailable"


@pytest.mark.anyio
async def test_openai_provider_maps_invalid_json_response() -> None:
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=FakeHttpClient(response=InvalidJsonResponse()),
    )

    with pytest.raises(ProviderUnavailableError) as error:
        await provider.create_chat_completion({"model": "gpt-test"})

    assert error.value.status_code == 502
    assert error.value.code == "provider_invalid_response"


@pytest.mark.anyio
async def test_openai_provider_maps_client_error_to_generic_provider_error() -> None:
    provider = OpenAIProviderClient(
        api_key="provider-secret",
        timeout_seconds=2.5,
        http_client=FakeHttpClient(response=FakeHttpResponse(400)),
    )

    with pytest.raises(ProviderError) as error:
        await provider.create_chat_completion({"model": "gpt-test"})

    assert error.value.status_code == 400
    assert error.value.safe_message == "OpenAI request failed"
