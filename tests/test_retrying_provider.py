from typing import Optional, Union

import pytest

from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.application.retrying_provider import RetryingProviderClient
from finops_token_saver.domain.provider import ProviderError, ProviderResponse
from finops_token_saver.domain.retry_policy import RetryPolicy


class SequenceProviderClient(ProviderClient):
    def __init__(self, outcomes: list[Union[ProviderError, ProviderResponse]]) -> None:
        self.requests: list[dict] = []
        self._outcomes = outcomes

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        self.requests.append(payload)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome


class FakeSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, delay_seconds: float) -> None:
        self.delays.append(delay_seconds)


@pytest.mark.anyio
async def test_retrying_provider_succeeds_after_retry_without_real_sleep() -> None:
    response = ProviderResponse(status_code=200, body={"id": "ok"}, provider="fake")
    provider_client = SequenceProviderClient([_provider_error(429), response])
    sleeper = FakeSleeper()
    retrying_provider = RetryingProviderClient(
        provider_client=provider_client,
        retry_policy=RetryPolicy(max_attempts=3, jitter_seconds=0),
        sleep=sleeper.sleep,
    )
    payload = {"model": "test-model"}

    result = await retrying_provider.create_chat_completion(payload)

    assert result == ProviderResponse(
        status_code=200,
        body={"id": "ok"},
        provider="fake",
        retry_count=1,
    )
    assert provider_client.requests == [payload, payload]
    assert sleeper.delays == [2.0]


@pytest.mark.anyio
async def test_retrying_provider_raises_final_error_after_max_attempts() -> None:
    final_error = _provider_error(503, code="final_error")
    provider_client = SequenceProviderClient(
        [_provider_error(503), _provider_error(503), final_error]
    )
    sleeper = FakeSleeper()
    retrying_provider = RetryingProviderClient(
        provider_client=provider_client,
        retry_policy=RetryPolicy(max_attempts=3, jitter_seconds=0),
        sleep=sleeper.sleep,
    )

    with pytest.raises(ProviderError) as error:
        await retrying_provider.create_chat_completion({"model": "test-model"})

    assert error.value is final_error
    assert error.value.retry_count == 2
    assert len(provider_client.requests) == 3
    assert sleeper.delays == [2.0, 4.0]


@pytest.mark.anyio
async def test_retrying_provider_does_not_retry_client_4xx_errors() -> None:
    provider_client = SequenceProviderClient([_provider_error(400)])
    sleeper = FakeSleeper()
    retrying_provider = RetryingProviderClient(
        provider_client=provider_client,
        retry_policy=RetryPolicy(max_attempts=3, jitter_seconds=0),
        sleep=sleeper.sleep,
    )

    with pytest.raises(ProviderError):
        await retrying_provider.create_chat_completion({"model": "test-model"})

    assert len(provider_client.requests) == 1
    assert sleeper.delays == []


def _provider_error(status_code: int, code: Optional[str] = None) -> ProviderError:
    return ProviderError(
        status_code=status_code,
        error_type="provider_error",
        safe_message="Provider failed",
        code=code,
    )
