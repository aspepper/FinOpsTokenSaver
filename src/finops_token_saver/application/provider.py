from typing import Protocol

from finops_token_saver.domain.provider import ProviderResponse


class ProviderClient(Protocol):
    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        """Send a chat completion payload to an external LLM provider."""
