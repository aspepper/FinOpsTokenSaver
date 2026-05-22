from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import httpx

from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_PROVIDER_NAME = "openai"


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> dict:
        """Return the decoded JSON response body."""


class HttpClient(Protocol):
    async def post(
        self,
        url: str,
        *,
        json: dict,
        headers: Mapping[str, str],
    ) -> HttpResponse:
        """Post a JSON payload to an HTTP endpoint."""


class UnconfiguredProviderClient(ProviderClient):
    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        raise ProviderUnavailableError(
            status_code=503,
            error_type="provider_unavailable",
            safe_message="LLM provider is not configured",
            code="provider_not_configured",
        )


class OpenAIProviderClient(ProviderClient):
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        http_client: HttpClient | None = None,
        endpoint_url: str = OPENAI_CHAT_COMPLETIONS_URL,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client
        self._endpoint_url = endpoint_url

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        try:
            response = await self._post(payload)
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError(
                status_code=504,
                error_type="provider_timeout",
                safe_message="OpenAI request timed out",
                code="provider_timeout",
            ) from error
        except httpx.RequestError as error:
            raise ProviderUnavailableError(
                status_code=503,
                error_type="provider_unavailable",
                safe_message="OpenAI provider is unavailable",
                code="provider_unavailable",
            ) from error

        if 200 <= response.status_code < 300:
            return ProviderResponse(
                status_code=response.status_code,
                body=_response_body(response),
                provider=OPENAI_PROVIDER_NAME,
            )

        raise _provider_error_from_response(response.status_code)

    async def _post(self, payload: dict) -> HttpResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._http_client is not None:
            return await self._http_client.post(
                self._endpoint_url,
                json=payload,
                headers=headers,
            )

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await client.post(
                self._endpoint_url,
                json=payload,
                headers=headers,
            )


def _response_body(response: HttpResponse) -> dict:
    try:
        return response.json()
    except ValueError as error:
        raise ProviderUnavailableError(
            status_code=502,
            error_type="provider_invalid_response",
            safe_message="OpenAI returned an invalid JSON response",
            code="provider_invalid_response",
        ) from error


def _provider_error_from_response(status_code: int) -> ProviderError:
    if status_code in {401, 403}:
        return ProviderAuthenticationError(
            status_code=status_code,
            error_type="provider_authentication",
            safe_message="OpenAI authentication failed",
            code="provider_authentication",
        )
    if status_code == 408:
        return ProviderTimeoutError(
            status_code=status_code,
            error_type="provider_timeout",
            safe_message="OpenAI request timed out",
            code="provider_timeout",
        )
    if status_code == 429:
        return ProviderRateLimitError(
            status_code=status_code,
            error_type="rate_limit",
            safe_message="OpenAI rate limit exceeded",
            code="provider_rate_limit",
        )
    if status_code >= 500:
        return ProviderUnavailableError(
            status_code=status_code,
            error_type="provider_unavailable",
            safe_message="OpenAI provider is unavailable",
            code="provider_unavailable",
        )
    return ProviderError(
        status_code=status_code,
        error_type="provider_error",
        safe_message="OpenAI request failed",
        code="provider_error",
    )
