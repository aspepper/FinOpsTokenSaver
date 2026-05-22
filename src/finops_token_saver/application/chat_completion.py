from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

from finops_token_saver.application.cache import CacheStore
from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.cache_policy import CachePolicy
from finops_token_saver.domain.cache_status import (
    CACHE_STATUS_BYPASS,
    CACHE_STATUS_HIT,
    CACHE_STATUS_MISS,
)
from finops_token_saver.domain.canonical_payload import CanonicalPayload
from finops_token_saver.domain.provider import ProviderResponse

DEFAULT_PROVIDER_NAME = "openai"


@dataclass(frozen=True)
class ChatCompletionResult:
    provider_response: ProviderResponse
    cache_status: str


class ForwardChatCompletion:
    def __init__(
        self,
        provider_client: ProviderClient,
        cache_store: Optional[CacheStore] = None,
        cache_policy: Optional[CachePolicy] = None,
        cache_ttl_seconds: int = 0,
        provider_name: str = DEFAULT_PROVIDER_NAME,
    ) -> None:
        self._provider_client = provider_client
        self._cache_store = cache_store
        self._cache_policy = cache_policy or CachePolicy()
        self._cache_ttl_seconds = cache_ttl_seconds
        self._provider_name = provider_name

    async def execute(
        self,
        payload: dict,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ChatCompletionResult:
        request_headers = headers or {}
        if self._cache_store is None or not self._cache_policy.allows_cache_lookup(
            payload,
            request_headers,
        ):
            provider_response = await self._provider_client.create_chat_completion(payload)
            return ChatCompletionResult(provider_response, CACHE_STATUS_BYPASS)

        cache_key = self._cache_key_for(payload)
        cached_body = await self._cache_store.get(cache_key)
        if cached_body is not None:
            return ChatCompletionResult(
                ProviderResponse(
                    status_code=200,
                    body=cached_body,
                    provider=self._provider_name,
                ),
                CACHE_STATUS_HIT,
            )

        provider_response = await self._provider_client.create_chat_completion(payload)
        if self._cache_policy.allows_cache_storage(payload, request_headers, provider_response):
            await self._cache_store.set(
                cache_key,
                provider_response.body,
                self._cache_ttl_seconds,
            )
        return ChatCompletionResult(provider_response, CACHE_STATUS_MISS)

    def _cache_key_for(self, payload: dict) -> str:
        canonical_payload = CanonicalPayload.from_chat_completion_payload(
            payload,
            provider=self._provider_name,
        )
        return canonical_payload.sha256()
