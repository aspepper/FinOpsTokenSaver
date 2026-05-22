import asyncio
from collections.abc import Awaitable, Callable
from typing import Optional

from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import ProviderError, ProviderResponse
from finops_token_saver.domain.retry_policy import RetryPolicy

Sleep = Callable[[float], Awaitable[None]]


class RetryingProviderClient(ProviderClient):
    def __init__(
        self,
        provider_client: ProviderClient,
        retry_policy: Optional[RetryPolicy] = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._provider_client = provider_client
        self._retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        attempt_number = 1
        while True:
            try:
                return await self._provider_client.create_chat_completion(payload)
            except ProviderError as error:
                if not self._retry_policy.should_retry(error, attempt_number):
                    raise

                await self._sleep(self._retry_policy.delay_for_attempt(attempt_number))
                attempt_number += 1
