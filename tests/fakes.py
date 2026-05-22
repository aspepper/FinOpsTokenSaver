from typing import Optional

from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import ProviderError, ProviderResponse


class FakeProviderClient(ProviderClient):
    def __init__(
        self,
        response: Optional[ProviderResponse] = None,
        error: Optional[ProviderError] = None,
    ) -> None:
        self.requests: list[dict] = []
        self._response = response or ProviderResponse(
            status_code=200,
            body={"id": "fake-completion", "choices": []},
            provider="fake",
        )
        self._error = error

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        self.requests.append(payload)
        if self._error is not None:
            raise self._error
        return self._response
