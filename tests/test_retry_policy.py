import random

import pytest

from finops_token_saver.domain.provider import ProviderError
from finops_token_saver.domain.retry_policy import RetryPolicy


def test_retry_policy_retries_transient_provider_errors_before_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(_provider_error(408), attempt_number=1) is True
    assert policy.should_retry(_provider_error(429), attempt_number=1) is True
    assert policy.should_retry(_provider_error(500), attempt_number=1) is True
    assert policy.should_retry(_provider_error(503), attempt_number=1) is True


def test_retry_policy_does_not_retry_client_4xx_errors() -> None:
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(_provider_error(400), attempt_number=1) is False
    assert policy.should_retry(_provider_error(401), attempt_number=1) is False
    assert policy.should_retry(_provider_error(404), attempt_number=1) is False


def test_retry_policy_does_not_retry_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(_provider_error(429), attempt_number=3) is False


def test_retry_policy_calculates_exponential_delay_with_jitter() -> None:
    policy = RetryPolicy(
        base_delay_seconds=2,
        jitter_seconds=0.5,
        random_source=random.Random(1),
    )

    delay = policy.delay_for_attempt(2)

    assert 4 <= delay <= 4.5


def test_retry_policy_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="max_attempts must be positive"):
        RetryPolicy(max_attempts=0)


def _provider_error(status_code: int) -> ProviderError:
    return ProviderError(
        status_code=status_code,
        error_type="provider_error",
        safe_message="Provider failed",
    )
