import pytest

from finops_token_saver.application.chat_completion import ForwardChatCompletion
from finops_token_saver.domain.provider import ProviderRateLimitError, ProviderResponse
from tests.fakes import FakeProviderClient


@pytest.mark.anyio
async def test_forward_chat_completion_uses_provider_client_contract() -> None:
    provider_response = ProviderResponse(
        status_code=200,
        body={"id": "completion-1", "choices": [{"message": {"content": "ok"}}]},
        provider="fake",
    )
    provider_client = FakeProviderClient(response=provider_response)
    use_case = ForwardChatCompletion(provider_client)
    payload = {"model": "test-model", "messages": [{"role": "user", "content": "ping"}]}

    response = await use_case.execute(payload)

    assert response.provider_response == provider_response
    assert response.cache_status == "BYPASS"
    assert provider_client.requests == [payload]


@pytest.mark.anyio
async def test_provider_errors_expose_safe_contract_fields() -> None:
    provider_error = ProviderRateLimitError(
        status_code=429,
        error_type="rate_limit",
        safe_message="Provider rate limit exceeded",
        code="provider_rate_limit",
    )
    provider_client = FakeProviderClient(error=provider_error)
    use_case = ForwardChatCompletion(provider_client)

    with pytest.raises(ProviderRateLimitError) as error:
        await use_case.execute({"model": "test-model"})

    assert error.value.status_code == 429
    assert error.value.error_type == "rate_limit"
    assert error.value.safe_message == "Provider rate limit exceeded"
    assert error.value.code == "provider_rate_limit"
