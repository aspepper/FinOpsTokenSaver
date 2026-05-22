from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import ProviderResponse


class ForwardChatCompletion:
    def __init__(self, provider_client: ProviderClient) -> None:
        self._provider_client = provider_client

    async def execute(self, payload: dict) -> ProviderResponse:
        return await self._provider_client.create_chat_completion(payload)
