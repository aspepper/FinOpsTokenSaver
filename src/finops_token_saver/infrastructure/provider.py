from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import ProviderResponse, ProviderUnavailableError


class UnconfiguredProviderClient(ProviderClient):
    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        raise ProviderUnavailableError(
            status_code=503,
            error_type="provider_unavailable",
            safe_message="LLM provider is not configured",
            code="provider_not_configured",
        )
